"""
VJ-Gen 视频管线测试
测试图像和视频生成管线
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.image.base import ImageGenAdapter, ImageGenParams, ImageResult
from src.adapters.image.sd_adapter import StableDiffusionAdapter
from src.adapters.image.dalle_adapter import DalleAdapter
from src.adapters.video.base import VideoGenAdapter, VideoGenParams, VideoResult
from src.adapters.video.runway_adapter import RunwayAdapter
from src.adapters.video.kling_adapter import KlingAdapter
from src.adapters.video.topaz_adapter import TopazVideoAdapter
from src.adapters.base import AdapterConfig, AdapterResult
from src.pipelines.image_pipeline import ImagePipeline
from src.pipelines.video_pipeline import VideoPipeline
from src.core.router import SimpleModelRouter, QualityAwareRouter, CostAwareRouter
from src.models.schemas import (
    ShotScriptItem, ShotScript, SectionType, MotionDesign,
    CameraBehavior, TransitionHint, VJClip, ClipMetadata, TaskStatus,
)


class TestModelRouter(unittest.TestCase):
    """测试模型路由器"""

    def test_simple_router_default(self):
        """测试简单路由器默认路由"""
        router = SimpleModelRouter()
        self.assertEqual(router.route("image_gen"), "stability_ai")
        self.assertEqual(router.route("video_gen"), "runway")

    def test_simple_router_custom_config(self):
        """测试自定义配置"""
        router = SimpleModelRouter({"image_gen": "dalle"})
        self.assertEqual(router.route("image_gen"), "dalle")

    def test_quality_router(self):
        """测试质量感知路由"""
        router = QualityAwareRouter()

        # 高质量使用 DALL-E (openai)
        context = {"quality": "high"}
        self.assertEqual(router.route("image_gen", context), "openai")

        # 标准质量使用 SD
        context = {"quality": "standard"}
        self.assertEqual(router.route("image_gen", context), "stability_ai")

    def test_cost_router(self):
        """测试成本感知路由"""
        router = CostAwareRouter()

        # 低预算选择便宜选项
        context = {"budget_constraint": 0.01}
        self.assertEqual(router.route("image_gen", context), "stability_ai")

    def test_router_register(self):
        """测试路由注册"""
        router = SimpleModelRouter()
        router.register("custom_task", "my_adapter")
        self.assertEqual(router.route("custom_task"), "my_adapter")


class TestImageGenAdapters(unittest.TestCase):
    """测试图像生成适配器"""

    def setUp(self):
        """设置测试"""
        self.config = AdapterConfig(
            provider="test",
            model="test-model",
            api_key="test-key",
            api_base="https://api.test.com",
            extra_params={"output_dir": "/tmp/test-images"},
        )

    def test_sd_adapter_properties(self):
        """测试 SD 适配器属性"""
        adapter = StableDiffusionAdapter(self.config)
        self.assertEqual(adapter.provider, "stability_ai")
        self.assertEqual(adapter.max_resolution, (2048, 2048))
        self.assertIn("auto", adapter.supported_styles)

    def test_dalle_adapter_properties(self):
        """测试 DALL-E 适配器属性"""
        adapter = DalleAdapter(self.config)
        self.assertEqual(adapter.provider, "openai")
        self.assertIn("dall-e-3", adapter.model)
        self.assertEqual(adapter.max_resolution, (1792, 1792))

    def test_image_gen_params_validation(self):
        """测试图像生成参数验证"""
        params = ImageGenParams(
            prompt="test prompt",
            width=1024,
            height=1024,
        )
        self.assertEqual(params.width, 1024)
        self.assertEqual(params.height, 1024)


class TestVideoGenAdapters(unittest.TestCase):
    """测试视频生成适配器"""

    def setUp(self):
        """设置测试"""
        self.config = AdapterConfig(
            provider="test",
            model="test-model",
            api_key="test-key",
            api_base="https://api.test.com",
            extra_params={"output_dir": "/tmp/test-videos"},
        )

    def test_runway_adapter_properties(self):
        """测试 Runway 适配器属性"""
        adapter = RunwayAdapter(self.config)
        self.assertEqual(adapter.provider, "runway")
        self.assertEqual(adapter.max_duration, 10.0)
        self.assertIn("540p", adapter.supported_resolutions)

    def test_kling_adapter_properties(self):
        """测试 Kling 适配器属性"""
        adapter = KlingAdapter(self.config)
        self.assertEqual(adapter.provider, "kling")
        self.assertEqual(adapter.max_duration, 30.0)
        self.assertIn("1080p", adapter.supported_resolutions)

    def test_video_gen_params(self):
        """测试视频生成参数"""
        params = VideoGenParams(
            prompt="test prompt",
            duration=5.0,
            resolution="720p",
        )
        self.assertEqual(params.duration, 5.0)
        self.assertEqual(params.resolution, "720p")

    def test_estimate_cost(self):
        """测试成本估算"""
        adapter = RunwayAdapter(self.config)
        params = VideoGenParams(prompt="test", duration=5.0, resolution="720p")
        cost = adapter.estimate_cost(params)
        self.assertGreater(cost, 0)


class TestTopazAdapter(unittest.TestCase):
    """测试 Topaz 超分适配器"""

    def setUp(self):
        """设置测试"""
        self.config = AdapterConfig(
            provider="topaz",
            model="video-ai",
            api_key="test-key",
            api_base="https://api.topazlabs.io/v1",
            extra_params={"output_dir": "/tmp/test-upscaled"},
        )

    def test_topaz_adapter_properties(self):
        """测试 Topaz 适配器属性"""
        adapter = TopazVideoAdapter(self.config)
        self.assertEqual(adapter.provider, "topaz")
        self.assertEqual(adapter.model, "video-ai")


class TestImagePipeline(unittest.TestCase):
    """测试图像生成管线"""

    def setUp(self):
        """设置测试"""
        self.config = AdapterConfig(
            provider="test",
            model="test-model",
            api_key="test-key",
        )

        # 创建模拟适配器
        self.mock_adapter = MagicMock(spec=ImageGenAdapter)
        self.mock_adapter.provider = "stability_ai"
        self.mock_adapter.get_stats.return_value = {"total_calls": 0}

        # 创建路由器
        self.router = SimpleModelRouter()

        # 创建管线
        self.pipeline = ImagePipeline(
            adapters=[self.mock_adapter],
            router=self.router,
        )

    def test_pipeline_initialization(self):
        """测试管线初始化"""
        self.assertEqual(len(self.pipeline.adapters), 1)
        self.assertEqual(self.pipeline.router, self.router)

    def test_select_adapter(self):
        """测试适配器选择"""
        adapter = self.pipeline._select_adapter("image_gen", {})
        self.assertIsNotNone(adapter)

    def test_build_negative_prompt(self):
        """测试负面提示词构建"""
        script = ShotScriptItem(
            id="test",
            time_start=0,
            time_end=5,
            section_type=SectionType.SILENCE,
            lyric="",
            audio_emotion="calm",
            energy=0.3,
            visual_style="test",
            visual_prompt="test",
            motion_design=MotionDesign(),
            color_palette=[],
            camera_behavior=CameraBehavior.STATIC,
        )
        neg = self.pipeline._build_negative_prompt(script)
        self.assertIn("movement", neg)
        self.assertIn("action", neg)


class TestVideoPipeline(unittest.TestCase):
    """测试视频生成管线"""

    def setUp(self):
        """设置测试"""
        self.config = AdapterConfig(
            provider="test",
            model="test-model",
            api_key="test-key",
        )

        # 创建模拟视频适配器
        self.mock_adapter = MagicMock(spec=VideoGenAdapter)
        self.mock_adapter.provider = "runway"
        self.mock_adapter.get_stats.return_value = {"total_calls": 0}

        # 创建路由器
        self.router = SimpleModelRouter()

        # 创建管线
        self.pipeline = VideoPipeline(
            adapters=[self.mock_adapter],
            router=self.router,
        )

    def test_pipeline_initialization(self):
        """测试管线初始化"""
        self.assertEqual(len(self.pipeline.adapters), 1)
        self.assertIsNone(self.pipeline.upscale_adapter)

    def test_select_adapter(self):
        """测试适配器选择"""
        adapter = self.pipeline._select_adapter("video_gen", {})
        self.assertIsNotNone(adapter)

    def test_get_resolution_for_quality(self):
        """测试分辨率选择"""
        self.assertEqual(self.pipeline._get_resolution_for_quality("draft"), "540p")
        self.assertEqual(self.pipeline._get_resolution_for_quality("high"), "1080p")

    def test_create_failed_clip(self):
        """测试失败片段创建"""
        script = ShotScriptItem(
            id="test",
            time_start=0,
            time_end=5,
            section_type=SectionType.CHORUS,
            lyric="Test lyric",
            audio_emotion="climax",
            energy=0.8,
            visual_style="test",
            visual_prompt="test prompt",
            motion_design=MotionDesign(),
            color_palette=[],
            camera_behavior=CameraBehavior.STATIC,
        )

        clip = self.pipeline._create_failed_clip(script, "Test error")

        self.assertEqual(clip.script_item.id, "test")
        self.assertEqual(clip.generation_status, TaskStatus.FAILED)
        self.assertEqual(clip.error_message, "Test error")


class TestShotScriptItem(unittest.TestCase):
    """测试镜头脚本模型"""

    def test_shot_script_item_creation(self):
        """测试镜头脚本项创建"""
        script = ShotScriptItem(
            id="shot_001",
            time_start=0.0,
            time_end=5.0,
            section_type=SectionType.INTRO,
            lyric="Test lyric",
            audio_emotion="calm",
            energy=0.5,
            visual_style="cinematic",
            visual_prompt="A beautiful scene",
            motion_design=MotionDesign(primary_motion="pan", motion_intensity=0.5),
            color_palette=["#000000", "#FFFFFF"],
            camera_behavior=CameraBehavior.PAN,
            transition_hint=TransitionHint.FADE,
        )

        self.assertEqual(script.id, "shot_001")
        self.assertEqual(script.section_type, SectionType.INTRO)
        self.assertEqual(script.camera_behavior, CameraBehavior.PAN)

    def test_shot_script_creation(self):
        """测试完整镜头脚本创建"""
        items = [
            ShotScriptItem(
                id=f"shot_{i:03d}",
                time_start=i * 5,
                time_end=(i + 1) * 5,
                section_type=SectionType.CHORUS,
                lyric=f"Lync {i}",
                audio_emotion="climax",
                energy=0.8,
                visual_style="dynamic",
                visual_prompt="Test prompt",
                motion_design=MotionDesign(),
                color_palette=[],
                camera_behavior=CameraBehavior.STATIC,
            )
            for i in range(5)
        ]

        script = ShotScript(
            items=items,
            total_duration=25.0,
            resolution=(1920, 1080),
            fps=30,
        )

        self.assertEqual(len(script.items), 5)
        self.assertEqual(script.total_duration, 25.0)


class TestVJClip(unittest.TestCase):
    """测试 VJ 片段模型"""

    def test_vj_clip_creation(self):
        """测试 VJ 片段创建"""
        script = ShotScriptItem(
            id="shot_001",
            time_start=0.0,
            time_end=5.0,
            section_type=SectionType.INTRO,
            lyric="Test",
            audio_emotion="calm",
            energy=0.5,
            visual_style="test",
            visual_prompt="test",
            motion_design=MotionDesign(),
            color_palette=[],
            camera_behavior=CameraBehavior.STATIC,
        )

        metadata = ClipMetadata(
            width=1920,
            height=1080,
            fps=24,
            duration=5.0,
        )

        clip = VJClip(
            id="clip_001",
            time_start=0.0,
            time_end=5.0,
            script_item=script,
            video_path="/tmp/test.mp4",
            metadata=metadata,
        )

        self.assertEqual(clip.id, "clip_001")
        self.assertEqual(clip.metadata.width, 1920)
        self.assertEqual(clip.generation_status, TaskStatus.PENDING)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """设置测试"""
        self.image_config = AdapterConfig(
            provider="stable_diffusion",
            model="sd-xl",
            api_key="test-key",
            extra_params={"output_dir": "/tmp/test-images"},
        )

        self.video_config = AdapterConfig(
            provider="runway",
            model="pika",
            api_key="test-key",
            extra_params={"output_dir": "/tmp/test-videos"},
        )

    def test_adapter_configs(self):
        """测试适配器配置"""
        sd = StableDiffusionAdapter(self.image_config)
        runway = RunwayAdapter(self.video_config)

        self.assertEqual(sd.provider, "stability_ai")
        self.assertEqual(runway.provider, "runway")

    def test_pipeline_with_mock_generation(self):
        """测试管线配置"""
        router = SimpleModelRouter()

        # 创建管线
        pipeline = VideoPipeline(
            adapters=[],
            router=router,
        )

        self.assertIsNotNone(pipeline.router)


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """异步测试基类"""

    async def asyncTest(self):
        """异步测试占位"""
        pass


if __name__ == "__main__":
    unittest.main()
