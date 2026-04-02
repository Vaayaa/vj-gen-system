"""
VJ-Gen 歌词管线测试
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from src.adapters.base import AdapterConfig, AdapterResult
from src.adapters.llm.base import LLMResponse
from src.models.schemas import AudioSection, LyricSentiment, SectionType
from src.pipelines.lyric_pipeline import (
    LyricPipeline,
    analyze_lyrics_with_pipeline,
    parse_lrc,
)


class MockLLMAdapter:
    """模拟 LLM 适配器"""

    def __init__(self):
        self.context_window = 128000
        self.supports_structured_output = True

    async def structured_output(self, schema, prompt, system=None):
        """模拟结构化输出"""
        # 根据 prompt 内容返回不同的模拟数据
        if "视觉描述" in prompt or "enhanced_prompt" in prompt.lower():
            return AdapterResult.ok({
                "enhanced_prompt": "A cinematic night cityscape with neon lights reflecting on wet streets, dramatic lighting, dark moody atmosphere",
                "color_palette": ["#1a1a2e", "#e94560", "#0f3460"],
                "lighting": "dramatic rim lighting with neon glow",
                "composition": "wide angle shot with leading lines"
            })
        else:
            return AdapterResult.ok({
                "lines": [
                    {
                        "text": "在黑暗中独自行走",
                        "sentiment": "dark",
                        "imagery": ["黑暗", "行走", "孤独"],
                        "style": "cinematic",
                        "visual_prompt": "A lone figure walking through darkness"
                    },
                    {
                        "text": "寻找那丢失的光明",
                        "sentiment": "build",
                        "imagery": ["光明", "寻找", "希望"],
                        "style": "ethereal",
                        "visual_prompt": "A beam of light piercing through darkness"
                    }
                ],
                "overall_mood": "melancholic",
                "themes": ["孤独", "寻找", "希望"]
            })


class TestLyricPipeline:
    """歌词管线测试"""

    @pytest.fixture
    def mock_adapter(self):
        return MockLLMAdapter()

    @pytest.fixture
    def pipeline(self, mock_adapter):
        return LyricPipeline(mock_adapter)

    @pytest.fixture
    def sample_lyrics(self):
        return "在黑暗中独自行走\n寻找那丢失的光明"

    @pytest.fixture
    def sample_audio_sections(self):
        return [
            AudioSection(start=0.0, end=3.0, type=SectionType.VERSE, energy=0.5),
            AudioSection(start=3.0, end=6.0, type=SectionType.VERSE, energy=0.6),
        ]

    @pytest.mark.asyncio
    async def test_analyze_basic(self, pipeline, sample_lyrics):
        """测试基础歌词分析"""
        result = await pipeline.analyze(sample_lyrics)

        assert len(result.lines) == 2
        assert result.lines[0].text == "在黑暗中独自行走"
        assert result.lines[1].text == "寻找那丢失的光明"
        assert result.lines[0].sentiment == LyricSentiment.DARK
        assert result.lines[1].sentiment == LyricSentiment.BUILD

    @pytest.mark.asyncio
    async def test_analyze_with_audio_sections(self, pipeline, sample_lyrics, sample_audio_sections):
        """测试带音频段落的歌词分析"""
        result = await pipeline.analyze(sample_lyrics, sample_audio_sections)

        assert len(result.lines) == 2
        # 验证时间对齐
        assert result.lines[0].start_time == 0.0
        assert result.lines[0].end_time == 3.0
        assert result.lines[1].start_time == 3.0
        assert result.lines[1].end_time == 6.0

    @pytest.mark.asyncio
    async def test_enhance_visual_prompts(self, pipeline, sample_lyrics):
        """测试视觉 Prompt 增强"""
        # 先分析
        analysis = await pipeline.analyze(sample_lyrics)
        # 再增强
        enhanced = await pipeline.enhance_visual_prompts(analysis)

        assert len(enhanced.lines) == 2
        # 增强后的 prompt 应该更长
        for line in enhanced.lines:
            assert len(line.visual_prompt) > 0

    @pytest.mark.asyncio
    async def test_align_with_audio_sections(self, pipeline, sample_lyrics, sample_audio_sections):
        """测试音频段落对齐"""
        analysis = await pipeline.analyze(sample_lyrics)
        aligned = pipeline.align_with_audio_sections(analysis, sample_audio_sections)

        assert len(aligned.lines) == 2
        # 验证对齐后的时间
        assert aligned.lines[0].start_time == 0.0
        assert aligned.lines[1].start_time == 3.0

    def test_detect_language_chinese(self, pipeline):
        """测试中文检测"""
        lang = pipeline._detect_language("在黑暗中独自行走")
        assert lang == "zh"

    def test_detect_language_english(self, pipeline):
        """测试英文检测"""
        lang = pipeline._detect_language("walking through the darkness")
        assert lang == "en"

    def test_detect_language_mixed(self, pipeline):
        """测试混合语言检测"""
        lang = pipeline._detect_language("在黑暗中 walking through darkness")
        assert lang == "mixed"

    def test_map_sentiment(self, pipeline):
        """测试情绪映射"""
        assert pipeline._map_sentiment("dark") == LyricSentiment.DARK
        assert pipeline._map_sentiment("climax") == LyricSentiment.CLIMAX
        assert pipeline._map_sentiment("unknown") == LyricSentiment.NEUTRAL

    def test_split_lyrics(self, pipeline):
        """测试歌词分割"""
        lyrics = "第一句\n第二句\n第三句"
        lines = pipeline._split_lyrics(lyrics)
        assert lines == ["第一句", "第二句", "第三句"]


class TestLRCParsing:
    """LRC 解析测试"""

    def test_parse_lrc_basic(self):
        """测试基础 LRC 解析"""
        lrc = """[00:00.00]第一句
