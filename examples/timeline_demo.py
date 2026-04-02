"""
时间线编排示例
演示如何使用 Phase 6 实现的时间线、节拍对齐、转场效果和 FFmpeg 渲染
"""

import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.timeline import VJTimelineManager, TimelineConfig, TimelineClip
from src.core.beat_sync import BeatSync
from src.core.transitions import TransitionBuilder, TransitionEffect
from src.services.renderer import FFmpegRenderer
from src.models.schemas import AudioAnalysisResult, BeatInfo, AudioSection, SectionType


def demo_timeline():
    """演示时间线管理"""
    print("\n" + "=" * 60)
    print("1. 时间线管理演示")
    print("=" * 60)
    
    # 创建时间线配置
    config = TimelineConfig(
        resolution=(1920, 1080),
        fps=30,
        audio_path="/path/to/audio.mp3",
        fade_in_duration=1.0,
        fade_out_duration=1.0,
    )
    
    # 创建时间线管理器
    timeline = VJTimelineManager(config)
    
    # 添加片段
    clips = [
        TimelineClip(
            clip_id="clip_001",
            time_start=0.0,
            time_end=5.0,
            video_path="/media/clip1.mp4",
            duration=5.0,
        ),
        TimelineClip(
            clip_id="clip_002",
            time_start=5.0,
            time_end=10.0,
            video_path="/media/clip2.mp4",
            duration=5.0,
        ),
        TimelineClip(
            clip_id="clip_003",
            time_start=10.0,
            time_end=15.0,
            video_path="/media/clip3.mp4",
            duration=5.0,
        ),
    ]
    
    timeline.add_clips(clips)
    
    print(f"总片段数: {len(timeline.clips)}")
    print(f"总时长: {timeline.get_total_duration()} 秒")
    print(f"分辨率: {timeline.config.resolution}")
    
    # 生成 FFmpeg concat 列表
    concat_list = timeline.to_simple_concat_list()
    print("\nFFmpeg concat 列表:")
    print(concat_list)
    
    # 验证时间线
    errors = timeline.validate()
    if errors:
        print(f"验证错误: {errors}")
    else:
        print("时间线验证通过")
    
    return timeline


