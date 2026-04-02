"""
VJ-Gen 歌词分析示例
演示如何使用 LyricPipeline 分析歌词
"""

import asyncio
import os
from dotenv import load_dotenv

from src.adapters.base import AdapterConfig
from src.adapters.llm.openai_adapter import OpenAIAdapter
from src.adapters.llm.anthropic_adapter import AnthropicAdapter
from src.models.schemas import AudioSection, SectionType
from src.pipelines.lyric_pipeline import LyricPipeline, analyze_lyrics_with_pipeline


# 示例歌词
SAMPLE_LYRICS = """在黑暗中独自行走
寻找那丢失的光明
霓虹灯闪烁的街头
孤独身影被拉长

心跳声在耳边回响
回忆像潮水般涌来
城市灯火阑珊处
谁在等待着谁

向前走 不回头
风在耳边呼啸而过
穿越这无尽的黑夜
黎明就在前方等候"""


# 示例音频段落
SAMPLE_AUDIO_SECTIONS = [
    AudioSection(start=0.0, end=8.0, type=SectionType.INTRO, energy=0.3, mood=["ambient"]),
    AudioSection(start=8.0, end=20.0, type=SectionType.VERSE, energy=0.5, mood=["melancholic"]),
    AudioSection(start=20.0, end=35.0, type=SectionType.CHORUS, energy=0.8, mood=["energetic"]),
    AudioSection(start=35.0, end=45.0, type=SectionType.BRIDGE, energy=0.6, mood=["reflective"]),
    AudioSection(start=45.0, end=55.0, type=SectionType.OUTRO, energy=0.4, mood=["calm"]),
]


async def demo_openai():
    """使用 OpenAI 进行歌词分析"""
    print("=" * 60)
    print("使用 OpenAI GPT-4o 进行歌词分析")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 未设置 OPENAI_API_KEY 环境变量")
        return

    config = AdapterConfig(
        provider="openai",
        model="gpt-4o",
        api_key=api_key,
    )
    adapter = OpenAIAdapter(config)

    # 创建管线
    pipeline = LyricPipeline(adapter)

    print("\n原始歌词:")
    print(SAMPLE_LYRICS)
    print()

    # 分析歌词
    print("正在分析歌词...")
    analysis = await pipeline.analyze(SAMPLE_LYRICS, SAMPLE_AUDIO_SECTIONS)

    print(f"\n分析结果:")
    print(f"语言: {analysis.language}")
    print(f"整体情绪: {analysis.overall_mood.value}")
    print(f"主题: {analysis.themes}")
    print(f"歌词行数: {len(analysis.lines)}")

    print("\n逐行分析:")
    for i, line in enumerate(analysis.lines, 1):
        print(f"\n[{i}] {line.text}")
        print(f"    情绪: {line.sentiment.value}")
        print(f"    意象: {line.imagery}")
        print(f"    Visual Prompt: {line.visual_prompt[:100]}...")

    # 增强视觉 Prompts
    print("\n正在增强视觉 Prompts...")
    enhanced = await pipeline.enhance_visual_prompts(analysis, SAMPLE_AUDIO_SECTIONS)

    print("\n增强后的 Visual Prompts:")
    for i, line in enumerate(enhanced.lines, 1):
        print(f"\n[{i}] {line.text}")
        print(f"    增强后: {line.visual_prompt[:150]}...")


async def demo_anthropic():
    """使用 Anthropic Claude 进行歌词分析"""
    print("\n" + "=" * 60)
    print("使用 Anthropic Claude 进行歌词分析")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        return

    config = AdapterConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key=api_key,
    )
    adapter = AnthropicAdapter(config)

    # 使用便捷函数
    print("\n原始歌词:")
    print(SAMPLE_LYRICS)
    print()

    print("正在分析歌词...")
    analysis = await analyze_lyrics_with_pipeline(
        adapter,
        SAMPLE_LYRICS,
        SAMPLE_AUDIO_SECTIONS,
        enhance_prompts=False,  # 暂时跳过增强
    )

    print(f"\n分析结果:")
    print(f"语言: {analysis.language}")
    print(f"整体情绪: {analysis.overall_mood.value}")
    print(f"主题: {analysis.themes}")

    print("\n逐行分析:")
    for i, line in enumerate(analysis.lines, 1):
        print(f"\n[{i}] {line.text}")
        print(f"    情绪: {line.sentiment.value}")
        print(f"    意象: {line.imagery}")


async def demo_lrc_parsing():
    """演示 LRC 歌词解析"""
    print("\n" + "=" * 60)
    print("LRC 歌词解析演示")
    print("=" * 60)

    lrc_content = """[00:00.00]在黑暗中独自行走
[00:05.20]寻找那丢失的光明
[00:10.50]霓虹灯闪烁的街头
[00:15.80]孤独身影被拉长
[00:21.00]心跳声在耳边回响
[00:26.30]回忆像潮水般涌来
[00:31.50]城市灯火阑珊处
[00:36.80]谁在等待着谁
[00:42.00]向前走 不回头
[00:47.20]风在耳边呼啸而过
[00:52.50]穿越这无尽的黑夜
[00:57.80]黎明就在前方等候"""

    from src.pipelines.lyric_pipeline import parse_lrc

    parsed = parse_lrc(lrc_content)
    print("\n解析结果:")
    for timestamp, text in parsed:
        print(f"  [{timestamp:.2f}s] {text}")


async def main():
    load_dotenv()

    print("VJ-Gen 歌词分析示例")
    print("=" * 60)

    await demo_lrc_parsing()

    # 根据环境变量选择
    if os.getenv("OPENAI_API_KEY"):
        await demo_openai()
    elif os.getenv("ANTHROPIC_API_KEY"):
        await demo_anthropic()
    else:
        print("\n请设置环境变量 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 来运行完整示例")
        print("\n仅演示 LRC 解析（无需 API Key）")


if __name__ == "__main__":
    asyncio.run(main())
