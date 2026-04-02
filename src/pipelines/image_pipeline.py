"""
VJ-Gen 图像生成管线
根据镜头脚本生成关键帧图像
"""

import asyncio
import logging
import time
from typing import Any

from src.adapters.image.base import ImageGenAdapter, ImageGenParams
from src.adapters.base import AdapterResult
from src.core.router import ModelRouter
from src.models.schemas import ShotScriptItem, ShotScript

logger = logging.getLogger(__name__)


class ImagePipeline:
    """图像生成管线"""

    def __init__(
        self,
        adapters: list[ImageGenAdapter],
        router: ModelRouter,
        output_dir: str = "/tmp/vj-gen/keyframes",
    ):
        """
        初始化图像生成管线

        Args:
            adapters: 可用的图像生成适配器列表
            router: 模型路由器
            output_dir: 输出目录
        """
        self.adapters = adapters
        self.router = router
        self.output_dir = output_dir

        # 按名称索引适配器
        self._adapter_map = {a.provider: a for a in adapters}

    def _select_adapter(self, task_type: str, context: dict[str, Any]) -> ImageGenAdapter | None:
        """选择合适的适配器"""
        adapter_name = self.router.route(task_type, context)
        return self._adapter_map.get(adapter_name)

    async def generate_keyframes(
        self,
        shot_scripts: list[ShotScriptItem],
        quality: str = "standard",
    ) -> list[AdapterResult[str]]:
        """
        生成关键帧

        Args:
            shot_scripts: 镜头脚本列表
            quality: 质量等级 (draft/standard/high/production)

        Returns:
            图像路径列表
        """
        logger.info(f"Generating {len(shot_scripts)} keyframes...")

        # 为每个镜头生成关键帧
        tasks = [
            self._generate_single_keyframe(script_item, quality)
            for script_item in shot_scripts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Keyframe {i} failed: {result}")
                final_results.append(AdapterResult.fail(str(result)))
            else:
                final_results.append(result)

        return final_results

    async def _generate_single_keyframe(
        self,
        script_item: ShotScriptItem,
        quality: str,
    ) -> AdapterResult[str]:
        """生成单个关键帧"""
        start_time = time.time()

        # 构建上下文用于路由
        context = {
            "visual_style": script_item.visual_style,
            "quality": quality,
            "energy": script_item.energy,
            "section_type": script_item.section_type.value,
        }

        # 选择适配器
        adapter = self._select_adapter("image_gen", context)
        if adapter is None:
            return AdapterResult.fail("No suitable adapter found")

        # 构建生成参数
        params = ImageGenParams(
            prompt=script_item.visual_prompt,
            negative_prompt=self._build_negative_prompt(script_item),
            width=1920,
            height=1080,
            guidance_scale=7.5 if quality in ["high", "production"] else 5.0,
            steps=50 if quality in ["high", "production"] else 30,
        )

        # 生成图像
        result = await adapter.generate(script_item.visual_prompt, params)

        if result.success and result.data:
            return AdapterResult.ok(result.data.image_path, result.latency_ms)
        else:
            return AdapterResult.fail(result.error or "Generation failed")

    async def generate_batch(
        self,
        prompts: list[str],
        adapter_name: str | None = None,
        **params_kwargs,
    ) -> list[AdapterResult[str]]:
        """
        批量生成图像

        Args:
            prompts: 提示词列表
            adapter_name: 指定适配器名称
            **params_kwargs: 传递给 ImageGenParams 的参数

        Returns:
            图像路径列表
        """
        if adapter_name and adapter_name in self._adapter_map:
            adapter = self._adapter_map[adapter_name]
        else:
            adapter = self.adapters[0] if self.adapters else None

        if adapter is None:
            return [AdapterResult.fail("No adapter available") for _ in prompts]

        params = ImageGenParams(**params_kwargs) if params_kwargs else None

        tasks = [adapter.generate(prompt, params) for prompt in prompts]
        results = await asyncio.gather(*tasks)

        return [
            AdapterResult.ok(r.data.image_path, r.latency_ms) if r.success else AdapterResult.fail(r.error)
            for r in results
        ]

    async def regenerate_keyframe(
        self,
        image_path: str,
        script_item: ShotScriptItem,
        strength: float = 0.5,
    ) -> AdapterResult[str]:
        """
        重新生成关键帧（基于原图变体）

        Args:
            image_path: 原图路径
            script_item: 镜头脚本
            strength: 变化强度

        Returns:
            新图像路径
        """
        adapter = self._select_adapter("image_variation", {"visual_style": script_item.visual_style})
        if adapter is None:
            return AdapterResult.fail("No suitable adapter found")

        result = await adapter.variation(
            image_path=image_path,
            prompt=script_item.visual_prompt,
            strength=strength,
        )

        if result.success and result.data:
            return AdapterResult.ok(result.data.image_path)
        return AdapterResult.fail(result.error or "Variation failed")

    async def upscale_keyframe(
        self,
        image_path: str,
        scale: int = 2,
        adapter_name: str = "topaz",
    ) -> AdapterResult[str]:
        """
        超分关键帧

        Args:
            image_path: 图像路径
            scale: 放大倍数
            adapter_name: 超分适配器名称

        Returns:
            放大后的图像路径
        """
        adapter = self._adapter_map.get(adapter_name)
        if adapter is None:
            return AdapterResult.fail(f"Adapter {adapter_name} not found")

        return await adapter.upscale(image_path, scale)

    def _build_negative_prompt(self, script_item: ShotScriptItem) -> str:
        """构建负面提示词"""
        negatives = [
            "blurry", "low quality", "distorted", "deformed",
            "ugly", "bad anatomy", "extra limbs",
        ]

        # 根据段落类型添加特定负面词
        if script_item.section_type.value in ["silence", "break"]:
            negatives.extend(["movement", "action", "dynamic"])

        return ", ".join(negatives)

    def get_adapter_stats(self) -> dict[str, Any]:
        """获取所有适配器的统计信息"""
        stats = {}
        for name, adapter in self._adapter_map.items():
            stats[name] = adapter.get_stats()
        return stats

    async def health_check_all(self) -> dict[str, bool]:
        """检查所有适配器的健康状态"""
        results = {}
        for name, adapter in self._adapter_map.items():
            try:
                status = await adapter.health_check()
                results[name] = status.healthy
            except Exception:
                results[name] = False
        return results