def demo_beat_sync():
    """演示节拍对齐"""
    print("\n" + "=" * 60)
    print("2. 节拍对齐演示")
    print("=" * 60)
    
    # 模拟音频分析结果
    beats = [
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
    
    audio_analysis = AudioAnalysisResult(
        bpm=120.0,
        time_signature="4/4",
        duration=5.0,
        beats=beats,
    )
    
    # 创建节拍同步器
    beat_sync = BeatSync(audio_analysis)
    
    # 查找最近的节拍
    test_times = [0.3, 1.2, 2.7, 3.9]
    print("\n查找最近的节拍:")
    for t in test_times:
        nearest = beat_sync.find_nearest_beat(t)
        if nearest:
            print(f"  时间 {t:.1f}s -> 节拍 {nearest.timestamp:.1f}s ({nearest.beat_type})")
    
    # 吸附到节拍
    print("\n吸附到节拍 (阈值=0.1s):")
    for t in test_times:
        aligned = beat_sync.align_time_to_beat(t, threshold=0.1)
        print(f"  时间 {t:.1f}s -> 对齐到 {aligned:.1f}s")
    
    # 获取转场点
    print("\n获取转场点 (阈值=0.1s):")
    for t in test_times:
        tp = beat_sync.get_transition_point(t, threshold=0.1)
        print(f"  时间 {t:.1f}s -> 转场点: {tp if tp else '无'}")
    
    # 检查是否在节拍上
    print("\n检查是否在节拍上 (阈值=0.05s):")
    for t in [0.0, 0.5, 1.0, 2.0, 3.0]:
        on_beat = beat_sync.is_on_beat(t, threshold=0.05)
        print(f"  时间 {t:.1f}s -> {'是' if on_beat else '否'}")
    
    return beat_sync


def demo_transitions():
    """演示转场效果构建"""
    print("\n" + "=" * 60)
    print("3. 转场效果演示")
    print("=" * 60)
    
    builder = TransitionBuilder(width=1920, height=1080, fps=30)
    
    # 测试各种转场效果
    effects = [
        TransitionEffect.CROSSFADE,
        TransitionEffect.DISSOLVE,
        TransitionEffect.SCREEN,
        TransitionEffect.ADD,
        TransitionEffect.GLOW,
        TransitionEffect.HARD_CUT,
    ]
    
    print("\n各种转场效果的 filter 字符串:")
    for effect in effects:
        filter_str = builder.build(effect, duration=0.5)
        print(f"  {effect.value}: {filter_str or '(无 filter)'}")
    
    # 构建复杂转场
    print("\n构建复杂转场 (clip1 -> clip2):")
    complex_filter = builder.build_complex_transition(
        "[0:v]", "[1:v]",
        TransitionEffect.CROSSFADE,
        transition_duration=0.5,
        output_label="[v]"
    )
    print(f"  {complex_filter}")
    
    return builder


def demo_renderer():
    """演示 FFmpeg 渲染器"""
    print("\n" + "=" * 60)
    print("4. FFmpeg 渲染器演示")
    print("=" * 60)
    
    # 检查 FFmpeg 是否可用
    available, version = FFmpegRenderer.check_ffmpeg()
    if available:
        print(f"FFmpeg 状态: {version}")
    else:
        print(f"FFmpeg 状态: {version}")
        return
    
    # 创建测试时间线
    config = TimelineConfig(
        resolution=(1920, 1080),
        fps=30,
        audio_path=None,
        fade_in_duration=0.5,
        fade_out_duration=0.5,
    )
    
    timeline = VJTimelineManager(config)
    
    # 注意：这里只是演示，实际需要真实视频文件
    # clips = [
    #     TimelineClip("clip1", 0, 5, "/path/to/video1.mp4", 5.0),
    #     TimelineClip("clip2", 5, 10, "/path/to/video2.mp4", 5.0),
    # ]
    # timeline.add_clips(clips)
    
    # 创建渲染器
    renderer = FFmpegRenderer(
        timeline,
        width=1920,
        height=1080,
        fps=30,
        crf=23,
        preset="medium",
    )
    
    print(f"渲染器配置:")
    print(f"  分辨率: {renderer.width}x{renderer.height}")
    print(f"  帧率: {renderer.fps}")
    print(f"  CRF: {renderer.crf}")
    print(f"  预设: {renderer.preset}")


def demo_end_to_end():
    """端到端演示"""
    print("\n" + "=" * 60)
    print("5. 端到端流程演示")
    print("=" * 60)
    
    # 1. 模拟音频分析
    beats = [
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
    
    audio_analysis = AudioAnalysisResult(
        bpm=120.0,
        time_signature="4/4",
        duration=5.0,
        beats=beats,
    )
    
    # 2. 创建节拍同步器
    beat_sync = BeatSync(audio_analysis)
    
    # 3. 创建时间线
    config = TimelineConfig(
        resolution=(1920, 1080),
        fps=30,
        audio_path="/music/track.mp3",
    )
    
    timeline = VJTimelineManager(config)
    
    # 4. 模拟 VJ 脚本（片段已在节拍上）
    # 但我们可以演示吸附过程
    original_times = [0.3, 1.2, 2.7, 3.9]
    aligned_times = []
    
    print("\n片段时间吸附到节拍:")
    for i, t in enumerate(original_times):
        aligned = beat_sync.align_time_to_beat(t, threshold=0.15)
        aligned_times.append(aligned)
        print(f"  clip_{i+1}: {t:.2f}s -> {aligned:.2f}s")
    
    # 5. 识别转场点
    print("\n识别的转场点:")
    transition_points = []
    for i in range(len(aligned_times) - 1):
        mid_point = (aligned_times[i] + aligned_times[i+1]) / 2
        tp = beat_sync.get_transition_point(mid_point, threshold=0.2)
        if tp:
            transition_points.append(tp)
            print(f"  转场 {i+1}: {tp:.2f}s")
    
    # 6. 构建转场效果
    builder = TransitionBuilder()
    print("\n转场效果配置:")
    print(f"  效果: {TransitionEffect.CROSSFADE.value}")
    print(f"  时长: 0.5s")
    print(f"  Filter: {builder.build(TransitionEffect.CROSSFADE, 0.5)}")


def main():
    """主函数"""
    print("=" * 60)
    print("VJ-Gen 系统 Phase 6: 时间线编排演示")
    print("=" * 60)
    
    try:
        demo_timeline()
        demo_beat_sync()
        demo_transitions()
        demo_renderer()
        demo_end_to_end()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
