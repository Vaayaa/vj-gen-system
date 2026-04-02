"""
VJ-Gen Librosa 音频分析适配器
实现基于 librosa 的音频分析功能
"""

import time
from pathlib import Path
from typing import Optional

import numpy as np

from src.adapters.audio.base import AudioAnalysisAdapter, AudioAnalysisParams
from src.adapters.base import AdapterConfig, HealthStatus
from src.models.schemas import (
    AudioAnalysisResult,
    AudioSection,
    BeatInfo,
    EnergyPoint,
    SectionType,
)


class LibrosaAdapter(AudioAnalysisAdapter):
    """
    Librosa 音频分析适配器
    
    提供：
    - BPM 检测
    - 节拍提取
    - 能量曲线
    - 段落分析
    """

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._try_import_librosa()

    def _try_import_librosa(self) -> None:
        """尝试导入 librosa"""
        try:
            import librosa
            self.librosa = librosa
        except ImportError:
            raise ImportError(
                "librosa 未安装，请运行: pip install librosa"
            )

    @property
    def provider(self) -> str:
        return "local"

    @property
    def model(self) -> str:
        return "librosa"

    @property
    def supported_formats(self) -> list[str]:
        return [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"]

    def get_capabilities(self) -> list:
        from src.adapters.base import AdapterCapability
        return [
            AdapterCapability(
                name="beat_detection",
                description="检测音频节拍和时间戳",
                supported_params=["onset_method"],
                estimated_latency_ms=5000,
            ),
            AdapterCapability(
                name="bpm_detection",
                description="检测音乐 BPM",
                supported_params=["start_bpm"],
                estimated_latency_ms=3000,
            ),
            AdapterCapability(
                name="energy_analysis",
                description="分析音频能量曲线",
                supported_params=["frame_length", "hop_length"],
                estimated_latency_ms=2000,
            ),
        ]

    async def health_check(self) -> HealthStatus:
        """健康检查"""
        start = time.time()
        try:
            # 简单的 librosa 功能测试
            import librosa
            y, sr = librosa.load(
                librosa.ex("trumpet"),
                duration=1.0,
                sr=22050,
            )
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
            return await self.analyze(input_data)
        raise ValueError("input_data must be audio_path (str)")

    async def analyze(
        self,
        audio_path: str,
        params: Optional[AudioAnalysisParams] = None,
    ) -> AudioAnalysisResult:
        """
        完整音频分析
        
        Args:
            audio_path: 音频文件路径
            params: 分析参数
            
        Returns:
            AudioAnalysisResult
        """
        params = params or AudioAnalysisParams()
        
        # 加载音频
        y, sr = self.librosa.load(audio_path, sr=22050, mono=True)
        duration = len(y) / sr
        
        # 并行执行各项分析
        bpm = await self.detect_bpm(audio_path)
        beats = await self.extract_beats(audio_path)
        
        energy_curve = []
        if params.compute_energy:
            energy_curve = self._compute_energy_curve(y, sr, params)
        
        sections = []
        if params.compute_sections:
            sections = self._detect_sections(y, sr, beats, energy_curve)
        
        return AudioAnalysisResult(
            bpm=bpm,
            time_signature="4/4",
            duration=duration,
            sections=sections,
            energy_curve=energy_curve,
            beats=beats,
            analysis_version="1.0.0",
        )

    async def extract_beats(self, audio_path: str) -> list[BeatInfo]:
        """提取节拍"""
        import librosa
        
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        
        # onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # beats
        times = librosa.frames_to_time(
            librosa.onset.onset_detect(y=y, sr=sr),
            sr=sr
        )
        
        beats = []
        for i, t in enumerate(times):
            beat_type = "downbeat" if i % 4 == 0 else "beat"
            strength = float(onset_env[i]) if i < len(onset_env) else 0.5
            beats.append(BeatInfo(
                timestamp=t,
                beat_type=beat_type,
                strength=strength,
            ))
        
        return beats

    async def detect_bpm(self, audio_path: str) -> float:
        """检测 BPM"""
        import librosa
        
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        
        # 使用 librosa 的 beat tracker
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        
        return float(tempo)

    async def separate_vocals(self, audio_path: str, output_dir: str) -> tuple[str, str]:
        """分离人声 - 需要 demucs，这个是 librosa 不支持的"""
        raise NotImplementedError(
            "Vocal separation requires demucs adapter, not librosa"
        )

    async def compute_waveform(self, audio_path: str) -> list[float]:
        """计算波形"""
        import librosa
        
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        
        # 归一化到 -1~1
        y = y / (np.max(np.abs(y)) + 1e-8)
        
        return y.tolist()

    def _compute_energy_curve(
        self,
        y: np.ndarray,
        sr: int,
        params: AudioAnalysisParams,
    ) -> list[EnergyPoint]:
        """计算能量曲线"""
        import librosa
        
        # RMS 能量
        rms = librosa.feature.rms(
            y=y,
            frame_length=params.frame_length,
            hop_length=params.hop_length,
        )[0]
        
        # 时间对齐
        times = librosa.frames_to_time(
            np.arange(len(rms)),
            sr=sr,
            hop_length=params.hop_length,
        )
        
        # 归一化
        rms = rms / (np.max(rms) + 1e-8)
        
        return [
            EnergyPoint(timestamp=t, energy=float(e))
            for t, e in zip(times, rms)
        ]

    def _detect_sections(
        self,
        y: np.ndarray,
        sr: int,
        beats: list[BeatInfo],
        energy_curve: list[EnergyPoint],
    ) -> list[AudioSection]:
        """检测段落结构"""
        # 简化版段落检测
        # 完整实现需要更复杂的算法
        
        duration = len(y) / sr
        
        # 基于能量和位置简单分段
        sections = []
        
        if len(energy_curve) == 0:
            return sections
        
        # 计算平均能量
        avg_energy = np.mean([e.energy for e in energy_curve])
        
        # 简单的固定段落划分（演示用）
        segment_duration = 30.0  # 每段 30 秒
        current_time = 0.0
        
        section_types = [
            SectionType.INTRO,
            SectionType.VERSE,
            SectionType.PRE_CHORUS,
            SectionType.CHORUS,
            SectionType.DROP,
            SectionType.BRIDGE,
            SectionType.OUTRO,
        ]
        
        idx = 0
        while current_time < duration:
            seg_end = min(current_time + segment_duration, duration)
            
            # 找这段的平均能量
            seg_energies = [
                e.energy for e in energy_curve
                if current_time <= e.timestamp < seg_end
            ]
            seg_avg = np.mean(seg_energies) if seg_energies else avg_energy
            
            # 简单判断段落类型
            progress = current_time / duration
            if progress < 0.05:
                sec_type = SectionType.INTRO
            elif progress > 0.9:
                sec_type = SectionType.OUTRO
            elif seg_avg > avg_energy * 1.2:
                sec_type = SectionType.CHORUS if idx % 2 == 0 else SectionType.DROP
            elif seg_avg > avg_energy * 0.8:
                sec_type = SectionType.VERSE
            else:
                sec_type = SectionType.BRIDGE
            
            sections.append(AudioSection(
                start=current_time,
                end=seg_end,
                type=sec_type,
                energy=seg_avg,
                mood=[],
            ))
            
            current_time = seg_end
            idx += 1
        
        return sections


# 注册适配器
from src.adapters.base import AdapterRegistry
AdapterRegistry._adapters["librosa"] = LibrosaAdapter
