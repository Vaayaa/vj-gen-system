"""
转场效果模块
定义并构建 FFmpeg 转场 filter
"""

from enum import Enum
from typing import List, Optional, Tuple


class TransitionEffect(Enum):
    """转场效果类型"""
    CROSSFADE = "crossfade"       # 交叉淡化
    FADE = "fade"                  # 淡入淡出
    GLOW = "glow"                # 发光效果
    ADD = "add"                  # 叠加
    SCREEN = "screen"            # 屏幕混合
    LUMA_FADE = "luma_fade"      # 亮度淡化
    HARD_CUT = "hard_cut"        # 硬切
    STROBE = "strobe"            # 频闪
    DISSOLVE = "dissolve"        # 消散
    WIPE = "wipe"                # 滑入
    BLUR = "blur"                # 模糊过渡


class TransitionBuilder:
    """FFmpeg 转场构建器"""
    
    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
    
    def build(
        self,
        effect: TransitionEffect,
        duration: float
    ) -> str:
        """
        生成单个转场 filter 字符串
        
        Args:
            effect: 转场效果类型
            duration: 转场时长（秒）
            
        Returns:
            FFmpeg filter 字符串
        """
        n = self._get_frame_count(duration)
        
        if effect == TransitionEffect.CROSSFADE:
            return f"crossfade=d={n}"
        elif effect == TransitionEffect.DISSOLVE:
            return f"dissolve"
        elif effect == TransitionEffect.FADE:
            return f"fade=t=out:st=0:d={n}"
        elif effect == TransitionEffect.GLOW:
            # 使用 blur + 叠加实现发光
            return f"gblur=sigma=5"
        elif effect == TransitionEffect.ADD:
            return f"add"
        elif effect == TransitionEffect.SCREEN:
            return f"blend=all_expr='A+(B*(1-A/255))'"  # screen 模式
        elif effect == TransitionEffect.LUMA_FADE:
            return f"fade=t=out:st=0:d={n}"
        elif effect == TransitionEffect.HARD_CUT:
            return ""  # 硬切不需要 filter
        elif effect == TransitionEffect.STROBE:
            return f"frepeat"
        elif effect == TransitionEffect.BLUR:
            return f"gblur=sigma=3"
        elif effect == TransitionEffect.WIPE:
            return f"wipeout"
        else:
            return ""
    
    def _get_frame_count(self, duration: float) -> int:
        """将秒转换为帧数"""
        return int(duration * self.fps)
    
    def build_complex_transition(
        self,
        clip1_path: str,
        clip2_path: str,
        effect: TransitionEffect,
        transition_duration: float,
        output_label: str = "[v]"
    ) -> str:
        """
        构建复杂转场（用于 filter_complex）
        
        生成两个片段之间的转场 FFmpeg 命令片段
        
        Args:
            clip1_path: 第一个片段路径（输入标签）
            clip2_path: 第二个片段路径（输入标签）
            effect: 转场效果
            transition_duration: 转场时长（秒）
            output_label: 输出标签
            
        Returns:
            FFmpeg filter_complex 字符串
        """
        n = self._get_frame_count(transition_duration)
        
        if effect == TransitionEffect.CROSSFADE:
            return (
                f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:"
                f"offset={0}{output_label}"
            )
        elif effect == TransitionEffect.DISSOLVE:
            return (
                f"[0:v][1:v]xfade=transition=dissolve:duration={transition_duration}:"
                f"offset={0}{output_label}"
            )
        elif effect == TransitionEffect.WIPE:
            return (
                f"[0:v][1:v]xfade=transition=wipeleft:duration={transition_duration}:"
                f"offset={0}{output_label}"
            )
        elif effect == TransitionEffect.SCREEN:
            return (
                f"[0:v][1:v]blend=all_expr='min(A+(B*(1-A/255)),255)'{output_label}"
            )
        elif effect == TransitionEffect.ADD:
            return (
                f"[0:v][1:v]blend=all_expr='min(A+B,255)'{output_label}"
            )
        elif effect == TransitionEffect.GLOW:
            # 发光 = 高斯模糊 + 叠加
            return (
                f"[0:v]gblur=sigma=8[0g];"
                f"[1:v]gblur=sigma=8[1g];"
                f"[0g][1g]blend=all_expr='min(A+B,255)'{output_label}"
            )
        elif effect == TransitionEffect.HARD_CUT:
            # 硬切直接拼接
            return f"[1:v]{output_label}"
        else:
            return f"[0:v][1:v]xfade=duration={transition_duration}{output_label}"
    
    def build_xfade_chain(
        self,
        clip_labels: List[str],
        effect: TransitionEffect,
        transition_duration: float
    ) -> str:
        """
        构建多个片段的 xfade 链式转场
        
        Args:
            clip_labels: 输入标签列表，如 ['[0:v]', '[1:v]', '[2:v]']
            effect: 转场效果
            transition_duration: 转场时长（秒）
            
        Returns:
            完整的 filter 字符串
        """
        if len(clip_labels) < 2:
            return clip_labels[0] if clip_labels else ""
        
        filters = []
        current = clip_labels[0]
        
        for i, next_label in enumerate(clip_labels[1:], start=1):
            offset = i  # 每个片段的偏移量
            xfade = self.build_xfade(current, next_label, effect, transition_duration, offset)
            current = "[v" + str(i) + "]"
            filters.append(xfade)
        
        return ";".join(filters)
    
    def build_xfade(
        self,
        clip1_label: str,
        clip2_label: str,
        effect: TransitionEffect,
        duration: float,
        offset: float
    ) -> str:
        """构建单个 xfade filter"""
        transition_name = self._get_xfade_transition_name(effect)
        return (
            f"{clip1_label}{clip2_label}xfade="
            f"transition={transition_name}:"
            f"duration={duration}:"
            f"offset={offset}[v]"
        )
    
    def _get_xfade_transition_name(self, effect: TransitionEffect) -> str:
        """获取 xfade 的 transition 参数名"""
        mapping = {
            TransitionEffect.CROSSFADE: "fade",
            TransitionEffect.DISSOLVE: "dissolve",
            TransitionEffect.WIPE: "wipeleft",
            TransitionEffect.BLUR: "fade",
        }
        return mapping.get(effect, "fade")
    
    def build_concat_with_transitions(
        self,
        segments: List[Tuple[str, str, float, float]],
        transitions: List[Tuple[TransitionEffect, float]]
    ) -> str:
        """
        构建带转场的 concat filter
        
        Args:
            segments: [(label, path, start, duration), ...]
            transitions: [(effect, duration), ...] 转场效果列表（比 segments 少1个）
            
        Returns:
            FFmpeg filter_complex 字符串
        """
        filters = []
        inputs = ""
        
        # 收集所有输入
        for i, (label, path, start, duration) in enumerate(segments):
            inputs += f"-i {path} "
        
        # 构建转场链
        if len(segments) == 1:
            filters.append(f"[0:v]null[v]")
        elif len(segments) == 2:
            effect, trans_dur = transitions[0] if transitions else (TransitionEffect.HARD_CUT, 0)
            xfade = self.build_complex_transition(
                segments[0][0], segments[1][0], effect, trans_dur
            )
            filters.append(xfade)
        else:
            # 多片段：构建 filter_complex
            for i in range(len(segments) - 1):
                effect, trans_dur = transitions[i] if i < len(transitions) else (TransitionEffect.HARD_CUT, 0)
                offset = i
                filters.append(
                    f"[{i}:v][{i+1}:v]xfade="
                    f"transition={self._get_xfade_transition_name(effect)}:"
                    f"duration={trans_dur}:"
                    f"offset={offset}[v{i}]"
                )
        
        # 最终 concat
        if len(segments) > 2:
            v_labels = "[v0]" + "".join([f"[v{i}]" for i in range(1, len(segments) - 1)])
            filters.append(f"{v_labels}concat=n={len(segments) - 1}:v=1:a=0[outv]")
        elif len(segments) == 2:
            filters.append(f"[v]null[outv]")
        
        return inputs, ";".join(filters) + ";[outv]"
    
    def estimate_video_duration(
        self,
        clip_durations: List[float],
        transition_count: int,
        transition_duration: float
    ) -> float:
        """估算最终视频时长（考虑转场重叠）"""
        if not clip_durations:
            return 0.0
        
        total = sum(clip_durations)
        # 转场会重叠，所以总时长减去转场重叠的部分
        overlap = transition_count * transition_duration
        return max(0.0, total - overlap)
