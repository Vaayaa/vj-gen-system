"""
多画幅渲染配置模型
定义渲染配置和画幅比例枚举
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AspectRatio(Enum):
    """画幅比例枚举"""
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    ULTRA_WIDE = "32:9"
    LED_WALL = "16:9"  # 3840x2160 resolution

    @property
    def width_ratio(self) -> float:
        """获取宽度比例"""
        ratios = {
            "16:9": 16,
            "9:16": 9,
            "1:1": 1,
            "32:9": 32,
        }
        return ratios.get(self.value, 16)

    @property
    def height_ratio(self) -> float:
        """获取高度比例"""
        ratios = {
            "16:9": 9,
            "9:16": 16,
            "1:1": 1,
            "32:9": 9,
        }
        return ratios.get(self.value, 9)

    @property
    def ratio_float(self) -> float:
        """获取浮点比例"""
        return self.width_ratio / self.height_ratio


@dataclass
class RenderProfile:
    """渲染配置"""
    name: str
    width: int
    height: int
    aspect_ratio: str
    fps: int = 30
    output_format: str = "mp4"
    codec: str = "libx264"
    crf: int = 23
    preset: str = "medium"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 44100

    def __post_init__(self):
        """验证配置"""
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Invalid resolution: {self.width}x{self.height}")
        if self.fps <= 0:
            raise ValueError(f"Invalid fps: {self.fps}")

    @property
    def resolution(self) -> tuple[int, int]:
        """获取分辨率元组"""
        return (self.width, self.height)

    @property
    def resolution_str(self) -> str:
        """获取分辨率字符串"""
        return f"{self.width}x{self.height}"

    def to_ffmpeg_args(self) -> List[str]:
        """转换为 ffmpeg 参数"""
        args = [
            "-vf", f"scale={self.width}:{self.height}",
            "-c:v", self.codec,
            "-crf", str(self.crf),
            "-preset", self.preset,
            "-c:a", self.audio_codec,
            "-b:a", self.audio_bitrate,
            "-ar", str(self.audio_sample_rate),
        ]
        return args


@dataclass
class BoundingBox:
    """边界框"""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0

    def to_tuple(self) -> tuple[int, int, int, int]:
        """转换为 (x, y, w, h) 元组"""
        return (self.x, self.y, self.width, self.height)


@dataclass
class CropRegion:
    """裁切区域"""
    x: int
    y: int
    width: int
    height: int

    @property
    def to_ffmpeg_crop(self) -> str:
        """转换为 ffmpeg crop 滤镜参数"""
        return f"{self.width}:{self.height}:{self.x}:{self.y}"

    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class RenderJob:
    """渲染任务"""
    input_path: str
    output_path: str
    profile: RenderProfile
    crop_region: Optional[CropRegion] = None
    fill_method: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "profile_name": self.profile.name,
            "crop_region": self.crop_region.to_dict() if self.crop_region else None,
            "fill_method": self.fill_method,
            "status": self.status,
            "error": self.error,
        }


# 预设画幅配置
PRESET_PROFILES: Dict[str, RenderProfile] = {
    "landscape_16_9": RenderProfile(
        name="横屏16:9",
        width=1920,
        height=1080,
        aspect_ratio="16:9",
    ),
    "portrait_9_16": RenderProfile(
        name="竖屏9:16",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
    ),
    "square_1_1": RenderProfile(
        name="方形1:1",
        width=1080,
        height=1080,
        aspect_ratio="1:1",
    ),
    "ultra_wide": RenderProfile(
        name="超宽32:9",
        width=3840,
        height=1080,
        aspect_ratio="32:9",
    ),
    "led_wall": RenderProfile(
        name="LED大屏",
        width=3840,
        height=2160,
        aspect_ratio="16:9",
        fps=60,
    ),
}


def get_all_presets() -> List[RenderProfile]:
    """获取所有预设配置"""
    return list(PRESET_PROFILES.values())
