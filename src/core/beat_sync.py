"""
节拍对齐模块
基于音频分析结果，实现片段与节拍的智能对齐
"""

from typing import List, Optional, Tuple

from src.models.schemas import AudioAnalysisResult, BeatInfo, VJClip


class BeatSync:
    """节拍同步器"""
    
    def __init__(self, audio_analysis: AudioAnalysisResult):
        self.audio_analysis = audio_analysis
        self.beats: List[BeatInfo] = audio_analysis.beats
    
    def find_nearest_beat(self, time: float) -> Optional[BeatInfo]:
        """
        找到最近的节拍
        
        Args:
            time: 时间点（秒）
            
        Returns:
            最近的节拍信息，如果无节拍则返回 None
        """
        if not self.beats:
            return None
        
        nearest = None
        min_diff = float('inf')
        
        for beat in self.beats:
            diff = abs(beat.timestamp - time)
            if diff < min_diff:
                min_diff = diff
                nearest = beat
        
        return nearest
    
    def find_nearest_beat_time(self, time: float) -> Optional[float]:
        """找到最近的节拍时间点"""
        beat = self.find_nearest_beat(time)
        return beat.timestamp if beat else None
    
    def get_beats_in_range(self, start: float, end: float) -> List[BeatInfo]:
        """获取时间范围内的所有节拍"""
        return [
            beat for beat in self.beats
            if start <= beat.timestamp <= end
        ]
    
    def get_downbeats_in_range(self, start: float, end: float) -> List[BeatInfo]:
        """获取时间范围内的强拍（下沉）"""
        return [
            beat for beat in self.beats
            if start <= beat.timestamp <= end and beat.beat_type == "downbeat"
        ]
    
    def align_time_to_beat(self, time: float, threshold: float = 0.1) -> float:
        """
        将时间对齐到最近的节拍
        
        Args:
            time: 原始时间
            threshold: 对齐阈值（秒），超过此值则不强制对齐
            
        Returns:
            对齐后的时间
        """
        nearest_beat = self.find_nearest_beat(time)
        if nearest_beat is None:
            return time
        
        if abs(nearest_beat.timestamp - time) <= threshold:
            return nearest_beat.timestamp
        
        return time
    
    def align_clip_to_beat(self, clip: VJClip, align_start: bool = True) -> VJClip:
        """
        将片段对齐到最近的节拍
        
        Args:
            clip: VJ 片段
            align_start: 是否对齐开始时间，False 则对齐结束时间
            
        Returns:
            对齐后的新片段（不修改原片段）
        """
        if align_start:
            new_start = self.align_time_to_beat(clip.time_start)
            duration = clip.time_end - clip.time_start
            new_end = new_start + duration
        else:
            new_end = self.align_time_to_beat(clip.time_end)
            duration = clip.time_end - clip.time_start
            new_start = new_end - duration
        
        # 创建新片段（浅拷贝相关属性）
        aligned_clip = clip.model_copy()
        aligned_clip.time_start = new_start
        aligned_clip.time_end = new_end
        
        return aligned_clip
    
    def align_clips_to_beats(self, clips: List[VJClip], align_starts: bool = True) -> List[VJClip]:
        """批量对齐片段到节拍"""
        return [self.align_clip_to_beat(clip, align_starts) for clip in clips]
    
    def get_transition_point(
        self,
        time: float,
        threshold: float = 0.1
    ) -> Optional[float]:
        """
        获取转场点（节拍交界处）
        
        当时间接近某个节拍时，返回该节拍时间作为转场点
        
        Args:
            time: 时间点
            threshold: 阈值，超过此值则返回 None
            
        Returns:
            转场点时间，如果不在节拍附近则返回 None
        """
        nearest_beat = self.find_nearest_beat(time)
        if nearest_beat is None:
            return None
        
        if abs(nearest_beat.timestamp - time) <= threshold:
            return nearest_beat.timestamp
        
        return None
    
    def find_beat_before(self, time: float) -> Optional[BeatInfo]:
        """找到指定时间之前的最后一个节拍"""
        before_beats = [b for b in self.beats if b.timestamp < time]
        return before_beats[-1] if before_beats else None
    
    def find_beat_after(self, time: float) -> Optional[BeatInfo]:
        """找到指定时间之后的第一个节拍"""
        after_beats = [b for b in self.beats if b.timestamp > time]
        return after_beats[0] if after_beats else None
    
    def get_beat_interval(self, time: float) -> Optional[Tuple[float, float]]:
        """
        获取指定时间所在节拍区间
        
        Returns:
            (前一个节拍时间, 后一个节拍时间) 或 None
        """
        before = self.find_beat_before(time)
        after = self.find_beat_after(time)
        
        if before and after:
            return (before.timestamp, after.timestamp)
        return None
    
    def is_on_beat(self, time: float, threshold: float = 0.05) -> bool:
        """判断时间点是否在节拍上"""
        return self.get_transition_point(time, threshold) is not None
    
    def snap_to_beat(
        self,
        time: float,
        mode: str = "nearest"
    ) -> float:
        """
        吸附到节拍
        
        Args:
            time: 时间点
            mode: 吸附模式
                - "nearest": 最近节拍
                - "before": 之前的节拍
                - "after": 之后的节拍
                
        Returns:
            吸附后的时间
        """
        if mode == "nearest":
            return self.find_nearest_beat_time(time) or time
        elif mode == "before":
            beat = self.find_beat_before(time)
            return beat.timestamp if beat else time
        elif mode == "after":
            beat = self.find_beat_after(time)
            return beat.timestamp if beat else time
        else:
            return time
