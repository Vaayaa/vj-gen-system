"""
时间线编排模块测试
测试 Timeline、BeatSync、Transitions 和 Renderer
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.timeline import VJTimelineManager, TimelineConfig, TimelineClip
from src.core.beat_sync import BeatSync
from src.core.transitions import TransitionBuilder, TransitionEffect
from src.services.renderer import FFmpegRenderer
from src.models.schemas import AudioAnalysisResult, BeatInfo, VJClip, ClipMetadata, ShotScriptItem, SectionType, TaskStatus


class TestTimelineClip(unittest.TestCase):
    """测试 TimelineClip"""
    
    def test_clip_creation(self):
        """测试片段创建"""
        clip = TimelineClip(
            clip_id="test_001",
            time_start=0.0,
            time_end=5.0,
            video_path="/path/to/video.mp4",
            duration=5.0,
        )
        
        self.assertEqual(clip.id, "test_001")
        self.assertEqual(clip.time_start, 0.0)
        self.assertEqual(clip.time_end, 5.0)
        self.assertEqual(clip.duration, 5.0)
        self.assertEqual(clip.in_point, 0.0)
        self.assertEqual(clip.out_point, 5.0)
    
    def test_clip_default_duration(self):
        """测试默认时长计算"""
        clip = TimelineClip(
            clip_id="test_002",
            time_start=2.0,
            time_end=7.0,
            video_path="/path/to/video.mp4",
        )
        
        self.assertEqual(clip.duration, 5.0)


class TestVJTimelineManager(unittest.TestCase):
    """测试 VJTimelineManager"""
    
    def setUp(self):
        """设置测试时间线"""
        self.config = TimelineConfig(
            resolution=(1920, 1080),
            fps=30,
            audio_path="/path/to/audio.mp3",
        )
        self.timeline = VJTimelineManager(self.config)
        
        self.clips = [
            TimelineClip("clip_001", 0.0, 5.0, "/media/v1.mp4", 5.0),
            TimelineClip("clip_002", 5.0, 10.0, "/media/v2.mp4", 5.0),
            TimelineClip("clip_003", 10.0, 15.0, "/media/v3.mp4", 5.0),
        ]
    
    def test_add_clip(self):
        """测试添加片段"""
        self.timeline.add_clip(self.clips[0])
        self.assertEqual(len(self.timeline.clips), 1)
    
    def test_add_clips(self):
        """测试批量添加"""
        self.timeline.add_clips(self.clips)
        self.assertEqual(len(self.timeline.clips), 3)
    
    def test_sort_by_time(self):
        """测试按时间排序"""
        # 添加乱序的片段
        out_of_order = [
            TimelineClip("c", 10.0, 15.0, "/v3.mp4", 5.0),
            TimelineClip("a", 0.0, 5.0, "/v1.mp4", 5.0),
            TimelineClip("b", 5.0, 10.0, "/v2.mp4", 5.0),
        ]
        self.timeline.add_clips(out_of_order)
        
        self.timeline.sort_by_time()
        
        self.assertEqual(self.timeline.clips[0].id, "a")
        self.assertEqual(self.timeline.clips[1].id, "b")
        self.assertEqual(self.timeline.clips[2].id, "c")
    
    def test_get_total_duration(self):
        """测试获取总时长"""
        self.timeline.add_clips(self.clips)
        self.assertEqual(self.timeline.get_total_duration(), 15.0)
    
    def test_get_total_duration_empty(self):
        """测试空时间线的总时长"""
        self.assertEqual(self.timeline.get_total_duration(), 0.0)
    
    def test_get_clips_at_time(self):
        """测试获取指定时间的片段"""
        self.timeline.add_clips(self.clips)
        
        clips_at_2s = self.timeline.get_clips_at_time(2.0)
        self.assertEqual(len(clips_at_2s), 1)
        self.assertEqual(clips_at_2s[0].id, "clip_001")
        
        clips_at_5s = self.timeline.get_clips_at_time(5.0)
        self.assertEqual(len(clips_at_5s), 1)
        self.assertEqual(clips_at_5s[0].id, "clip_002")
    
    def test_validate_empty(self):
        """测试空时间线验证"""
        errors = self.timeline.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("空", errors[0])
    
    def test_validate_negative_time(self):
        """测试负时间验证"""
        bad_clip = TimelineClip("bad", -1.0, 5.0, "/v.mp4", 6.0)
        self.timeline.add_clip(bad_clip)
        
        errors = self.timeline.validate()
        self.assertTrue(any("负数" in e for e in errors))
    
    def test_validate_end_before_start(self):
        """测试结束时间早于开始时间"""
        bad_clip = TimelineClip("bad", 5.0, 3.0, "/v.mp4", -2.0)
        self.timeline.add_clip(bad_clip)
        
        errors = self.timeline.validate()
        self.assertTrue(any("大于开始时间" in e for e in errors))
    
    def test_to_ffmpeg_concat_list(self):
        """测试生成 FFmpeg concat 列表"""
        self.timeline.add_clips(self.clips)
        
        content = self.timeline.to_simple_concat_list()
        
        self.assertIn("file '/media/v1.mp4'", content)
        self.assertIn("file '/media/v2.mp4'", content)
        self.assertIn("file '/media/v3.mp4'", content)
    
    def test_to_ffmpeg_concat_list_with_points(self):
        """测试生成带入点出点的 concat 列表"""
        self.timeline.add_clips(self.clips)
        
        content = self.timeline.to_ffmpeg_concat_list()
        
        self.assertIn("inpoint", content)
        self.assertIn("outpoint", content)


class TestBeatSync(unittest.TestCase):
    """测试 BeatSync"""
    
    def setUp(self):
        """设置测试数据"""
        self.beats = [
            BeatInfo(timestamp=0.0, beat_type="downbeat", strength=1.0),
            BeatInfo(timestamp=0.5, beat_type="beat", strength=0.8),
            BeatInfo(timestamp=1.0, beat_type="beat", strength=0.8),
            BeatInfo(timestamp=1.5, beat_type="offbeat", strength=0.5),
            BeatInfo(timestamp=2.0, beat_type="beat", strength=0.8),
            BeatInfo(timestamp=2.5, beat_type="beat", strength=0.8),
            BeatInfo(timestamp=3.0, beat_type="downbeat", strength=1.0),
            BeatInfo(timestamp=3.5, beat_type="beat", strength=0.8),
            BeatInfo(timestamp=4.0, beat_type="beat", strength=0.8),
            BeatInfo(timestamp=4.5, beat_type="offbeat", strength=0.5),
            BeatInfo(timestamp=5.0, beat_type="beat", strength=0.8),
        ]
        
        self.audio_analysis = AudioAnalysisResult(
            bpm=120.0,
            time_signature="4/4",
            duration=5.0,
            beats=self.beats,
        )
        
        self.beat_sync = BeatSync(self.audio_analysis)
    
    def test_find_nearest_beat(self):
        """测试查找最近节拍"""
        # 接近 0.5 (0.3 is 0.2 away from 0.5, 0.3 away from 0.0)
        nearest = self.beat_sync.find_nearest_beat(0.3)
        self.assertEqual(nearest.timestamp, 0.5)
        
        nearest = self.beat_sync.find_nearest_beat(0.7)
        self.assertEqual(nearest.timestamp, 0.5)
        
        # 接近中间 (1.3 is 0.2 away from 1.5, 0.3 away from 1.0)
        nearest = self.beat_sync.find_nearest_beat(1.3)
        self.assertEqual(nearest.timestamp, 1.5)
    
    def test_find_nearest_beat_time(self):
        """测试查找最近节拍时间"""
        # 1.25 is closer to 1.0 (diff=0.25) than 1.5 (diff=0.25) - equal, takes first
        time = self.beat_sync.find_nearest_beat_time(1.25)
        self.assertEqual(time, 1.0)
    
    def test_get_beats_in_range(self):
        """测试获取范围内的节拍"""
        beats = self.beat_sync.get_beats_in_range(1.0, 3.0)
        self.assertEqual(len(beats), 5)  # 1.0, 1.5, 2.0, 2.5, 3.0
    
    def test_get_downbeats_in_range(self):
        """测试获取范围内的强拍"""
        beats = self.beat_sync.get_downbeats_in_range(0.0, 5.0)
        self.assertEqual(len(beats), 2)  # 0.0, 3.0
    
    def test_align_time_to_beat(self):
        """测试时间对齐"""
        # 0.3 -> nearest beat is 0.5, diff=0.2, within threshold 0.2
        aligned = self.beat_sync.align_time_to_beat(0.3, threshold=0.2)
        self.assertEqual(aligned, 0.5)
        
        # 超过阈值，不对齐
        aligned = self.beat_sync.align_time_to_beat(0.8, threshold=0.1)
        self.assertEqual(aligned, 0.8)
    
    def test_get_transition_point(self):
        """测试获取转场点"""
        # 0.3 is close to beat 0.5 (diff=0.2 <= threshold 0.2)
        tp = self.beat_sync.get_transition_point(0.3, threshold=0.2)
        self.assertEqual(tp, 0.5)
        
        # 不在节拍附近
        tp = self.beat_sync.get_transition_point(0.8, threshold=0.1)
        self.assertIsNone(tp)
    
    def test_is_on_beat(self):
        """测试判断是否在节拍上"""
        self.assertTrue(self.beat_sync.is_on_beat(0.0, threshold=0.05))
        self.assertTrue(self.beat_sync.is_on_beat(0.5, threshold=0.05))
        self.assertFalse(self.beat_sync.is_on_beat(0.3, threshold=0.05))
    
    def test_find_beat_before(self):
        """测试查找之前的节拍"""
        beat = self.beat_sync.find_beat_before(2.3)
        self.assertEqual(beat.timestamp, 2.0)
    
    def test_find_beat_after(self):
        """测试查找之后的节拍"""
        beat = self.beat_sync.find_beat_after(2.3)
        self.assertEqual(beat.timestamp, 2.5)
    
    def test_snap_to_beat_nearest(self):
        """测试吸附到最近节拍"""
        # 2.3 is closer to 2.5 (diff=0.2) than 2.0 (diff=0.3)
        snapped = self.beat_sync.snap_to_beat(2.3, mode="nearest")
        self.assertEqual(snapped, 2.5)
    
    def test_snap_to_beat_before(self):
        """测试吸附到之前的节拍"""
        snapped = self.beat_sync.snap_to_beat(2.3, mode="before")
        self.assertEqual(snapped, 2.0)
    
    def test_snap_to_beat_after(self):
        """测试吸附到之后的节拍"""
        snapped = self.beat_sync.snap_to_beat(2.3, mode="after")
        self.assertEqual(snapped, 2.5)


class TestTransitionBuilder(unittest.TestCase):
    """测试 TransitionBuilder"""
    
    def setUp(self):
        """设置测试构建器"""
        self.builder = TransitionBuilder(width=1920, height=1080, fps=30)
    
    def test_build_crossfade(self):
        """测试构建交叉淡化"""
        filter_str = self.builder.build(TransitionEffect.CROSSFADE, 0.5)
        self.assertIn("crossfade", filter_str)
    
    def test_build_hard_cut(self):
        """测试构建硬切"""
        filter_str = self.builder.build(TransitionEffect.HARD_CUT, 0.5)
        self.assertEqual(filter_str, "")
    
    def test_build_glow(self):
        """测试构建发光效果"""
        filter_str = self.builder.build(TransitionEffect.GLOW, 0.5)
        self.assertIn("gblur", filter_str)
    
    def test_build_screen(self):
        """测试构建屏幕混合"""
        filter_str = self.builder.build(TransitionEffect.SCREEN, 0.5)
        self.assertIn("blend", filter_str)
    
    def test_frame_count_calculation(self):
        """测试帧数计算"""
        # 30fps * 0.5s = 15 frames
        n = self.builder._get_frame_count(0.5)
        self.assertEqual(n, 15)
    
    def test_build_complex_transition_crossfade(self):
        """测试构建复杂交叉淡化"""
        result = self.builder.build_complex_transition(
            "[0:v]", "[1:v]",
            TransitionEffect.CROSSFADE,
            0.5,
            "[v]"
        )
        self.assertIn("xfade", result)
        self.assertIn("transition=fade", result)
    
    def test_build_complex_transition_hard_cut(self):
        """测试构建复杂硬切"""
        result = self.builder.build_complex_transition(
            "[0:v]", "[1:v]",
            TransitionEffect.HARD_CUT,
            0.0,
            "[v]"
        )
        self.assertEqual(result, "[1:v][v]")
    
    def test_estimate_duration(self):
        """测试时长估算"""
        durations = [5.0, 5.0, 5.0]
        estimated = self.builder.estimate_video_duration(durations, 2, 0.5)
        # 15 - 2*0.5 = 14
        self.assertEqual(estimated, 14.0)


class TestFFmpegRenderer(unittest.TestCase):
    """测试 FFmpegRenderer"""
    
    def setUp(self):
        """设置测试渲染器"""
        config = TimelineConfig(
            resolution=(1920, 1080),
            fps=30,
        )
        self.timeline = VJTimelineManager(config)
        
        self.renderer = FFmpegRenderer(
            self.timeline,
            width=1920,
            height=1080,
            fps=30,
            crf=23,
        )
    
    def test_renderer_creation(self):
        """测试渲染器创建"""
        self.assertEqual(self.renderer.width, 1920)
        self.assertEqual(self.renderer.height, 1080)
        self.assertEqual(self.renderer.fps, 30)
        self.assertEqual(self.renderer.crf, 23)
    
    @patch("subprocess.run")
    def test_check_ffmpeg_available(self, mock_run):
        """测试检查 FFmpeg 可用"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"ffmpeg version 5.0",
        )
        
        available, version = FFmpegRenderer.check_ffmpeg()
        self.assertTrue(available)
    
    @patch("subprocess.run")
    def test_check_ffmpeg_unavailable(self, mock_run):
        """测试 FFmpeg 不可用"""
        mock_run.side_effect = FileNotFoundError()
        
        available, msg = FFmpegRenderer.check_ffmpeg()
        self.assertFalse(available)
        self.assertIn("未安装", msg)
    
    def test_build_concat_cmd(self):
        """测试构建 concat 命令"""
        clip = TimelineClip("test", 0.0, 5.0, "/v.mp4", 5.0)
        self.timeline.add_clip(clip)
        
        # 创建临时文件存储 concat 列表
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            concat_file = os.path.join(tmpdir, "concat.txt")
            with open(concat_file, 'w') as f:
                f.write("file '/v.mp4'\n")
            
            cmd = self.renderer._build_concat_cmd(concat_file, "/out.mp4")
            
            self.assertIn("ffmpeg", cmd)
            self.assertIn("-y", cmd)
            self.assertIn("-f", cmd)
            self.assertIn("concat", cmd)
            self.assertIn("/out.mp4", cmd)
    
    def test_build_xfade_filter(self):
        """测试构建 xfade filter"""
        clips = [
            TimelineClip("c1", 0.0, 5.0, "/v1.mp4", 5.0),
            TimelineClip("c2", 5.0, 10.0, "/v2.mp4", 5.0),
        ]
        self.timeline.add_clips(clips)
        
        filter_str = self.renderer._build_xfade_filter(
            TransitionEffect.CROSSFADE,
            0.5
        )
        
        self.assertIn("xfade", filter_str)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_timeline_to_schema_conversion(self):
        """测试时间线与 Schema 互相转换"""
        from src.models.schemas import VJTimeline as VJTimelineSchema
        
        # 创建 TimelineManager
        config = TimelineConfig(
            resolution=(1920, 1080),
            fps=30,
            audio_path="/music.mp3",
        )
        manager = VJTimelineManager(config)
        manager.add_clip(TimelineClip("c1", 0, 5, "/v1.mp4", 5.0))
        
        # 转换为 Schema
        schema = manager.to_schema("/music.mp3")
        
        self.assertEqual(len(schema.clips), 1)
        self.assertEqual(schema.audio_path, "/music.mp3")
        self.assertEqual(schema.resolution, (1920, 1080))
        self.assertEqual(schema.fps, 30)


if __name__ == "__main__":
    unittest.main()