[00:05.00]第二句
[00:10.00]第三句"""

        result = parse_lrc(lrc)
        assert len(result) == 3
        assert result[0] == (0.0, "第一句")
        assert result[1] == (5.0, "第二句")
        assert result[2] == (10.0, "第三句")

    def test_parse_lrc_with_milliseconds(self):
        """测试毫秒解析"""
        lrc = """[00:00.50]有毫秒
[00:01.25]也有毫秒"""

        result = parse_lrc(lrc)
        assert result[0][0] == 0.5
        assert result[1][0] == 1.25

    def test_parse_lrc_empty_lines(self):
        """测试空行处理"""
        lrc = """[00:00.00]第一句

[00:05.00]第二句"""

        result = parse_lrc(lrc)
        assert len(result) == 2

    def test_parse_lrc_no_match(self):
        """测试无匹配行"""
        lrc = """这不是LRC格式
[00:00.00]这是
"""

        result = parse_lrc(lrc)
        assert len(result) == 1


class TestAnalyzeLyricsWithPipeline:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_analyze_lyrics_with_pipeline(self):
        """测试便捷分析函数"""
        adapter = MockLLMAdapter()
        lyrics = "测试歌词"

        result = await analyze_lyrics_with_pipeline(
            adapter,
            lyrics,
            enhance_prompts=False
        )

        assert len(result.lines) > 0


class TestSentimentMapping:
    """情绪映射测试"""

    def test_all_sentiments(self):
        """测试所有情绪值"""
        pipeline = LyricPipeline(MockLLMAdapter())

        assert pipeline._map_sentiment("calm") == LyricSentiment.CALM
        assert pipeline._map_sentiment("build") == LyricSentiment.BUILD
        assert pipeline._map_sentiment("climax") == LyricSentiment.CLIMAX
        assert pipeline._map_sentiment("dark") == LyricSentiment.DARK
        assert pipeline._map_sentiment("bright") == LyricSentiment.BRIGHT
        assert pipeline._map_sentiment("neutral") == LyricSentiment.NEUTRAL
        # 不区分大小写
        assert pipeline._map_sentiment("DARK") == LyricSentiment.DARK
        assert pipeline._map_sentiment("Dark") == LyricSentiment.DARK
