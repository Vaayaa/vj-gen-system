"""
VJ-Gen 音频分析适配器基类
定义音频分析的统一接口
"""

from abc import abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.adapters.base import AdapterConfig, BaseAdapter, HealthStatus


class AudioAnalysisParams(BaseModel):
    """音频分析参数"""
    beat_algorithm: Literal["specflux", " librosa", "rkiss"] = Field(
        default="librosa", description="节拍检测算法"
    )
    onset_method: Literal["default", "mkl", "scipy"] = Field(
        default="default", description="onset 检测方法"
    )
    compute_vocal: bool = Field(default=True, description="是否分离人声")
    compute_energy: bool = Field(default=True, description="是否计算能量曲线")
    compute_sections: bool = Field(default=True, description="是否检测段落结构")
    frame_length: int = Field(default=2048, description="帧长度")
    hop_length: int = Field(default=512, description="跳跃长度")


class AudioAnalysisAdapter(BaseAdapter):
    """
    音频分析适配器基类
    
    统一接口：
    - BPM 检测
    - 节拍提取
    - 段落结构分析
    - 能量曲线
    - 人声分离
    """

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """支持的音频格式"""
        pass

    @abstractmethod
    async def analyze(
        self,
        audio_path: str,
        params: AudioAnalysisParams | None = None,
    ) -> dict:
        """
        分析音频文件
        
        Args:
            audio_path: 音频文件路径
            params: 分析参数
            
        Returns:
            AudioAnalysisResult 字典
        """
        pass

    @abstractmethod
    async def extract_beats(self, audio_path: str) -> list[dict]:
        """
        提取节拍
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            节拍列表
        """
        pass

    @abstractmethod
    async def detect_bpm(self, audio_path: str) -> float:
        """
        检测 BPM
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            BPM 值
        """
        pass

    @abstractmethod
    async def separate_vocals(self, audio_path: str, output_dir: str) -> tuple[str, str]:
        """
        分离人声
        
        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            
        Returns:
            (人声路径, 伴奏路径)
        """
        pass

    @abstractmethod
    async def compute_waveform(self, audio_path: str) -> list[float]:
        """
        计算波形数据
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            波形数据列表（归一化到 -1~1）
        """
        pass

    def validate_audio_file(self, audio_path: str) -> bool:
        """
        验证音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            是否有效
        """
        path = Path(audio_path)
        if not path.exists():
            return False
        if path.suffix.lower() not in self.supported_formats:
            return False
        return True
