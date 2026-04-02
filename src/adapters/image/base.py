"""
VJ-Gen 图像生成适配器基类
定义图像生成的统一接口
"""

from abc import abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from src.adapters.base import AdapterConfig, AdapterResult, BaseAdapter, HealthStatus


class ImageGenParams(BaseModel):
    """图像生成参数"""
    width: int = Field(default=1024, ge=256, le=2048, description="宽度")
    height: int = Field(default=1024, ge=256, le=2048, description="高度")
    prompt: str = Field(..., description="生成提示")
    negative_prompt: str = Field(default="", description="负面提示")
    num_images: int = Field(default=1, ge=1, le=4, description="生成数量")
    seed: int = Field(default=-1, description="随机种子 (-1 表示随机)")
    guidance_scale: float = Field(default=7.5, ge=1, le=20, description="引导尺度")
    steps: int = Field(default=30, ge=1, le=150, description="采样步数")
    style: str = Field(default="auto", description="风格预设")


class ImageResult(BaseModel):
    """图像生成结果"""
    image_path: str = Field(..., description="生成的图像路径")
    seed: int = Field(default=0, description="使用的种子")
    prompt: str = Field(..., description="使用的提示")
    width: int = Field(..., description="宽度")
    height: int = Field(..., description="高度")
    generation_time_ms: float = Field(default=0, description="生成耗时（毫秒）")


class ImageGenAdapter(BaseAdapter):
    """
    图像生成适配器基类
    
    统一接口：
    - 文本生成图像
    - 图像变体
    - 风格迁移
    """

    @property
    @abstractmethod
    def max_resolution(self) -> tuple[int, int]:
        """最大分辨率"""
        pass

    @property
    @abstractmethod
    def supported_styles(self) -> list[str]:
        """支持的风格列表"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        params: ImageGenParams | None = None,
    ) -> AdapterResult[ImageResult]:
        """
        生成图像
        
        Args:
            prompt: 生成提示
            params: 生成参数
            
        Returns:
            图像结果
        """
        pass

    @abstractmethod
    async def generate_batch(
        self,
        prompts: list[str],
        params: ImageGenParams | None = None,
    ) -> list[AdapterResult[ImageResult]]:
        """
        批量生成图像
        
        Args:
            prompts: 提示列表
            params: 生成参数
            
        Returns:
            图像结果列表
        """
        pass

    @abstractmethod
    async def upscale(
        self,
        image_path: str,
        scale: int = 2,
    ) -> AdapterResult[str]:
        """
        超分辨率放大
        
        Args:
            image_path: 输入图像路径
            scale: 放大倍数 (2 或 4)
            
        Returns:
            放大后的图像路径
        """
        pass

    @abstractmethod
    async def variation(
        self,
        image_path: str,
        prompt: str | None = None,
        strength: float = 0.5,
    ) -> AdapterResult[ImageResult]:
        """
        生成图像变体
        
        Args:
            image_path: 输入图像路径
            prompt: 变体提示
            strength: 变化强度
            
        Returns:
            变体图像
        """
        pass

    def validate_params(self, params: ImageGenParams) -> tuple[bool, str]:
        """
        验证生成参数
        
        Args:
            params: 生成参数
            
        Returns:
            (是否有效, 错误信息)
        """
        max_w, max_h = self.max_resolution
        if params.width > max_w or params.height > max_h:
            return False, f"分辨率超过最大限制 {max_w}x{max_h}"
        if params.width % 8 != 0 or params.height % 8 != 0:
            return False, "宽度和高度必须是 8 的倍数"
        if params.num_images > 4:
            return False, "单次最多生成 4 张图像"
        return True, ""
