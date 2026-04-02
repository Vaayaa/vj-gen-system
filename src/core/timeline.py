"""
VJ 时间线编排模块
负责片段排列、时间对齐、FFmpeg concat 文件生成
"""

import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.models.schemas import VJClip, VJTimeline as VJTimelineSchema, SectionType


@dataclass
class TimelineConfig:
    """时间线配置"""
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    audio_path: Optional[str] = None
    fade_in_duration: float = 0.0
    fade_out_duration: float = 0.0


class TimelineClip:
    """时间线片段（轻量级，不依赖 Pydantic）"""
    
    def __init__(
        self,
        clip_id: str,
        time_start: float,
        time_end: float,
        video_path: str,
        duration: Optional[float] = None,
        transition_out: Optional[str] = None,
        transition_in: Optional[str] = None,
    ):
        self.id = clip_id
        self.time_start = time_start
        self.time_end = time_end
        self.video_path = video_path
        self.duration = duration if duration is not None else (time_end - time_start)
        self.transition_out = transition_out  # 出场转场效果
        self.transition_in = transition_in    # 入场转场效果
    
    @property
    def in_point(self) -> float:
        """入点（相对于源文件的起始位置）"""
        return 0.0
    
    @property
    def out_point(self) -> float:
        """出点（相对于源文件的结束位置）"""
        return self.duration


class VJTimelineManager:
    """VJ 时间线管理器"""
    
    def __init__(self, config: TimelineConfig):
        self.clips: List[TimelineClip] = []
        self.config = config
    
    def add_clip(self, clip: TimelineClip) -> None:
        """添加片段到时间线"""
        self.clips.append(clip)
    
    def add_clips(self, clips: List[TimelineClip]) -> None:
        """批量添加片段"""
        self.clips.extend(clips)
    
    def sort_by_time(self) -> None:
        """按开始时间排序"""
        self.clips.sort(key=lambda c: c.time_start)
    
    def get_total_duration(self) -> float:
        """获取总时长"""
        if not self.clips:
            return 0.0
        return max(c.time_end for c in self.clips)
    
    def get_clips_at_time(self, time: float) -> List[TimelineClip]:
        """获取指定时间的片段"""
        return [c for c in self.clips if c.time_start <= time < c.time_end]
    
    def validate(self) -> List[str]:
        """验证时间线，返回错误列表"""
        errors = []
        
        if not self.clips:
            errors.append("时间线为空")
            return errors
        
        # 检查片段是否有有效路径
        for clip in self.clips:
            if not clip.video_path or not os.path.exists(clip.video_path):
                errors.append(f"片段 {clip.id} 视频文件不存在: {clip.video_path}")
        
        # 检查片段时间是否有效
        for clip in self.clips:
            if clip.time_start < 0:
                errors.append(f"片段 {clip.id} 开始时间不能为负数")
            if clip.time_end <= clip.time_start:
                errors.append(f"片段 {clip.id} 结束时间必须大于开始时间")
        
        # 检查片段是否有重叠（警告）
        sorted_clips = sorted(self.clips, key=lambda c: c.time_start)
        for i in range(len(sorted_clips) - 1):
            curr = sorted_clips[i]
            next_clip = sorted_clips[i + 1]
            if curr.time_end > next_clip.time_start:
                errors.append(f"片段 {curr.id} 和 {next_clip.id} 时间重叠")
        
        return errors
    
    def to_ffmpeg_concat_list(self, output_dir: Optional[str] = None) -> str:
        """
        生成 FFmpeg concat demuxer 需要的文件列表
        
        格式:
        file '/path/to/video1.mp4'
        outpoint 5.0
        file '/path/to/video2.mp4'
        outpoint 3.5
        ...
        """
        lines = []
        
        for clip in self.clips:
            lines.append(f"file '{clip.video_path}'")
            # 指定入点和出点
            lines.append(f"inpoint {clip.in_point}")
            lines.append(f"outpoint {clip.duration}")
        
        content = "\n".join(lines) + "\n"
        
        if output_dir:
            # 写入临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                dir=output_dir,
                delete=False
            ) as f:
                f.write(content)
                return f.name
        
        return content
    
    def to_simple_concat_list(self) -> str:
        """
        生成简单 concat 列表（仅文件名，用于无转场情况）
        """
        lines = [f"file '{clip.video_path}'" for clip in self.clips]
        return "\n".join(lines) + "\n"
    
    @classmethod
    def from_schema(cls, schema: VJTimelineSchema) -> "VJTimelineManager":
        """从 Pydantic 模型创建时间线"""
        config = TimelineConfig(
            resolution=schema.resolution,
            fps=schema.fps,
            audio_path=schema.audio_path,
            fade_in_duration=schema.fade_in_duration,
            fade_out_duration=schema.fade_out_duration,
        )
        manager = cls(config)
        
        for clip in schema.clips:
            if clip.video_path:
                timeline_clip = TimelineClip(
                    clip_id=clip.id,
                    time_start=clip.time_start,
                    time_end=clip.time_end,
                    video_path=clip.video_path,
                    duration=clip.metadata.duration,
                )
                manager.add_clip(timeline_clip)
        
        return manager
    
    def to_schema(self, audio_path: str) -> VJTimelineSchema:
        """转换为 Pydantic 模型"""
        schema_clips = []
        
        for clip in self.clips:
            from src.models.schemas import ClipMetadata, VJClip, TaskStatus, ShotScriptItem, MotionDesign, CameraBehavior, TransitionHint
            metadata = ClipMetadata(
                width=self.config.resolution[0],
                height=self.config.resolution[1],
                fps=self.config.fps,
                duration=clip.duration,
            )
            # 创建最小化的 script_item
            script_item = ShotScriptItem(
                id=clip.id,
                time_start=clip.time_start,
                time_end=clip.time_end,
                section_type=SectionType.VERSE,
                lyric="",
                audio_emotion="neutral",
                energy=0.5,
                visual_style="default",
                visual_prompt="",
                motion_design=MotionDesign(),
                color_palette=[],
                camera_behavior=CameraBehavior.STATIC,
                transition_hint=TransitionHint.CUT,
            )
            schema_clip = VJClip(
                id=clip.id,
                time_start=clip.time_start,
                time_end=clip.time_end,
                script_item=script_item,
                video_path=clip.video_path,
                metadata=metadata,
                generation_status=TaskStatus.COMPLETED,
            )
            schema_clips.append(schema_clip)
        
        return VJTimelineSchema(
            clips=schema_clips,
            audio_path=audio_path,
            total_duration=self.get_total_duration(),
            resolution=self.config.resolution,
            fps=self.config.fps,
            fade_in_duration=self.config.fade_in_duration,
            fade_out_duration=self.config.fade_out_duration,
        )
