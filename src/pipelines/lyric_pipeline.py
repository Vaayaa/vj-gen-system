"""
VJ-Gen 歌词NLP管线
实现歌词分句、情绪分析、视觉Prompt生成的完整流程
"""

import json
import re
import time
from typing import Optional

from src.adapters.llm.base import LLMAdapter
from src.models.schemas import (
    AudioSection,
    LyricAnalysis,
    LyricLine,
    LyricSentiment,
    SectionType,
)
from src.prompts.lyric_analysis import (
    LYRIC_ANALYSIS_SCHEMA,
    VISUAL_PROMPT_ENHANCEMENT_SCHEMA,
    get_lyric_analysis_prompt,
    get_visual_enhancement_prompt,
)


class LyricPipeline:
    """歌词分析管线"""

    def __init__(self, llm_adapter: LLMAdapter):
        self.llm = llm_adapter

    def _split_lyrics(self, lyrics: str) -> list[str]:
        """将歌词文本分割成单句"""
        # 按换行分割
        lines = lyrics.strip().split("\n")
        result = []
        for line in lines:
            line = line.strip()
            if line:
                result.append(line)
        return result

    def _map_sentiment(self, sentiment_str: str) -> LyricSentiment:
        """将字符串情绪映射到枚举"""
        mapping = {
            "calm": LyricSentiment.CALM,
            "build": LyricSentiment.BUILD,
            "climax": LyricSentiment.CLIMAX,
            "dark": LyricSentiment.DARK,
            "bright": LyricSentiment.BRIGHT,
            "neutral": LyricSentiment.NEUTRAL,
            "emotional": LyricSentiment.NEUTRAL,
            "aggressive": LyricSentiment.CLIMAX,
        }
        return mapping.get(sentiment_str.lower(), LyricSentiment.NEUTRAL)

    async def analyze(self, lyrics: str, audio_sections: Optional[list[AudioSection]] = None) -> LyricAnalysis:
        """
        分析歌词

        Args:
            lyrics: 歌词文本（支持带时间戳的LRC格式或纯文本）
            audio_sections: 音频段落信息（可选，用于时间对齐）

        Returns:
            歌词分析结果
        """
        # 解析歌词（支持LRC格式和纯文本）
        raw_lines = self._split_lyrics(lyrics)
        if not raw_lines:
            return LyricAnalysis()

        # 构建提示词
        prompt = get_lyric_analysis_prompt(lyrics)

        # 调用 LLM 分析
        result = await self.llm.structured_output(
            schema=LYRIC_ANALYSIS_SCHEMA,
            prompt=prompt,
        )

        if not result.success:
            raise RuntimeError(f"歌词分析失败: {result.error}")

        data = result.data

        # 构建歌词行列表
        lyric_lines = []
        for i, line_data in enumerate(data.get("lines", [])):
            # 估算时间（如果未提供音频段落）
            if audio_sections and i < len(audio_sections):
                start_time = audio_sections[i].start
                end_time = audio_sections[i].end
            else:
                # 均匀分配时间
                start_time = i * 3.0  # 每句假设3秒
                end_time = (i + 1) * 3.0

            lyric_line = LyricLine(
                start_time=start_time,
                end_time=end_time,
                text=line_data.get("text", ""),
                sentiment=self._map_sentiment(line_data.get("sentiment", "neutral")),
                keywords=[],  # 可扩展
                imagery=line_data.get("imagery", []),
                visual_prompt=line_data.get("visual_prompt", ""),
            )
            lyric_lines.append(lyric_line)

        # 检测语言
        language = self._detect_language(lyrics)

        # 整体情绪
        overall_mood = self._map_sentiment(data.get("overall_mood", "neutral"))

        return LyricAnalysis(
            lines=lyric_lines,
            language=language,
            overall_mood=overall_mood,
            themes=data.get("themes", []),
        )

    async def enhance_visual_prompts(
        self,
        analysis: LyricAnalysis,
        audio_sections: Optional[list[AudioSection]] = None,
    ) -> LyricAnalysis:
        """
        增强视觉Prompts

        Args:
            analysis: 已有歌词分析结果
            audio_sections: 音频段落信息

        Returns:
            增强后的歌词分析结果
        """
        enhanced_lines = []

        for i, line in enumerate(analysis.lines):
            # 获取对应的音频段落能量
            energy = 0.5
            if audio_sections:
                for section in audio_sections:
                    if section.start <= line.start_time < section.end:
                        energy = section.energy
                        break

            # 增强 visual_prompt
            prompt = get_visual_enhancement_prompt(
                lyric_text=line.text,
                sentiment=line.sentiment.value,
                imagery=line.imagery,
                style="",  # 使用默认
                energy=energy,
            )

            result = await self.llm.structured_output(
                schema=VISUAL_PROMPT_ENHANCEMENT_SCHEMA,
                prompt=prompt,
            )

            if result.success:
                data = result.data
                # 组合原始和增强的 prompt
                enhanced_prompt = f"{line.visual_prompt}. {data.get('enhanced_prompt', '')}"
                enhanced_line = LyricLine(
                    start_time=line.start_time,
                    end_time=line.end_time,
                    text=line.text,
                    sentiment=line.sentiment,
                    keywords=line.keywords,
                    imagery=line.imagery,
                    visual_prompt=enhanced_prompt,
                )
            else:
                enhanced_line = line

            enhanced_lines.append(enhanced_line)

        return LyricAnalysis(
            lines=enhanced_lines,
            language=analysis.language,
            overall_mood=analysis.overall_mood,
            themes=analysis.themes,
            analysis_version="1.1.0",
        )

    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        # 简单检测：计算中文字符比例
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_chars = len(text.replace(" ", ""))
        if total_chars == 0:
            return "unknown"
        chinese_ratio = chinese_chars / total_chars
        if chinese_ratio > 0.3:
            return "zh"
        elif chinese_ratio > 0:
            return "mixed"
        else:
            return "en"

    def align_with_audio_sections(
        self,
        analysis: LyricAnalysis,
        audio_sections: list[AudioSection],
    ) -> LyricAnalysis:
        """
        将歌词与音频段落对齐

        Args:
            analysis: 歌词分析结果
            audio_sections: 音频段落

        Returns:
            对齐后的歌词分析结果
        """
        if not audio_sections:
            return analysis

        aligned_lines = []

        for line in analysis.lines:
            # 找到包含该歌词的音频段落
            matched_section = None
            for section in audio_sections:
                if section.start <= line.start_time < section.end:
                    matched_section = section
                    break

            if matched_section:
                aligned_line = LyricLine(
                    start_time=line.start_time,
                    end_time=line.end_time,
                    text=line.text,
                    sentiment=self._merge_sentiment(line.sentiment, matched_section),
                    keywords=line.keywords,
                    imagery=line.imagery,
                    visual_prompt=line.visual_prompt,
                )
            else:
                aligned_line = line

            aligned_lines.append(aligned_line)

        return LyricAnalysis(
            lines=aligned_lines,
            language=analysis.language,
            overall_mood=analysis.overall_mood,
            themes=analysis.themes,
        )

    def _merge_sentiment(self, lyric_sentiment: LyricSentiment, section: AudioSection) -> LyricSentiment:
        """合并歌词情绪和音频段落情绪"""
        # 如果音频段落有特定情绪标签，可以用来调整
        # 这里简单返回歌词情绪
        return lyric_sentiment


