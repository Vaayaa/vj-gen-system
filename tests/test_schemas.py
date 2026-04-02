"""
VJ-Gen Phase 1 测试：核心数据模型
"""

import pytest
from datetime import datetime

from src.models.schemas import (
    # Enums
    TaskStatus,
    SectionType,
    LyricSentiment,
    AspectRatio,
    OutputFormat,
    # Task models
    TaskNode,
    Workflow,
    # Audio models
    EnergyPoint,
    AudioSection,
    BeatInfo,
    AudioAnalysisResult,
    # Lyric models
    LyricLine,
    LyricAnalysis,
    # Shot script models
    MotionDesign,
    ShotScriptItem,
    ShotScript,
    # Clip models
    ClipMetadata,
    VJClip,
    # Timeline models
    VJTimeline,
    # Render models
    RenderProfile,
    # Project models
    ProjectStatus,
    Project,
    # API models
    APIResponse,
    ProjectCreateRequest,
)


class TestEnums:
    """测试枚举类型"""

    def test_task_status(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_section_type(self):
        assert SectionType.INTRO.value == "intro"
        assert SectionType.CHORUS.value == "chorus"
        assert SectionType.DROP.value == "drop"

    def test_lyric_sentiment(self):
        assert LyricSentiment.CALM.value == "calm"
        assert LyricSentiment.CLIMAX.value == "climax"

    def test_aspect_ratio(self):
        assert AspectRatio.RATIO_16_9.value == "16:9"
        assert AspectRatio.RATIO_9_16.value == "9:16"
        assert AspectRatio.RATIO_1_1.value == "1:1"

    def test_output_format(self):
        assert OutputFormat.MP4.value == "mp4"
        assert OutputFormat.WEBM.value == "webm"


class TestTaskModels:
    """测试任务模型"""

    def test_task_node_creation(self):
        node = TaskNode(
            id="test-node-1",
            type="audio_analysis",
            input_data={"audio_path": "/path/to/audio.mp3"},
        )
        assert node.id == "test-node-1"
        assert node.type == "audio_analysis"
        assert node.status == TaskStatus.PENDING
        assert node.retry_count == 0
        assert len(node.depends_on) == 0

    def test_task_node_status_transition(self):
        node = TaskNode(id="test", type="audio_analysis")
        node.status = TaskStatus.RUNNING
        assert node.status == TaskStatus.RUNNING
        node.status = TaskStatus.COMPLETED
        assert node.status == TaskStatus.COMPLETED

    def test_workflow_creation(self):
        workflow = Workflow(
            id="workflow-1",
            name="Test Workflow",
        )
        assert workflow.id == "workflow-1"
        assert len(workflow.nodes) == 0

    def test_workflow_add_nodes(self):
        workflow = Workflow(id="wf-1", name="Test")
        node1 = TaskNode(id="node-1", type="audio_analysis")
        node2 = TaskNode(id="node-2", type="lyric_nlp", depends_on=["node-1"])
        workflow.nodes.extend([node1, node2])
        
        assert len(workflow.nodes) == 2
        assert workflow.get_node("node-1") == node1
        assert workflow.get_node("node-2") == node2
        assert workflow.get_node("node-999") is None

    def test_workflow_get_ready_nodes(self):
        workflow = Workflow(id="wf-1", name="Test")
        node1 = TaskNode(id="node-1", type="audio_analysis")
        node2 = TaskNode(id="node-2", type="lyric_nlp", depends_on=["node-1"])
        node3 = TaskNode(id="node-3", type="shot_script", depends_on=["node-2"])
        workflow.nodes.extend([node1, node2, node3])
        
        # Initially only node1 is ready
        ready = workflow.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "node-1"
        
        # Complete node1, node2 becomes ready
        node1.status = TaskStatus.COMPLETED
        ready = workflow.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "node-2"


class TestAudioModels:
    """测试音频模型"""

    def test_energy_point(self):
        point = EnergyPoint(timestamp=1.5, energy=0.8)
        assert point.timestamp == 1.5
        assert point.energy == 0.8

    def test_audio_section(self):
        section = AudioSection(
            start=0.0,
            end=30.0,
            type=SectionType.INTRO,
            energy=0.5,
            mood=["calm", "dark"],
        )
        assert section.start == 0.0
        assert section.end == 30.0
        assert section.type == SectionType.INTRO

    def test_beat_info(self):
        beat = BeatInfo(timestamp=0.5, beat_type="downbeat", strength=1.0)
        assert beat.timestamp == 0.5
        assert beat.beat_type == "downbeat"

    def test_audio_analysis_result(self):
        result = AudioAnalysisResult(
            bpm=120.0,
            time_signature="4/4",
            duration=180.0,
            sections=[
                AudioSection(
                    start=0.0,
                    end=30.0,
                    type=SectionType.INTRO,
                    energy=0.3,
                )
            ],
            beats=[
                BeatInfo(timestamp=0.5, strength=1.0),
            ],
        )
        assert result.bpm == 120.0
        assert result.duration == 180.0
        assert len(result.sections) == 1
        assert len(result.beats) == 1


class TestLyricModels:
    """测试歌词模型"""

    def test_lyric_line(self):
        line = LyricLine(
            start_time=0.0,
            end_time=3.0,
            text="Hello world",
            sentiment=LyricSentiment.CALM,
            keywords=["hello", "world"],
            imagery=["sunrise"],
        )
        assert line.text == "Hello world"
        assert line.sentiment == LyricSentiment.CALM

    def test_lyric_analysis(self):
        analysis = LyricAnalysis(
            lines=[
                LyricLine(
                    start_time=0.0,
                    end_time=3.0,
                    text="Test line",
                    sentiment=LyricSentiment.BRIGHT,
                )
            ],
            language="en",
            overall_mood=LyricSentiment.BRIGHT,
            themes=["love", "hope"],
        )
        assert len(analysis.lines) == 1
        assert analysis.language == "en"


class TestShotScriptModels:
    """测试镜头脚本模型"""

    def test_motion_design(self):
        motion = MotionDesign(
            primary_motion="zoom",
            secondary_motion="pan",
            motion_intensity=0.7,
            motion_direction="left",
        )
        assert motion.primary_motion == "zoom"
        assert motion.motion_intensity == 0.7

    def test_shot_script_item(self):
        item = ShotScriptItem(
            id="shot-1",
            time_start=0.0,
            time_end=5.0,
            section_type=SectionType.INTRO,
            lyric="Test lyrics",
            audio_emotion="calm",
            energy=0.3,
            visual_style="cinematic",
            visual_prompt="A peaceful landscape",
            color_palette=["#000000", "#FFFFFF"],
        )
        assert item.id == "shot-1"
        assert item.energy == 0.3

    def test_shot_script(self):
        script = ShotScript(
            items=[
                ShotScriptItem(
                    id="shot-1",
                    time_start=0.0,
                    time_end=5.0,
                    section_type=SectionType.INTRO,
                    energy=0.3,
                    visual_style="cinematic",
                    visual_prompt="test",
                )
            ],
            total_duration=5.0,
            resolution=(1920, 1080),
            fps=30,
        )
        assert len(script.items) == 1
        assert script.total_duration == 5.0


class TestClipModels:
    """测试片段模型"""

    def test_clip_metadata(self):
        metadata = ClipMetadata(
            width=1920,
            height=1080,
            fps=30,
            duration=5.0,
            codec="h264",
            bitrate=5000000,
        )
        assert metadata.width == 1920
        assert metadata.bitrate == 5000000

    def test_vj_clip(self):
        clip = VJClip(
            id="clip-1",
            time_start=0.0,
            time_end=5.0,
            script_item=ShotScriptItem(
                id="shot-1",
                time_start=0.0,
                time_end=5.0,
                section_type=SectionType.INTRO,
                energy=0.3,
                visual_style="test",
                visual_prompt="test",
            ),
            metadata=ClipMetadata(
                width=1920,
                height=1080,
                fps=30,
                duration=5.0,
            ),
        )
        assert clip.id == "clip-1"
        assert clip.generation_status == TaskStatus.PENDING


class TestTimelineModels:
    """测试时间线模型"""

    def test_vj_timeline(self):
        timeline = VJTimeline(
            clips=[],
            audio_path="/path/to/audio.mp3",
            total_duration=180.0,
            resolution=(1920, 1080),
            fps=30,
        )
        assert timeline.total_duration == 180.0
        assert timeline.fps == 30


class TestRenderModels:
    """测试渲染模型"""

    def test_render_profile(self):
        profile = RenderProfile(
            name="1080p",
            width=1920,
            height=1080,
            fps=30,
            aspect_ratio=AspectRatio.RATIO_16_9,
            output_format=OutputFormat.MP4,
            codec="libx264",
            crf=23,
        )
        assert profile.name == "1080p"
        assert profile.resolution_str == "1920x1080"

    def test_render_profile_9_16(self):
        profile = RenderProfile(
            name="9x16",
            width=1080,
            height=1920,
            aspect_ratio=AspectRatio.RATIO_9_16,
            output_format=OutputFormat.MP4,
        )
        assert profile.width == 1080
        assert profile.height == 1920


class TestProjectModels:
    """测试项目模型"""

    def test_project_creation(self):
        project = Project(
            id="proj-1",
            name="Test Project",
            description="A test project",
        )
        assert project.id == "proj-1"
        assert project.status == ProjectStatus.CREATED
        assert project.audio_path is None

    def test_project_with_audio(self):
        project = Project(
            id="proj-1",
            name="Test",
            audio_path="/path/to/audio.mp3",
            status=ProjectStatus.UPLOADED,
        )
        assert project.audio_path == "/path/to/audio.mp3"
        assert project.status == ProjectStatus.UPLOADED


class TestAPIModels:
    """测试 API 模型"""

    def test_api_response_success(self):
        response = APIResponse(
            success=True,
            message="Operation successful",
            data={"key": "value"},
        )
        assert response.success is True
        assert response.data["key"] == "value"

    def test_api_response_failure(self):
        response = APIResponse(
            success=False,
            message="Something went wrong",
            error_code="ERR_001",
        )
        assert response.success is False
        assert response.error_code == "ERR_001"

    def test_project_create_request(self):
        request = ProjectCreateRequest(
            name="New Project",
            description="Description here",
        )
        assert request.name == "New Project"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
