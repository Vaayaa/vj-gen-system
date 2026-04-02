"""
VJ-Gen 歌词分析 Prompt 模板
"""

LYRIC_ANALYSIS_PROMPT = """你是一个专业的VJ视觉设计师。请分析以下歌词，提取视觉创作所需的信息。

歌词：
{lyrics}

请为每句歌词生成：
1. 情绪标签（calm/build/climax/dark/bright/emotional/aggressive）
2. 场景意象（2-3个关键词）
3. 视觉风格建议
4. 详细视觉描述Prompt（英文，用于AI图像生成）

情绪标签说明：
- calm: 平静舒缓的氛围
- build: 渐进积累的能量
- climax: 高潮爆发时刻
- dark: 暗黑压抑的情绪
- bright: 明亮欢快的氛围
- emotional: 深情抒情的时刻
- aggressive: 强烈激进的感觉

请返回JSON格式：
{{
  "lines": [
    {{
      "text": "歌词内容",
      "sentiment": "情绪",
      "imagery": ["意象1", "意象2", "意象3"],
      "style": "风格建议",
      "visual_prompt": "详细的英文视觉描述Prompt"
    }}
  ],
  "overall_mood": "整体情绪",
  "themes": ["主题1", "主题2"]
}}
"""

LYRIC_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "sentiment": {"type": "string"},
                    "imagery": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "style": {"type": "string"},
                    "visual_prompt": {"type": "string"}
                },
                "required": ["text", "sentiment", "imagery", "style", "visual_prompt"]
            }
        },
        "overall_mood": {"type": "string"},
        "themes": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["lines", "overall_mood", "themes"]
}

VISUAL_PROMPT_ENHANCEMENT_PROMPT = """你是一个专业的VJ视觉设计师。请根据以下信息，生成一个增强的AI图像生成Prompt。

歌词内容：{lyric_text}
当前情绪：{sentiment}
当前意象：{imagery}
当前风格：{style}
音频能量：{energy} (0-1)

请生成一个详细的、适合AI图像生成的英文Prompt。要求：
1. 包含主体描述
2. 包含环境/背景描述
3. 包含光线和色彩建议
4. 包含风格参考（如：cinematic, ethereal, dramatic等）
5. 包含构图建议

返回JSON格式：
{{
  "enhanced_prompt": "详细增强的英文Prompt",
  "color_palette": ["颜色1", "颜色2", "颜色3"],
  "lighting": "光线描述",
  "composition": "构图建议"
}}
"""

VISUAL_PROMPT_ENHANCEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "enhanced_prompt": {"type": "string"},
        "color_palette": {
            "type": "array",
            "items": {"type": "string"}
        },
        "lighting": {"type": "string"},
        "composition": {"type": "string"}
    },
    "required": ["enhanced_prompt", "color_palette", "lighting", "composition"]
}


def get_lyric_analysis_prompt(lyrics: str) -> str:
    """获取歌词分析提示词"""
    return LYRIC_ANALYSIS_PROMPT.format(lyrics=lyrics)


def get_visual_enhancement_prompt(lyric_text: str, sentiment: str, imagery: list[str], style: str, energy: float = 0.5) -> str:
    """获取视觉Prompt增强提示词"""
    imagery_str = ", ".join(imagery) if imagery else "abstract"
    return VISUAL_PROMPT_ENHANCEMENT_PROMPT.format(
        lyric_text=lyric_text,
        sentiment=sentiment,
        imagery=imagery_str,
        style=style,
        energy=energy
    )
