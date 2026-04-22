"""
VJ-Gen 音频分析管线
整合多个音频分析适配器，提供完整的音频分析能力
"""

import asyncio
import importlib.util
import os
import time
from pathlib import Path
from typing import Dict, Any, Literal, Optional

from src.adapters.audio.base import AudioAnalysisAdapter, AudioAnalysisParams
from src.adapters.audio.demucs_adapter import DemucsAdapter
from src.adapters.audio.librosa_adapter import LibrosaAdapter
from src.adapters.base import AdapterConfig, AdapterRegistry
from src.models.schemas import (
    AudioAnalysisResult,
    AudioSection,
    BeatInfo,
    EnergyPoint,
)


def _load_audio_analysis_module():
    """动态加载 audio_analysis_module.py"""
    # 找到项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent  # src/pipelines -> project root
    
    module_path = project_root / "audio_analysis_module.py"
    if not module_path.exists():
        raise FileNotFoundError(f"audio_analysis_module.py not found at {module_path}")
    
    spec = importlib.util.spec_from_file_location("audio_analysis_module", str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 预加载模块
try:
    _audio_analysis_module = _load_audio_analysis_module()
except Exception as e:
    print(f"Warning: Could not load audio_analysis_module: {e}")
    _audio_analysis_module = None


class AudioPipeline:
    """
    音频分析管线
    
    整合 librosa（分析）和 demucs（分离）适配器，
    提供完整的音频分析能力：
    - BPM 检测
    - 节拍提取
    - 段落分析
    - 能量曲线
    - 人声分离
    """

    def __init__(
        self,
        librosa_adapter: Optional[LibrosaAdapter] = None,
        demucs_adapter: Optional[DemucsAdapter] = None,
        output_dir: str = "./output/audio",
    ):
        """
        初始化音频管线
        
        Args:
            librosa_adapter: librosa 分析适配器实例
            demucs_adapter: demucs 分离适配器实例
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建或使用提供的适配器
        librosa_config = AdapterConfig(provider="local", model="librosa")
        self.librosa = librosa_adapter or LibrosaAdapter(librosa_config)
        
        demucs_config = AdapterConfig(provider="local", model="demucs")
        self.demucs = demucs_adapter or DemucsAdapter(demucs_config)

    @classmethod
    def create_default(cls, output_dir: str = "./output/audio") -> "AudioPipeline":
        """
        创建默认配置的音频管线
        
        Args:
            output_dir: 输出目录
            
        Returns:
            AudioPipeline 实例
        """
        return cls(output_dir=output_dir)

    async def process(
        self,
        audio_path: str,
        params: Optional[AudioAnalysisParams] = None,
        separate_vocals: bool = False,
    ) -> AudioAnalysisResult:
        """
        完整音频分析管线
        
        Args:
            audio_path: 音频文件路径
            params: 分析参数
            separate_vocals: 是否分离人声
            
        Returns:
            AudioAnalysisResult
        """
        params = params or AudioAnalysisParams()
        start_time = time.time()
        
        # 1. 验证文件
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # 2. 并行执行 BPM/节拍/段落分析
        bpm_task = self.librosa.detect_bpm(audio_path)
        beats_task = self.librosa.extract_beats(audio_path)
        
        # 加载音频用于能量计算
        import librosa
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        duration = len(y) / sr
        
        # 能量曲线计算
        energy_curve = []
        if params.compute_energy:
            energy_curve = self.librosa._compute_energy_curve(y, sr, params)
        
        # 段落检测
        sections = []
        if params.compute_sections:
            beats = await beats_task
            sections = self.librosa._detect_sections(y, sr, beats, energy_curve)
        
        # 等待 BPM 和节拍
        bpm = await bpm_task
        beats = await beats_task
        
        # 3. 人声分离（可选，异步执行）
        vocal_path = None
        instrumental_path = None
        
        if separate_vocals and params.compute_vocal:
            try:
                vocal_path, instrumental_path = await self.demucs.separate_vocals(
                    audio_path,
                    str(self.output_dir),
                )
            except Exception as e:
                print(f"Vocal separation failed: {e}")
        
        # 4. 构建结果
        result = AudioAnalysisResult(
            bpm=bpm,
            time_signature="4/4",
            duration=duration,
            sections=sections,
            energy_curve=energy_curve,
            beats=beats,
            vocal_path=vocal_path,
            instrumental_path=instrumental_path,
            analysis_version="1.0.0",
        )
        
        elapsed = time.time() - start_time
        print(f"Audio analysis completed in {elapsed:.2f}s")
        
        return result

    def analyze_with_module(self, audio_path: str) -> Dict[str, Any]:
        """
        使用 audio_analysis_module.py 进行完整分析
        
        这是对 adapter-based 方法的替代，使用经过验证的独立模块。
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            audio_analysis_module.full_analysis() 的原始结果字典
        """
        if _audio_analysis_module is None:
            raise RuntimeError("audio_analysis_module not available")
        
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        return _audio_analysis_module.full_analysis(audio_path)

    async def analyze_only(
        self,
        audio_path: str,
        params: Optional[AudioAnalysisParams] = None,
    ) -> AudioAnalysisResult:
        """
        仅执行音频分析（不分离人声）
        
        Args:
            audio_path: 音频文件路径
            params: 分析参数
            
        Returns:
            AudioAnalysisResult
        """
        return await self.process(audio_path, params, separate_vocals=False)

    async def analyze_with_vocals(
        self,
        audio_path: str,
        params: Optional[AudioAnalysisParams] = None,
    ) -> AudioAnalysisResult:
        """
        执行音频分析并分离人声
        
        Args:
            audio_path: 音频文件路径
            params: 分析参数
            
        Returns:
            AudioAnalysisResult
        """
        return await self.process(audio_path, params, separate_vocals=True)

    async def separate_only(
        self,
        audio_path: str,
    ) -> tuple[str, str]:
        """
        仅分离人声（不执行分析）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            (人声路径, 伴奏路径)
        """
        return await self.demucs.separate_vocals(
            audio_path,
            str(self.output_dir),
        )

    async def health_check(self) -> dict[str, bool]:
        """
        健康检查所有适配器
        
        Returns:
            {适配器名: 是否健康}
        """
        results = {}
        
        # librosa 健康检查
        try:
            librosa_status = await self.librosa.health_check()
            results["librosa"] = librosa_status.healthy
        except Exception:
            results["librosa"] = False
        
        # demucs 健康检查
        try:
            demucs_status = await self.demucs.health_check()
            results["demucs"] = demucs_status.healthy
        except Exception:
            results["demucs"] = False
        
        return results

    def get_capabilities(self) -> dict[str, list]:
        """
        获取所有适配器的能力
        
        Returns:
            {适配器名: 能力列表}
        """
        return {
            "librosa": self.librosa.get_capabilities(),
            "demucs": self.demucs.get_capabilities(),
        }


class AudioPipelineBuilder:
    """
    音频管线构建器
    
    提供流式 API 来构建音频管线
    """

    def __init__(self):
        self._output_dir = "./output/audio"
        self._adapters = {}
        self._params = AudioAnalysisParams()

    def output_dir(self, path: str) -> "AudioPipelineBuilder":
        """设置输出目录"""
        self._output_dir = path
        return self

    def with_librosa(self, adapter: LibrosaAdapter) -> "AudioPipelineBuilder":
        """设置 librosa 适配器"""
        self._adapters["librosa"] = adapter
        return self

    def with_demucs(self, adapter: DemucsAdapter) -> "AudioPipelineBuilder":
        """设置 demucs 适配器"""
        self._adapters["demucs"] = adapter
        return self

    def with_params(self, params: AudioAnalysisParams) -> "AudioPipelineBuilder":
        """设置分析参数"""
        self._params = params
        return self

    def compute_energy(self, enabled: bool = True) -> "AudioPipelineBuilder":
        """设置是否计算能量"""
        self._params.compute_energy = enabled
        return self

    def compute_sections(self, enabled: bool = True) -> "AudioPipelineBuilder":
        """设置是否检测段落"""
        self._params.compute_sections = enabled
        return self

    def compute_vocals(self, enabled: bool = True) -> "AudioPipelineBuilder":
        """设置是否分离人声"""
        self._params.compute_vocal = enabled
        return self

    def build(self) -> AudioPipeline:
        """构建音频管线"""
        return AudioPipeline(
            librosa_adapter=self._adapters.get("librosa"),
            demucs_adapter=self._adapters.get("demucs"),
            output_dir=self._output_dir,
        )


# 便捷函数
async def analyze_audio(
    audio_path: str,
    output_dir: str = "./output/audio",
    separate_vocals: bool = False,
) -> AudioAnalysisResult:
    """
    便捷函数：分析音频文件
    
    Args:
        audio_path: 音频文件路径
        output_dir: 输出目录
        separate_vocals: 是否分离人声
        
    Returns:
        AudioAnalysisResult
    """
    pipeline = AudioPipeline.create_default(output_dir)
    return await pipeline.process(audio_path, separate_vocals=separate_vocals)
