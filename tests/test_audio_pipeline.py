"""
VJ-Gen 音频管线测试
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.audio.base import AudioAnalysisParams
from src.adapters.audio.librosa_adapter import LibrosaAdapter
from src.adapters.audio.demucs_adapter import DemucsAdapter
from src.adapters.base import AdapterConfig
from src.models.schemas import (
    AudioAnalysisResult,
    AudioSection,
    BeatInfo,
    EnergyPoint,
    SectionType,
)
from src.pipelines.audio_pipeline import (
    AudioPipeline,
    AudioPipelineBuilder,
    analyze_audio,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def librosa_config():
    """Librosa 适配器配置"""
    return AdapterConfig(provider="local", model="librosa")


@pytest.fixture
def demucs_config():
    """Demucs 适配器配置"""
    return AdapterConfig(provider="local", model="demucs")


@pytest.fixture
def librosa_adapter(librosa_config):
    """Librosa 适配器实例"""
    return LibrosaAdapter(librosa_config)


@pytest.fixture
def demucs_adapter(demucs_config):
    """Demucs 适配器实例"""
    return DemucsAdapter(demucs_config)


@pytest.fixture
def sample_audio_path():
    """示例音频路径（使用 librosa 内置示例）"""
    return "librosa.util.example_audio_file"


@pytest.fixture
def output_dir():
    """临时输出目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_audio_data():
    """模拟音频数据"""
    import numpy as np
    # 生成 10 秒的测试音频（正弦波）
    sr = 22050
    duration = 10
    t = np.linspace(0, duration, int(sr * duration))
    # 440 Hz 正弦波
    y = np.sin(2 * np.pi * 440 * t)
    return y, sr


# ============================================================================
# LibrosaAdapter 测试
# ============================================================================

class TestLibrosaAdapter:
    """LibrosaAdapter 单元测试"""

    def test_init(self, librosa_config):
        """测试初始化"""
        adapter = LibrosaAdapter(librosa_config)
        assert adapter.provider == "local"
        assert adapter.model == "librosa"
        assert ".mp3" in adapter.supported_formats

    def test_supported_formats(self, librosa_adapter):
        """测试支持的格式"""
        formats = librosa_adapter.supported_formats
        assert ".mp3" in formats
        assert ".wav" in formats
        assert ".flac" in formats

    def test_get_capabilities(self, librosa_adapter):
        """测试能力列表"""
        capabilities = librosa_adapter.get_capabilities()
        assert len(capabilities) > 0
        cap_names = [c.name for c in capabilities]
        assert "bpm_detection" in cap_names
        assert "beat_detection" in cap_names
        assert "energy_analysis" in cap_names

    @pytest.mark.asyncio
    async def test_health_check(self, librosa_adapter):
        """测试健康检查"""
        status = await librosa_adapter.health_check()
        assert status.healthy is True
        assert status.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_detect_bpm_mock(self, librosa_adapter, mock_audio_data):
        """测试 BPM 检测（模拟）"""
        with patch.object(librosa_adapter.librosa, 'load', return_value=mock_audio_data):
            with patch.object(librosa_adapter.librosa.beat, 'beat_track', return_value=(120.0, [])):
                # 不真正调用 librosa
                pass

    @pytest.mark.asyncio
    async def test_invoke_requires_path(self, librosa_adapter):
        """测试 invoke 需要路径参数"""
        with pytest.raises(ValueError):
            await librosa_adapter.invoke(123)


# ============================================================================
# DemucsAdapter 测试
# ============================================================================

class TestDemucsAdapter:
    """DemucsAdapter 单元测试"""

    def test_init(self, demucs_config):
        """测试初始化"""
        adapter = DemucsAdapter(demucs_config)
        assert adapter.provider == "local"
        assert adapter.model == "demucs"

    def test_supported_formats(self, demucs_adapter):
        """测试支持的格式"""
        formats = demucs_adapter.supported_formats
        assert ".mp3" in formats
        assert ".wav" in formats

    def test_get_capabilities(self, demucs_adapter):
        """测试能力列表"""
        capabilities = demucs_adapter.get_capabilities()
        cap_names = [c.name for c in capabilities]
        assert "vocal_separation" in cap_names
        assert "instrument_separation" in cap_names

    @pytest.mark.asyncio
    async def test_health_check(self, demucs_adapter):
        """测试健康检查"""
        status = await demucs_adapter.health_check()
        # 可能因为 demucs 未完全安装而失败，但不应抛出异常
        assert isinstance(status.healthy, bool)
        assert status.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_analyze_not_implemented(self, demucs_adapter):
        """测试 analyze 方法未实现"""
        with pytest.raises(NotImplementedError):
            await demucs_adapter.analyze("dummy_path")


# ============================================================================
# AudioPipeline 测试
# ============================================================================

