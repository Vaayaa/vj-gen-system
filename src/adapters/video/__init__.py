"""
VJ-Gen 视频适配器
"""

from src.adapters.video.base import VideoGenAdapter, VideoGenParams, VideoResult
from src.adapters.video.runway_adapter import RunwayAdapter
from src.adapters.video.kling_adapter import KlingAdapter
from src.adapters.video.topaz_adapter import TopazVideoAdapter, TopazAdapter

__all__ = [
    "VideoGenAdapter",
    "VideoGenParams",
    "VideoResult",
    "RunwayAdapter",
    "KlingAdapter",
    "TopazVideoAdapter",
    "TopazAdapter",
]
