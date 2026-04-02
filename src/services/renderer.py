"""
FFmpeg 渲染服务
执行时间线到最终视频的渲染
"""

import os
import subprocess
import tempfile
from typing import Callable, List, Optional, Tuple

from src.core.timeline import VJTimelineManager, TimelineConfig, TimelineClip
from src.core.transitions import TransitionBuilder, TransitionEffect


class FFmpegRenderer:
    """FFmpeg 视频渲染器"""
    
    def __init__(
        self,
        timeline: VJTimelineManager,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        crf: int = 23,
        preset: str = "medium",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
    ):
        self.timeline = timeline
        self.width = width
        self.height = height
        self.fps = fps
        self.crf = crf
        self.preset = preset
        self.audio_codec = audio_codec
        self.audio_bitrate = audio_bitrate
        self.transition_builder = TransitionBuilder(width, height, fps)
    
    def render(
        self,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[bool, str]:
        """
        渲染完整时间线（简单 concat，无转场）
        
        Args:
            output_path: 输出文件路径
            progress_callback: 进度回调函数，参数为 0-1 的进度值
            
        Returns:
            (是否成功, 错误信息)
        """
        # 验证时间线
        errors = self.timeline.validate()
        if errors:
            return False, f"时间线验证失败: {', '.join(errors)}"
        
        if not self.timeline.clips:
            return False, "时间线为空"
        
        # 创建临时文件存储 concat 列表
        with tempfile.TemporaryDirectory() as tmpdir:
            concat_list = self.timeline.to_ffmpeg_concat_list(tmpdir)
            concat_file = os.path.join(tmpdir, "concat_list.txt")
            
            with open(concat_file, 'w') as f:
                f.write(concat_list)
            
            # 构建 FFmpeg 命令
            cmd = self._build_concat_cmd(concat_file, output_path)
            
            # 执行渲染
            success, error = self._run_ffmpeg(cmd, progress_callback)
            
            return success, error
    
    def render_with_transitions(
        self,
        output_path: str,
        transition_effect: TransitionEffect = TransitionEffect.CROSSFADE,
        transition_duration: float = 0.5,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[bool, str]:
        """
        渲染带转场的时间线
        
        Args:
            output_path: 输出文件路径
            transition_effect: 转场效果类型
            transition_duration: 转场时长（秒）
            progress_callback: 进度回调
            
        Returns:
            (是否成功, 错误信息)
        """
        errors = self.timeline.validate()
        if errors:
            return False, f"时间线验证失败: {', '.join(errors)}"
        
        if len(self.timeline.clips) < 2:
            # 单片段，直接复制
            return self.render(output_path, progress_callback)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 构建 filter_complex
            filter_complex = self._build_xfade_filter(
                transition_effect, transition_duration
            )
            
            # 构建输入参数
            inputs = []
            for clip in self.timeline.clips:
                inputs.extend(["-i", clip.video_path])
            
            # 构建命令
            cmd = self._build_xfade_cmd(
                inputs, filter_complex, output_path,
                self.timeline.config.audio_path
            )
            
            success, error = self._run_ffmpeg(cmd, progress_callback)
            return success, error
    
    def render_preview(
        self,
        start: float,
        end: float,
        output_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        渲染预览片段
        
        Args:
            start: 开始时间（秒）
            end: 结束时间（秒）
            output_path: 输出路径，None 则生成临时文件
            
        Returns:
            (是否成功, 错误信息, 输出路径)
        """
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp4")
        
        # 找出范围内的片段
        clips_in_range = [
            clip for clip in self.timeline.clips
            if clip.time_start < end and clip.time_end > start
        ]
        
        if not clips_in_range:
            return False, "指定时间范围内没有片段", None
        
        # 对片段进行裁剪以适应范围
        trimmed_clips = self._trim_clips_to_range(clips_in_range, start, end)
        
        # 创建临时时间线
        from src.core.timeline import VJTimelineManager, TimelineConfig
        config = TimelineConfig(
            resolution=(self.width, self.height),
            fps=self.fps,
        )
        temp_timeline = VJTimelineManager(config)
        temp_timeline.add_clips(trimmed_clips)
        
        # 渲染
        renderer = FFmpegRenderer(
            temp_timeline,
            width=self.width,
            height=self.height,
            fps=self.fps,
            crf=self.crf,
            preset=self.preset,
        )
        
        success, error = renderer.render(output_path)
        return success, error, output_path if success else None
    
    def _trim_clips_to_range(
        self,
        clips: List[TimelineClip],
        start: float,
        end: float
    ) -> List[TimelineClip]:
        """将片段裁剪到指定时间范围"""
        trimmed = []
        
        for clip in clips:
            clip_start = max(clip.time_start, start)
            clip_end = min(clip.time_end, end)
            
            if clip_end > clip_start:
                # 计算在源文件中的偏移
                source_offset = clip_start - clip.time_start
                
                new_clip = TimelineClip(
                    clip_id=clip.id,
                    time_start=0,
                    time_end=clip_end - clip_start,
                    video_path=clip.video_path,
                    duration=clip.duration,  # 保持源时长不变
                )
                trimmed.append(new_clip)
        
        return trimmed
    
    def _build_concat_cmd(self, concat_file: str, output_path: str) -> List[str]:
        """构建简单 concat 命令"""
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264",
            "-crf", str(self.crf),
            "-preset", self.preset,
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-s", f"{self.width}x{self.height}",
        ]
        
        # 添加音频（如果有）
        if self.timeline.config.audio_path and os.path.exists(self.timeline.config.audio_path):
            cmd.extend([
                "-i", self.timeline.config.audio_path,
                "-c:a", self.audio_codec,
                "-b:a", self.audio_bitrate,
            ])
        else:
            cmd.append("-an")
        
        # 添加淡入淡出
        if self.timeline.config.fade_in_duration > 0:
            fade_in_frames = int(self.timeline.config.fade_in_duration * self.fps)
            cmd.extend(["-vf", f"fade=t=in:st=0:d={fade_in_frames}"])
        
        if self.timeline.config.fade_out_duration > 0:
            total_duration = self.timeline.get_total_duration()
            fade_out_start = total_duration - self.timeline.config.fade_out_duration
            cmd.extend([
                "-vf", f"fade=t=out:st={fade_out_start}:d={self.timeline.config.fade_out_duration}"
            ])
        
        cmd.append(output_path)
        return cmd
    
    def _build_xfade_filter(
        self,
        effect: TransitionEffect,
        duration: float
    ) -> str:
        """构建 xfade filter 字符串"""
        n = len(self.timeline.clips)
        filters = []
        
        for i in range(n - 1):
            offset = i
            filter_str = self.transition_builder.build_xfade(
                f"[{i}:v]", f"[{i+1}:v]",
                effect, duration, offset
            )
            filters.append(filter_str)
        
        # 添加最终的 null filter 和 concat
        filters.append(f"[v{n-1}]null[vout]")
        
        return ";".join(filters)
    
    def _build_xfade_cmd(
        self,
        inputs: List[str],
        filter_complex: str,
        output_path: str,
        audio_path: Optional[str]
    ) -> List[str]:
        """构建 xfade 命令"""
        cmd = ["ffmpeg", "-y"] + inputs
        
        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])
            filter_complex += f";[outv][{len(inputs)//2}:a]concat=n=1:v=1:a=1[out]"
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", f"[{len(inputs)//2}:a]",
            ])
        else:
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
            ])
        
        cmd.extend([
            "-c:v", "libx264",
            "-crf", str(self.crf),
            "-preset", self.preset,
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-c:a", self.audio_codec,
            "-b:a", self.audio_bitrate,
            output_path,
        ])
        
        return cmd
    
    def _run_ffmpeg(
        self,
        cmd: List[str],
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[bool, str]:
        """执行 FFmpeg 命令"""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 解析进度
            total_duration = self.timeline.get_total_duration()
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                if progress_callback and "time=" in line:
                    try:
                        # 解析时间: time=00:01:23.45
                        time_str = line.split("time=")[1].split()[0]
                        parts = time_str.split(":")
                        if len(parts) == 3:
                            current_time = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                            progress = min(current_time / total_duration, 1.0)
                            progress_callback(progress)
                    except (IndexError, ValueError):
                        pass
            
            returncode = process.wait()
            
            if returncode == 0:
                return True, ""
            else:
                stderr = process.stderr.read()
                return False, f"FFmpeg 错误: {stderr}"
                
        except FileNotFoundError:
            return False, "FFmpeg 未安装或不在 PATH 中"
        except Exception as e:
            return False, f"渲染失败: {str(e)}"
    
    @staticmethod
    def check_ffmpeg() -> Tuple[bool, str]:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode == 0:
                version = result.stdout.decode().split("\n")[0]
                return True, version
            return False, "FFmpeg 不可用"
        except FileNotFoundError:
            return False, "FFmpeg 未安装"