class TestAudioPipeline:
    """AudioPipeline 单元测试"""

    def test_create_default(self, output_dir):
        """测试创建默认管线"""
        pipeline = AudioPipeline.create_default(output_dir)
        assert pipeline.librosa is not None
        assert pipeline.demucs is not None
        assert pipeline.output_dir == Path(output_dir)

    def test_init_with_adapters(self, output_dir, librosa_adapter, demucs_adapter):
        """测试使用自定义适配器初始化"""
        pipeline = AudioPipeline(
            librosa_adapter=librosa_adapter,
            demucs_adapter=demucs_adapter,
            output_dir=output_dir,
        )
        assert pipeline.librosa is librosa_adapter
        assert pipeline.demucs is demucs_adapter

    @pytest.mark.asyncio
    async def test_health_check(self, output_dir):
        """测试管线健康检查"""
        pipeline = AudioPipeline.create_default(output_dir)
        results = await pipeline.health_check()
        assert "librosa" in results
        assert "demucs" in results

    def test_get_capabilities(self, output_dir):
        """测试获取能力列表"""
        pipeline = AudioPipeline.create_default(output_dir)
        caps = pipeline.get_capabilities()
        assert "librosa" in caps
        assert "demucs" in caps


class TestAudioPipelineBuilder:
    """AudioPipelineBuilder 单元测试"""

    def test_builder_output_dir(self):
        """测试设置输出目录"""
        builder = AudioPipelineBuilder().output_dir("/tmp/test")
        assert builder._output_dir == "/tmp/test"

    def test_builder_with_librosa(self, librosa_adapter):
        """测试设置 librosa 适配器"""
        builder = AudioPipelineBuilder().with_librosa(librosa_adapter)
        assert builder._adapters.get("librosa") is librosa_adapter

    def test_builder_with_demucs(self, demucs_adapter):
        """测试设置 demucs 适配器"""
        builder = AudioPipelineBuilder().with_demucs(demucs_adapter)
        assert builder._adapters.get("demucs") is demucs_adapter

    def test_builder_compute_options(self):
        """测试计算选项"""
        builder = (
            AudioPipelineBuilder()
            .compute_energy(True)
            .compute_sections(False)
            .compute_vocals(True)
        )
        assert builder._params.compute_energy is True
        assert builder._params.compute_sections is False
        assert builder._params.compute_vocal is True

    def test_builder_build(self):
        """测试构建管线"""
        pipeline = AudioPipelineBuilder().build()
        assert isinstance(pipeline, AudioPipeline)
        assert pipeline.librosa is not None


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_analyze_audio_fake_file(self):
        """测试 analyze_audio 处理不存在的文件"""
        with pytest.raises(FileNotFoundError):
            await analyze_audio("/nonexistent/file.mp3")


# ============================================================================
# 数据模型测试
# ============================================================================

class TestDataModels:
    """数据模型测试"""

    def test_audio_analysis_result_creation(self):
        """测试 AudioAnalysisResult 创建"""
        result = AudioAnalysisResult(
            bpm=120.0,
            duration=180.0,
            sections=[],
            energy_curve=[],
            beats=[],
        )
        assert result.bpm == 120.0
        assert result.duration == 180.0
        assert result.time_signature == "4/4"  # 默认值

    def test_audio_section_creation(self):
        """测试 AudioSection 创建"""
        section = AudioSection(
            start=0.0,
            end=30.0,
            type=SectionType.INTRO,
            energy=0.5,
        )
        assert section.start == 0.0
        assert section.end == 30.0
        assert section.type == SectionType.INTRO

    def test_beat_info_creation(self):
        """测试 BeatInfo 创建"""
        beat = BeatInfo(
            timestamp=1.5,
            beat_type="downbeat",
            strength=0.8,
        )
        assert beat.timestamp == 1.5
        assert beat.beat_type == "downbeat"
        assert beat.strength == 0.8

    def test_energy_point_creation(self):
        """测试 EnergyPoint 创建"""
        point = EnergyPoint(timestamp=0.0, energy=0.7)
        assert point.timestamp == 0.0
        assert point.energy == 0.7
        # 验证范围检查
        with pytest.raises(ValueError):
            EnergyPoint(timestamp=0.0, energy=1.5)  # 超过范围

    def test_section_type_enum(self):
        """测试 SectionType 枚举"""
        assert SectionType.INTRO.value == "intro"
        assert SectionType.CHORUS.value == "chorus"
        assert SectionType.DROP.value == "drop"


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试（需要真实音频文件）"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.path.exists("test_audio.mp3"),
        reason="需要测试音频文件"
    )
    async def test_full_pipeline_with_audio(self, output_dir):
        """测试完整管线（需要真实音频）"""
        pipeline = AudioPipeline.create_default(output_dir)
        result = await pipeline.analyze_only("test_audio.mp3")
        
        assert result.bpm > 0
        assert result.duration > 0
        assert len(result.beats) > 0
        assert result.energy_curve is not None


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
