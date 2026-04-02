"""
VJ-Gen 图像适配器
"""

from src.adapters.image.base import ImageGenAdapter, ImageGenParams, ImageResult
from src.adapters.image.sd_adapter import StableDiffusionAdapter
from src.adapters.image.dalle_adapter import DalleAdapter

__all__ = [
    "ImageGenAdapter",
    "ImageGenParams",
    "ImageResult",
    "StableDiffusionAdapter",
    "DalleAdapter",
]
