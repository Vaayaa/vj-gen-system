"""
VJ-Gen 模型路由
根据任务类型选择最合适的适配器
"""

from typing import Any, Protocol, TypeVar

from src.models.schemas import ShotScriptItem


class ModelRouter(Protocol):
    """模型路由器协议"""

    def route(self, task_type: str, context: dict[str, Any]) -> str:
        """
        根据任务类型和上下文路由到合适的模型

        Args:
            task_type: 任务类型 (image_gen, video_gen, etc.)
            context: 上下文信息

        Returns:
            适配器名称
        """
        ...


class SimpleModelRouter:
    """简单模型路由器"""

    def __init__(self, adapter_configs: dict[str, str] | None = None):
        """
        初始化路由器

        Args:
            adapter_configs: 适配器名称映射（任务类型 -> 提供商名称）
        """
        self._configs = adapter_configs or {
            "image_gen": "stability_ai",
            "image_variation": "stability_ai",
            "image_upscale": "topaz",
            "video_gen": "runway",
            "text_to_video": "kling",
        }

    def route(self, task_type: str, context: dict[str, Any] | None = None) -> str:
        """路由到合适的适配器"""
        # 根据任务类型路由
        if task_type in self._configs:
            return self._configs[task_type]

        # 根据上下文信息智能路由
        if context:
            return self._route_by_context(task_type, context)

        # 默认路由
        return self._get_default_adapter(task_type)

    def _route_by_context(self, task_type: str, context: dict[str, Any]) -> str:
        """根据上下文智能路由"""
        if task_type == "image_gen":
            # 根据视觉风格选择
            visual_style = context.get("visual_style", "").lower()

            if "realistic" in visual_style or "photo" in visual_style:
                return "dalle"
            elif "anime" in visual_style or "cartoon" in visual_style:
                return "stable_diffusion"
            else:
                return "stable_diffusion"

        elif task_type == "video_gen":
            # 根据时长选择
            duration = context.get("duration", 5)

            if duration > 10:
                return "kling"  # Kling 支持更长时长
            else:
                return "runway"

        return self._get_default_adapter(task_type)

    def _get_default_adapter(self, task_type: str) -> str:
        """获取默认适配器"""
        defaults = {
            "image_gen": "stability_ai",
            "image_variation": "stability_ai",
            "image_upscale": "topaz",
            "video_gen": "runway",
            "text_to_video": "kling",
        }
        return defaults.get(task_type, "stability_ai")

    def register(self, task_type: str, adapter_name: str) -> None:
        """注册任务类型到适配器的映射"""
        self._configs[task_type] = adapter_name

    def unregister(self, task_type: str) -> None:
        """取消注册"""
        self._configs.pop(task_type, None)


class CostAwareRouter(SimpleModelRouter):
    """成本感知路由器 - 在满足质量要求的前提下选择成本最低的适配器"""

    def __init__(self, adapter_configs: dict[str, str] | None = None):
        super().__init__(adapter_configs)
        self._cost_table = {
            "stability_ai": 0.01,
            "openai": 0.04,
            "runway": 0.05,
            "kling": 0.03,
            "topaz": 0.02,
        }

    def route(self, task_type: str, context: dict[str, Any] | None = None) -> str:
        """根据成本和上下文路由"""
        if context and context.get("budget_constraint"):
            # 如果有预算限制，选择最便宜的
            return self._route_by_budget(task_type, context.get("budget_constraint"))
        return super().route(task_type, context)

    def _route_by_budget(self, task_type: str, budget: float) -> str:
        """根据预算路由"""
        candidates = []

        if task_type in ["image_gen", "image_variation"]:
            candidates = ["stability_ai", "openai"]
        elif task_type in ["video_gen", "text_to_video"]:
            candidates = ["kling", "runway"]
        elif task_type == "image_upscale":
            candidates = ["topaz"]

        for adapter in candidates:
            cost = self._cost_table.get(adapter, 0.1)
            if cost <= budget:
                return adapter

        # 如果预算不够，返回最便宜的
        return candidates[0] if candidates else self._get_default_adapter(task_type)


class QualityAwareRouter(SimpleModelRouter):
    """质量感知路由器 - 根据质量要求选择最合适的适配器"""

    QUALITY_LEVELS = {
        "draft": 1,
        "standard": 2,
        "high": 3,
        "production": 4,
    }

    def route(self, task_type: str, context: dict[str, Any] | None = None) -> str:
        """根据质量要求和上下文路由"""
        if context is None:
            context = {}

        quality = context.get("quality", "standard")
        quality_level = self.QUALITY_LEVELS.get(quality, 2)

        if task_type == "image_gen":
            if quality_level >= 3:
                return "openai"  # DALL-E 3 质量更高
            else:
                return "stability_ai"

        elif task_type == "video_gen":
            if quality_level >= 3:
                return "runway"  # Runway 质量更高
            else:
                return "kling"

        return super().route(task_type, context)
