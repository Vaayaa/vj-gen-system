"""
VJ-Gen 视频生成管线
根据关键帧和镜头脚本生成视频片段
"""

import asyncio
import logging
import time
import uuid
from typing import Any

from src.adapters.base import AdapterResult
from src.adapters.video.base import VideoGenAdapter, VideoGenParams, VideoResult
from src.adapters.video.topaz_adapter import TopazVideoAdapter
from src.core.router import ModelRouter
from src.models.schemas import ShotScriptItem, VJClip, ClipMetadata, TaskStatus

logger = logging.getLogger(__name__)


class VideoPipeline:
    """视频生成管线"""

    def __init__(
        self,
        adapters: list[VideoGenAdapter],
        router: ModelRouter,
        upscale_adapter: TopazVideoAdapter | None = None,
        output_dir: str = "/tmp/vj-gen/clips",
    ):
        """
        初始化视频生成管线

        Args:
            adapters: 可用的视频生成适配器列表
            router: 模型路由器
            upscale_adapter: 超分适配器（可选）
            output_dir: 输出目录
        """
        self.adapters = adapters
        self.router = router
        self.upscale_adapter = upscale_adapter
        self.output_dir = output_dir

        # 按名称索引适配器
        self._adapter_map = {a.provider: a for a in adapters}

    def _select_adapter(self, task_type: str, context: dict[str, Any]) -> VideoGenAdapter | None:
        """选择合适的适配器"""
        adapter_name = self.router.route(task_type, context)
        return self._adapter_map.get(adapter_name)

    async def generate_clips(
        self,
        keyframes: list[str],
        shot_scripts: list[ShotScriptItem],
        quality: str = "standard",
        enable_upscale: bool = False,
    ) -> list[AdapterResult[VJClip]]:
        """
        生成视频片段

        Args:
            keyframes: 关键帧图像路径列表
            shot_scripts: 镜头脚本列表
            quality: 质量等级 (draft/standard/high/production)
            enable_upscale: 是否启用超分

        Returns:
            VJClip 列表
        """
        if len(keyframes) != len(shot_scripts):
            return [AdapterResult.fail("Keyframes and shot scripts count mismatch")]

        logger.info(f"Generating {len(shot_scripts)} video clips...")

        # 并发生成所有片段
        tasks = [
            self._generate_single_clip(keyframe, script_item, quality, enable_upscale)
            for keyframe, script_item in zip(keyframes, shot_scripts)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Clip {i} failed: {result}")
                # 创建失败的 clip
                clip = self._create_failed_clip(shot_scripts[i], str(result))
                final_results.append(AdapterResult.ok(clip))
            else:
                final_results.append(result)

        return final_results

    async def _generate_single_clip(
        self,
        keyframe: str,
        script_item: ShotScriptItem,
        quality: str,
        enable_upscale: bool,
    ) -> AdapterResult[VJClip]:
        """生成单个视频片段"""
        start_time = time.time()

        # 构建上下文用于路由
        context = {
            "duration": script_item.time_end - script_item.time_start,
            "quality": quality,
            "section_type": script_item.section_type.value,
            "energy": script_item.energy,
        }

        # 选择适配器
        adapter = self._select_adapter("video_gen", context)
        if adapter is None:
            return AdapterResult.fail("No suitable video adapter found")

        # 构建生成参数
        duration = script_item.time_end - script_item.time_start
        resolution = self._get_resolution_for_quality(quality)

        params = VideoGenParams(
            prompt=self._build_motion_prompt(script_item),
            duration=duration,
            resolution=resolution,
            fps=30 if quality in ["high", "production"] else 24,
            motion_intensity=script_item.motion_design.motion_intensity,
            camera_motion=script_item.camera_behavior.value,
        )

        # 生成视频
        result = await adapter.generate(keyframe, script_item.visual_prompt, params)

        if not result.success or not result.data:
            clip = self._create_failed_clip(script_item, result.error)
            return AdapterResult.ok(clip)

        video_result = result.data
        video_path = video_result.video_path

        # 可选：超分处理
        if enable_upscale and self.upscale_adapter:
            upscale_result = await self.upscale_adapter.upscale(
                video_path,
                scale=2 if quality in ["high", "production"] else 1,
            )
            if upscale_result.success and upscale_result.data:
                video_path = upscale_result.data

        # 创建 VJClip
        clip = VJClip(
            id=f"clip_{uuid.uuid4().hex[:8]}",
            time_start=script_item.time_start,
            time_end=script_item.time_end,
            script_item=script_item,
            keyframe_path=keyframe,
            video_path=video_path,
            metadata=ClipMetadata(
                width=video_result.width,
                height=video_result.height,
                fps=video_result.fps,
                duration=duration,
            ),
            generation_status=TaskStatus.COMPLETED,
        )

        return AdapterResult.ok(clip, result.latency_ms)

    async def generate_single_clip(
        self,
        keyframe: str,
        shot_script: ShotScriptItem,
        quality: str = "standard",
        enable_upscale: bool = False,
    ) -> AdapterResult[VJClip]:
        """生成单个视频片段（对外接口）"""
        return await self._generate_single_clip(keyframe, shot_script, quality, enable_upscale)

    async def extend_clip(
        self,
        clip: VJClip,
        additional_duration: float,
        prompt: str | None = None,
    ) -> AdapterResult[VideoResult]:
        """
        延长视频片段

        Args:
            clip: 原始片段
            additional_duration: 额外时长
            prompt: 运动提示

        Returns:
            延长后的视频
        """
        if not clip.video_path:
            return AdapterResult.fail("No video path in clip")

        # 选择适配器
        adapter = self._select_adapter("video_gen", {})
        if adapter is None:
            return AdapterResult.fail("No suitable video adapter found")

        return await adapter.extend(
            clip.video_path,
            clip.metadata.duration + additional_duration,
            prompt or clip.script_item.visual_prompt,
        )

    async def stylize_clip(
        self,
        clip: VJClip,
        style: str,
    ) -> AdapterResult[VideoResult]:
        """
        风格化视频片段

        Args:
            clip: 原始片段
            style: 风格名称

        Returns:
            风格化后的视频
        """
        if not clip.video_path:
            return AdapterResult.fail("No video path in clip")

        adapter = self._select_adapter("video_gen", {})
        if adapter is None:
            return AdapterResult.fail("No suitable video adapter found")

        return await adapter.stylize(clip.video_path, style)

    async def upscale_clip(
        self,
        clip: VJClip,
        scale: int = 2,
    ) -> AdapterResult[VJClip]:
        """
        超分视频片段

        Args:
            clip: 原始片段
            scale: 放大倍数

        Returns:
            超分后的片段
        """
        if not clip.video_path:
            return AdapterResult.fail("No video path in clip")

        if self.upscale_adapter is None:
            return AdapterResult.fail("No upscale adapter configured")

        result = await self.upscale_adapter.upscale(clip.video_path, scale)

        if not result.success or not result.data:
            return AdapterResult.fail(result.error or "Upscale failed")

        # 更新 clip
        updated_clip = clip.model_copy()
        updated_clip.video_path = result.data
        updated_clip.metadata = ClipMetadata(
            width=clip.metadata.width * scale,
            height=clip.metadata.height * scale,
            fps=clip.metadata.fps,
            duration=clip.metadata.duration,
        )

        return AdapterResult.ok(updated_clip, result.latency_ms)

    def _build_motion_prompt(self, script_item: ShotScriptItem) -> str:
        """构建运动提示词"""
        parts = []

        # 主要运动
        if script_item.motion_design.primary_motion != "none":
            parts.append(script_item.motion_design.primary_motion)

        # 相机行为
        camera_map = {
            "pan": "smooth horizontal pan",
            "tilt": "gentle vertical tilt",
            "dolly": "dolly in/out",
            "zoom_in": "slow zoom in",
            "zoom_out": "slow zoom out",
            "handheld": "slight handheld shake",
            "orbit": "orbit around center",
            "rise": "camera rises up",
            "fall": "camera falls down",
        }
        camera_hint = camera_map.get(script_item.camera_behavior.value, "")
        if camera_hint:
            parts.append(camera_hint)

        # 运动强度
        intensity = script_item.motion_design.motion_intensity
        if intensity > 0.7:
            parts.append("dynamic movement")
        elif intensity < 0.3:
            parts.append("subtle motion")

        return ", ".join(parts) if parts else script_item.visual_prompt

    def _get_resolution_for_quality(self, quality: str) -> str:
        """根据质量等级获取分辨率"""
        resolution_map = {
            "draft": "540p",
            "standard": "720p",
            "high": "1080p",
            "production": "1080p",
        }
        return resolution_map.get(quality, "720p")

    def _create_failed_clip(self, script_item: ShotScriptItem, error: str) -> VJClip:
        """创建失败的片段"""
        duration = script_item.time_end - script_item.time_start
        return VJClip(
            id=f"clip_{uuid.uuid4().hex[:8]}",
            time_start=script_item.time_start,
            time_end=script_item.time_end,
            script_item=script_item,
            keyframe_path=None,
            video_path=None,
            metadata=ClipMetadata(
                width=1920,
                height=1080,
                fps=24,
                duration=duration,
            ),
            generation_status=TaskStatus.FAILED,
            error_message=error,
        )

    def get_adapter_stats(self) -> dict[str, Any]:
        """获取所有适配器的统计信息"""
        stats = {}
        for name, adapter in self._adapter_map.items():
            stats[name] = adapter.get_stats()
        if self.upscale_adapter:
            stats["topaz"] = self.upscale_adapter.get_stats() if hasattr(self.upscale_adapter, 'get_stats') else {}
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

        if self.upscale_adapter:
            try:
                status = await self.upscale_adapter.health_check()
                results["topaz"] = status.healthy
            except Exception:
                results["topaz"] = False

        return results
