"""
VJ-Gen 视频生成适配器基类
定义视频生成的统一接口
"""

from abc import abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from src.adapters.base import AdapterConfig, AdapterResult, BaseAdapter, HealthStatus


class VideoGenParams(BaseModel):
    """视频生成参数"""
    duration: float = Field(default=5.0, ge=1, le=30, description="时长（秒）")
    prompt: str = Field(..., description="生成提示")
    negative_prompt: str = Field(default="", description="负面提示")
    seed: int = Field(default=-1, description="随机种子")
    resolution: Literal["540p", "720p", "1080p"] = Field(
        default="720p", description="分辨率"
    )
    fps: int = Field(default=24, ge=24, le=60, description="帧率")
    motion_intensity: float = Field(
        default=0.5, ge=0, le=1, description="运动强度"
    )
    camera_motion: str = Field(default="auto", description="相机运动")


class VideoResult(BaseModel):
    """视频生成结果"""
    video_path: str = Field(..., description="生成的视频路径")
    thumbnail_path: str = Field(..., description="缩略图路径")
    duration: float = Field(..., description="时长（秒）")
    width: int = Field(..., description="宽度")
    height: int = Field(..., description="高度")
    fps: float = Field(..., description="帧率")
    seed: int = Field(default=0, description="使用的种子")
    generation_time_ms: float = Field(default=0, description="生成耗时（毫秒）")


class VideoGenAdapter(BaseAdapter):
    """
    视频生成适配器基类
    
    统一接口：
    - 关键帧转视频
    - 文本生成视频
    - 视频风格化
    """

    @property
    @abstractmethod
    def max_duration(self) -> float:
        """最大支持时长（秒）"""
        pass

    @property
    @abstractmethod
    def supported_resolutions(self) -> list[str]:
        """支持的分辨率列表"""
        pass

    @abstractmethod
    async def generate(
        self,
        keyframe_path: str,
        prompt: str,
        params: VideoGenParams | None = None,
    ) -> AdapterResult[VideoResult]:
        """
        从关键帧生成视频
        
        Args:
            keyframe_path: 关键帧图像路径
            prompt: 运动提示
            params: 生成参数
            
        Returns:
            视频结果
        """
        pass

    @abstractmethod
    async def generate_from_text(
        self,
        prompt: str,
        params: VideoGenParams | None = None,
    ) -> AdapterResult[VideoResult]:
        """
        文本直接生成视频
        
        Args:
            prompt: 生成提示
            params: 生成参数
            
        Returns:
            视频结果
        """
        pass

    @abstractmethod
    async def extend(
        self,
        video_path: str,
        duration: float,
        prompt: str | None = None,
    ) -> AdapterResult[VideoResult]:
        """
        延长视频
        
        Args:
            video_path: 输入视频路径
            duration: 延长后的总时长
            prompt: 运动提示
            
        Returns:
            延长后的视频
        """
        pass

    @abstractmethod
    async def stylize(
        self,
        video_path: str,
        style: str,
    ) -> AdapterResult[VideoResult]:
        """
        视频风格化
        
        Args:
            video_path: 输入视频路径
            style: 风格名称
            
        Returns:
            风格化后的视频
        """
        pass

    def estimate_cost(self, params: VideoGenParams) -> float:
        """
        估算生成成本
        
        Args:
            params: 生成参数
            
        Returns:
            预估成本（美元）
        """
        # 子类可覆盖此方法
        base_cost = 0.01  # 基础成本
        duration_cost = params.duration * 0.005  # 时长成本
        resolution_multiplier = {
            "540p": 1.0,
            "720p": 1.5,
            "1080p": 2.5,
        }.get(params.resolution, 1.0)
        return (base_cost + duration_cost) * resolution_multiplier