def parse_lrc(lrc_content: str) -> list[tuple[float, str]]:
    """
    解析LRC歌词文件

    Args:
        lrc_content: LRC文件内容

    Returns:
        [(时间戳, 歌词), ...]
    """
    pattern = r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)"
    results = []

    for line in lrc_content.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            # 可能是2位或3位毫秒
            ms_str = match.group(3)
            if len(ms_str) == 2:
                ms = int(ms_str) * 10
            else:
                ms = int(ms_str)
            timestamp = minutes * 60 + seconds + ms / 1000
            text = match.group(4).strip()
            if text:
                results.append((timestamp, text))

    return results


async def analyze_lyrics_with_pipeline(
    llm_adapter: LLMAdapter,
    lyrics: str,
    audio_sections: Optional[list[AudioSection]] = None,
    enhance_prompts: bool = True,
) -> LyricAnalysis:
    """
    便捷函数：使用管线分析歌词

    Args:
        llm_adapter: LLM 适配器
        lyrics: 歌词内容
        audio_sections: 音频段落（可选）
        enhance_prompts: 是否增强视觉Prompts

    Returns:
        歌词分析结果
    """
    pipeline = LyricPipeline(llm_adapter)

    # 基础分析
    analysis = await pipeline.analyze(lyrics, audio_sections)

    # 与音频段落对齐
    if audio_sections:
        analysis = pipeline.align_with_audio_sections(analysis, audio_sections)

    # 增强视觉Prompts
    if enhance_prompts:
        try:
            analysis = await pipeline.enhance_visual_prompts(analysis, audio_sections)
        except Exception:
            # 增强失败不影响基础分析结果
            pass

    return analysis
