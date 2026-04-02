"""
VJ-Gen Phase 1 测试：适配器基类
"""

import pytest
from abc import ABC

from src.adapters.base import (
    AdapterCapability,
    AdapterConfig,
    AdapterResult,
    BaseAdapter,
    AdapterRegistry,
)
from src.adapters.audio.base import AudioAnalysisAdapter, AudioAnalysisParams
from src.adapters.llm.base import LLMAdapter, LLMMessage
from src.adapters.image.base import ImageGenAdapter, ImageGenParams, ImageResult
from src.adapters.video.base import VideoGenAdapter, VideoGenParams, VideoResult


class TestAdapterCapability:
    """测试适配器能力描述"""

    def test_capability_creation(self):
        cap = AdapterCapability(
            name="text_to_image",
            description="Generate images from text",
            supported_params=["prompt", "width", "height"],
            limitations=["Max resolution 1024x1024"],
            estimated_latency_ms=5000,
            cost_per_call=0.04,
        )
        assert cap.name == "text_to_image"
        assert cap.cost_per_call == 0.04


class TestAdapterConfig:
    """测试适配器配置"""

    def test_config_creation(self):
        config = AdapterConfig(
            provider="openai",
            model="gpt-4o",
            api_key="sk-xxx",
            api_base="https://api.openai.com/v1",
            timeout=60,
            max_retries=3,
            temperature=0.7,
            max_tokens=4096,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.timeout == 60

    def test_config_defaults(self):
        config = AdapterConfig(provider="test", model="test")
        assert config.api_key == ""
        assert config.timeout == 60
        assert config.max_retries == 3
        assert config.temperature == 0.7


class TestAdapterResult:
    """测试适配器结果封装"""

    def test_result_ok(self):
        result = AdapterResult[dict].ok(data={"key": "value"}, latency_ms=100, tokens_used=50)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.latency_ms == 100
        assert result.tokens_used == 50

    def test_result_fail(self):
        result = AdapterResult[dict].fail(error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None


class MockBaseAdapter(BaseAdapter):
    """用于测试的 BaseAdapter 实现"""

    @property
    def provider(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-model"

    def get_capabilities(self):
        return [
            AdapterCapability(
                name="mock_capability",
                description="A mock capability",
            )
        ]

    async def health_check(self):
        return {"healthy": True}

    async def invoke(self, input_data, **kwargs):
        return {"result": "mock_output"}


class TestBaseAdapter:
    """测试基础适配器"""

    def test_adapter_creation(self):
        config = AdapterConfig(provider="test", model="test-model")
        adapter = MockBaseAdapter(config)
        assert adapter.provider == "mock"
        assert adapter.model == "mock-model"

    def test_get_stats(self):
        config = AdapterConfig(provider="test", model="test")
        adapter = MockBaseAdapter(config)
        stats = adapter.get_stats()
        assert stats["total_calls"] == 0
        assert stats["failed_calls"] == 0

    def test_record_call(self):
        config = AdapterConfig(provider="test", model="test")
        adapter = MockBaseAdapter(config)
        adapter._record_call(success=True, latency_ms=100, tokens_used=50)
        stats = adapter.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_latency_ms"] == 100
        assert stats["total_tokens"] == 50
        assert stats["success_rate"] == 1.0

    def test_record_failed_call(self):
        config = AdapterConfig(provider="test", model="test")
        adapter = MockBaseAdapter(config)
        adapter._record_call(success=True, latency_ms=100)
        adapter._record_call(success=False, latency_ms=50)
        stats = adapter.get_stats()
        assert stats["total_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["success_rate"] == 0.5

    def test_prepare_headers(self):
        config = AdapterConfig(provider="test", model="test", api_key="Bearer xxx")
        adapter = MockBaseAdapter(config)
        headers = adapter._prepare_headers()
        assert "Authorization" in headers


class TestAdapterRegistry:
    """测试适配器注册表"""

    def test_register_and_get(self):
        AdapterRegistry.register("mock", MockBaseAdapter)
        cls = AdapterRegistry.get("mock")
        assert cls == MockBaseAdapter

    def test_get_nonexistent(self):
        cls = AdapterRegistry.get("nonexistent")
        assert cls is None

    def test_list_adapters(self):
        adapters = AdapterRegistry.list_adapters()
        assert "mock" in adapters

    def test_create(self):
        config = AdapterConfig(provider="test", model="test")
        adapter = AdapterRegistry.create("mock", config)
        assert adapter is not None
        assert isinstance(adapter, MockBaseAdapter)


class TestAudioAnalysisParams:
    """测试音频分析参数"""

    def test_default_params(self):
        params = AudioAnalysisParams()
        assert params.beat_algorithm == "librosa"
        assert params.compute_vocal is True
        assert params.compute_energy is True

    def test_custom_params(self):
        params = AudioAnalysisParams(
            beat_algorithm="specflux",
            compute_vocal=False,
            frame_length=4096,
        )
        assert params.beat_algorithm == "specflux"
        assert params.compute_vocal is False


class TestLLMMessage:
    """测试 LLM 消息"""

    def test_message_creation(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestImageGenParams:
    """测试图像生成参数"""

    def test_default_params(self):
        params = ImageGenParams(prompt="A beautiful landscape")
        assert params.width == 1024
        assert params.height == 1024
        assert params.num_images == 1
        assert params.guidance_scale == 7.5

    def test_custom_params(self):
        params = ImageGenParams(
            prompt="Test prompt",
            width=512,
            height=512,
            num_images=2,
            seed=42,
        )
        assert params.width == 512
        assert params.num_images == 2
        assert params.seed == 42


class TestVideoGenParams:
    """测试视频生成参数"""

    def test_default_params(self):
        params = VideoGenParams(prompt="A moving landscape")
        assert params.duration == 5.0
        assert params.resolution == "720p"
        assert params.fps == 24

    def test_custom_params(self):
        params = VideoGenParams(
            prompt="Test",
            duration=10.0,
            resolution="1080p",
            motion_intensity=0.8,
        )
        assert params.duration == 10.0
        assert params.resolution == "1080p"
        assert params.motion_intensity == 0.8


class TestAbstractAdapters:
    """测试抽象适配器类定义"""

    def test_audio_adapter_is_abstract(self):
        assert issubclass(AudioAnalysisAdapter, BaseAdapter)
        assert issubclass(AudioAnalysisAdapter, ABC)

    def test_llm_adapter_is_abstract(self):
        assert issubclass(LLMAdapter, BaseAdapter)
        assert issubclass(LLMAdapter, ABC)

    def test_image_adapter_is_abstract(self):
        assert issubclass(ImageGenAdapter, BaseAdapter)
        assert issubclass(ImageGenAdapter, ABC)

    def test_video_adapter_is_abstract(self):
        assert issubclass(VideoGenAdapter, BaseAdapter)
        assert issubclass(VideoGenAdapter, ABC)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
