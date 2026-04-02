"""
VJ-Gen Demucs 音频分离适配器
实现基于 Demucs 的人声/伴奏分离
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Optional

import numpy as np

from src.adapters.audio.base import AudioAnalysisAdapter, AudioAnalysisParams
from src.adapters.base import AdapterConfig, HealthStatus


class DemucsAdapter(AudioAnalysisAdapter):
    """
    Demucs 音频分离适配器
    
    提供：
    - 人声分离
    - 伴奏分离
    - 鼓/贝斯/其他分离
    """

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._demucs = None
        self._model = None

    def _get_demucs(self):
        """懒加载 Demucs"""
        if self._demucs is None:
            from demucs import pretrained
            from demucs.apply import apply_model
            from demucs.separate import separate
            self._demucs = type("DemucsModule", (), {
                "separate": separate,
                "apply_model": apply_model,
                "pretrained": pretrained,
            })()
        return self._demucs

    @property
    def provider(self) -> str:
        return "local"

    @property
    def model(self) -> str:
        return "demucs"

    @property
    def supported_formats(self) -> list[str]:
        return [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"]

    def get_capabilities(self) -> list:
        from src.adapters.base import AdapterCapability
        return [
            AdapterCapability(
                name="vocal_separation",
                description="分离人声和伴奏",
                supported_params=["model_name"],
                estimated_latency_ms=60000,
            ),
            AdapterCapability(
                name="instrument_separation",
                description="分离鼓、贝斯和其他乐器",
                supported_params=["model_name"],
                estimated_latency_ms=60000,
            ),
        ]

    async def health_check(self) -> HealthStatus:
        """健康检查"""
        start = time.time()
        try:
            # 简单测试导入
            from demucs import pretrained
            latency = (time.time() - start) * 1000
            return HealthStatus(
                healthy=True,
                latency_ms=latency,
                last_check=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                error_message=str(e),
                last_check=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

    async def invoke(self, input_data: any, **kwargs) -> any:
        """统一调用接口"""
        if isinstance(input_data, str):
            output_dir = kwargs.get("output_dir")
            if output_dir:
                return await self.separate_vocals(input_data, output_dir)
            raise ValueError("output_dir is required for demucs separation")
        raise ValueError("input_data must be audio_path (str)")

    async def analyze(
        self,
        audio_path: str,
        params: Optional[AudioAnalysisParams] = None,
    ) -> dict:
        """
        Demucs 主要用于分离，不做完整分析
        """
        raise NotImplementedError("Use separate_vocals for separation")

    async def extract_beats(self, audio_path: str) -> list[dict]:
        """Demucs 不支持节拍提取"""
        raise NotImplementedError("Beat extraction requires librosa adapter")

    async def detect_bpm(self, audio_path: str) -> float:
        """Demucs 不支持 BPM 检测"""
        raise NotImplementedError("BPM detection requires librosa adapter")

    async def separate_vocals(
        self,
        audio_path: str,
        output_dir: str,
        model_name: str = "htdemucs_ft",
    ) -> tuple[str, str]:
        """
        分离人声
        
        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            model_name: 模型名称 (htdemucs_ft, htdemucs, mdx_q, etc.)
            
        Returns:
            (人声路径, 伴奏路径)
        """
        demucs = self._get_demucs()
        
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 运行分离（Demucs 的 separate 是同步的）
        loop = asyncio.get_event_loop()
        
        # 创建一个临时目录用于分离
        with tempfile.TemporaryDirectory() as temp_dir:
            # 复制音频到临时目录
            import shutil
            audio_name = Path(audio_path).stem
            temp_audio = Path(temp_dir) / f"{audio_name}.wav"
            shutil.copy(audio_path, temp_audio)
            
            # 在临时目录中运行分离
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                # 调用 demucs 分离
                await loop.run_in_executor(
                    None,
                    lambda: demucs.separate.main(
                        args=[
                            "--mp3",  # 输出为 mp3 减小体积
                            "-n", model_name,
                            str(temp_audio),
                        ]
                    )
                )
            finally:
                os.chdir(original_cwd)
            
            # 分离后的文件在 temp_dir/separated/{model_name}/{audio_name}/
            separated_dir = Path(temp_dir) / "separated" / model_name / audio_name
            
            if not separated_dir.exists():
                raise FileNotFoundError(
                    f"Separation failed, output not found at {separated_dir}"
                )
            
            # 查找人声和伴奏文件
            # Demucs 输出的 stems: drums.wav, bass.wav, other.wav, vocals.wav, (accompaniment.wav for some models)
            stems = list(separated_dir.glob("*.mp3")) or list(separated_dir.glob("*.wav"))
            stem_files = {s.stem: str(s) for s in stems}
            
            # 人声路径
            vocal_path = stem_files.get("vocals", "")
            if not vocal_path:
                raise FileNotFoundError("Vocal track not found in separated output")
            
            # 伴奏 = drums + bass + other (或 accompaniment)
            if "accompaniment" in stem_files:
                accompaniment_path = stem_files["accompaniment"]
            else:
                # 手动混合非人声轨道
                accompaniment_path = self._mix_accompaniment(
                    [stem_files[k] for k in ["drums", "bass", "other"] if k in stem_files],
                    output_path / f"{audio_name}_accompaniment.wav"
                )
            
            # 复制到目标目录
            final_vocal = output_path / f"{audio_name}_vocals.wav"
            final_accompaniment = output_path / f"{audio_name}_accompaniment.wav"
            
            import shutil
            shutil.copy(vocal_path, final_vocal)
            shutil.copy(accompaniment_path, final_accompaniment)
            
            return str(final_vocal), str(final_accompaniment)

    def _mix_accompaniment(
        self,
        stem_paths: list[str],
        output_path: Path,
    ) -> str:
        """混合非人声轨道为伴奏"""
        try:
            import soundfile as sf
            
            # 读取所有 stem 并混合
            max_length = 0
            mixed = None
            
            for stem_path in stem_paths:
                y, sr = sf.read(stem_path)
                if len(y.shape) > 1:
                    y = y.mean(axis=1)  # 转单声道
                max_length = max(max_length, len(y))
                
                if mixed is None:
                    mixed = np.zeros(max_length)
                else:
                    # 扩展到当前长度
                    if len(mixed) < len(y):
                        mixed = np.pad(mixed, (0, len(y) - len(mixed)))
                mixed[:len(y)] += y
            
            # 归一化
            mixed = mixed / (len(stem_paths) + 1e-8)
            mixed = mixed / (np.max(np.abs(mixed)) + 1e-8)
            
            # 保存
            sf.write(str(output_path), mixed, sr)
            return str(output_path)
            
        except ImportError:
            # 如果 soundfile 不可用，返回第一个 stem
            return stem_paths[0]

    async def compute_waveform(self, audio_path: str) -> list[float]:
        """波形计算需要 librosa"""
        raise NotImplementedError("Waveform computation requires librosa adapter")


# 注册适配器
from src.adapters.base import AdapterRegistry
AdapterRegistry._adapters["demucs"] = DemucsAdapter
