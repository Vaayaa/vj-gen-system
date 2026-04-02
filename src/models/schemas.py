"""
VJ-Gen 系统核心数据模型
定义所有 Pydantic 模型，用于类型检查和序列化
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# 枚举类型
# ============================================================================


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SectionType(str, Enum):
    """音频段落类型"""
    INTRO = "intro"
    VERSE = "verse"
    PRE_CHORUS = "pre_chorus"
    CHORUS = "chorus"
    DROP = "drop"
    BRIDGE = "bridge"
    OUTRO = "outro"
    BREAK = "break"
    SILENCE = "silence"


class LyricSentiment(str, Enum):
    """歌词情绪类型"""
    CALM = "calm"
    BUILD = "build"
    CLIMAX = "climax"
    DARK = "dark"
    BRIGHT = "bright"
    NEUTRAL = "neutral"


class AspectRatio(str, Enum):
    """画幅比例"""
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_1_1 = "1:1"
    RATIO_4_3 = "4:3"
    RATIO_21_9 = "21:9"


class OutputFormat(str, Enum):
    """输出格式"""
    MP4 = "mp4"
    MOV = "mov"
    WEBM = "webm"


# ============================================================================
# 任务编排层模型
# ============================================================================


class TaskNode(BaseModel):
    """任务节点"""
    id: str = Field(..., description="节点唯一ID")
    type: Literal[
        "audio_analysis",
        "lyric_nlp",
        "shot_script",
        "keyframe_gen",
        "video_gen",
        "timeline_compile",
        "render",
    ] = Field(..., description="节点类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="节点状态")
    input_data: dict[str, Any] = Field(default_factory=dict, description="输入数据")
    output_data: Optional[dict[str, Any]] = Field(default=None, description="输出数据")
    depends_on: list[str] = Field(default_factory=list, description="依赖的节点ID列表")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    def model_post_init(self, __context: Any) -> None:
        """在初始化后更新 updated_at"""
        self.updated_at = datetime.now()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Workflow(BaseModel):
    """工作流定义"""
    id: str = Field(..., description="工作流唯一ID")
    name: str = Field(..., description="工作流名称")
    nodes: list[TaskNode] = Field(default_factory=list, description="任务节点列表")
    on_complete_callback: Optional[str] = Field(default=None, description="完成后的回调URL")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    def get_node(self, node_id: str) -> Optional[TaskNode]:
        """根据ID获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_ready_nodes(self) -> list[TaskNode]:
        """获取所有准备就绪的节点（依赖都已完成）"""
        ready = []
        for node in self.nodes:
            if node.status != TaskStatus.PENDING:
                continue
            deps_completed = all(
                self.get_node(dep_id) and 
                self.get_node(dep_id).status == TaskStatus.COMPLETED
                for dep_id in node.depends_on
            )
            if deps_completed:
                ready.append(node)
        return ready


# ============================================================================
# 音频分析模型
# ============================================================================


class EnergyPoint(BaseModel):
    """能量曲线上的一个点"""
    timestamp: float = Field(..., description="时间戳（秒）")
    energy: float = Field(..., ge=0, le=1, description="能量值 0-1")


class AudioSection(BaseModel):
    """音频段落"""
    start: float = Field(..., ge=0, description="开始时间（秒）")
    end: float = Field(..., gt=0, description="结束时间（秒）")
    type: SectionType = Field(..., description="段落类型")
    energy: float = Field(..., ge=0, le=1, description="能量值 0-1")
    mood: list[str] = Field(default_factory=list, description="情绪标签列表")
    bpm: Optional[float] = Field(default=None, description="该段的 BPM")


class BeatInfo(BaseModel):
    """节拍信息"""
    timestamp: float = Field(..., ge=0, description="节拍时间（秒）")
    beat_type: Literal["downbeat", "beat", "offbeat"] = Field(
        default="beat", description="节拍类型"
    )
    strength: float = Field(..., ge=0, le=1, description="强度 0-1")


class AudioAnalysisResult(BaseModel):
    """音频分析结果"""
    bpm: float = Field(..., gt=0, description="检测到的 BPM")
    time_signature: str = Field(default="4/4", description="拍号")
    duration: float = Field(..., gt=0, description="音频总时长（秒）")
    sections: list[AudioSection] = Field(default_factory=list, description="段落列表")
    energy_curve: list[EnergyPoint] = Field(default_factory=list, description="能量曲线")
    beats: list[BeatInfo] = Field(default_factory=list, description="节拍列表")
    vocal_path: Optional[str] = Field(default=None, description="人声音频路径")
    instrumental_path: Optional[str] = Field(default=None, description="伴奏音频路径")
    waveform_path: Optional[str] = Field(default=None, description="波形图路径")
    analysis_version: str = Field(default="1.0.0", description="分析版本")


# ============================================================================
# 歌词分析模型
# ============================================================================


class LyricLine(BaseModel):
    """单行歌词"""
    start_time: float = Field(..., ge=0, description="开始时间（秒）")
    end_time: float = Field(..., gt=0, description="结束时间（秒）")
    text: str = Field(..., description="歌词文本")
    sentiment: LyricSentiment = Field(default=LyricSentiment.NEUTRAL, description="情绪")
    keywords: list[str] = Field(default_factory=list, description="关键词")
    imagery: list[str] = Field(default_factory=list, description="场景意象")
    visual_prompt: str = Field(default="", description="生成的视觉 Prompt")


class LyricAnalysis(BaseModel):
    """歌词分析结果"""
    lines: list[LyricLine] = Field(default_factory=list, description="歌词行列表")
    language: str = Field(default="unknown", description="语言")
    overall_mood: LyricSentiment = Field(default=LyricSentiment.NEUTRAL, description="整体情绪")
    themes: list[str] = Field(default_factory=list, description="主题列表")
    analysis_version: str = Field(default="1.0.0", description="分析版本")


# ============================================================================
# VJ 镜头脚本模型
# ============================================================================


class TransitionHint(str, Enum):
    """转场提示"""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    ZOOM = "zoom"
    SLIDE = "slide"
    GLITCH = "glitch"


class CameraBehavior(str, Enum):
    """相机行为"""
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    HANDHELD = "handheld"
    ORBIT = "orbit"
    RISE = "rise"
    FALL = "fall"


class MotionDesign(BaseModel):
    """运动设计"""
    primary_motion: str = Field(default="none", description="主要运动类型")
    secondary_motion: Optional[str] = Field(default=None, description="次要运动")
    motion_intensity: float = Field(default=0.5, ge=0, le=1, description="运动强度")
    motion_direction: str = Field(default="center", description="运动方向")


class ShotScriptItem(BaseModel):
    """VJ 静帧脚本项"""
    id: str = Field(..., description="脚本项唯一ID")
    time_start: float = Field(..., ge=0, description="开始时间（秒）")
    time_end: float = Field(..., gt=0, description="结束时间（秒）")
    section_type: SectionType = Field(..., description="音频段落类型")
    lyric: str = Field(default="", description="对应歌词")
    audio_emotion: str = Field(default="neutral", description="音频情绪")
    energy: float = Field(..., ge=0, le=1, description="能量值")
    visual_style: str = Field(..., description="视觉风格")
    visual_prompt: str = Field(..., description="图像生成 Prompt")
    motion_design: MotionDesign = Field(default_factory=MotionDesign, description="运动设计")
    color_palette: list[str] = Field(default_factory=list, description="调色板")
    camera_behavior: CameraBehavior = Field(default=CameraBehavior.STATIC, description="相机行为")
    transition_hint: TransitionHint = Field(default=TransitionHint.CUT, description="转场提示")
    notes: Optional[str] = Field(default=None, description="备注")


class ShotScript(BaseModel):
    """VJ 镜头脚本"""
    items: list[ShotScriptItem] = Field(default_factory=list, description="脚本项列表")
    total_duration: float = Field(..., gt=0, description="总时长（秒）")
    resolution: tuple[int, int] = Field(default=(1920, 1080), description="分辨率")
    fps: int = Field(default=30, description="帧率")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")


# ============================================================================
# VJ 片段模型
# ============================================================================


class ClipMetadata(BaseModel):
    """片段元数据"""
    width: int = Field(..., gt=0, description="宽度")
    height: int = Field(..., gt=0, description="高度")
    fps: int = Field(default=30, description="帧率")
    duration: float = Field(..., gt=0, description="时长（秒）")
    codec: Optional[str] = Field(default=None, description="编码器")
    bitrate: Optional[int] = Field(default=None, description="码率")


class VJClip(BaseModel):
    """VJ 片段"""
    id: str = Field(..., description="片段唯一ID")
    time_start: float = Field(..., ge=0, description="开始时间（秒）")
    time_end: float = Field(..., gt=0, description="结束时间（秒）")
    script_item: ShotScriptItem = Field(..., description="对应的脚本项")
    keyframe_path: Optional[str] = Field(default=None, description="关键帧路径")
    video_path: Optional[str] = Field(default=None, description="生成视频路径")
    metadata: ClipMetadata = Field(..., description="片段元数据")
    generation_status: TaskStatus = Field(default=TaskStatus.PENDING, description="生成状态")
    error_message: Optional[str] = Field(default=None, description="错误信息")


# ============================================================================
# 时间线模型
# ============================================================================


class VJTimeline(BaseModel):
    """VJ 时间线"""
    clips: list[VJClip] = Field(default_factory=list, description="片段列表")
    audio_path: str = Field(..., description="背景音乐路径")
    total_duration: float = Field(..., gt=0, description="总时长（秒）")
    resolution: tuple[int, int] = Field(default=(1920, 1080), description="分辨率")
    fps: int = Field(default=30, description="帧率")
    fade_in_duration: float = Field(default=1.0, ge=0, description="淡入时长（秒）")
    fade_out_duration: float = Field(default=1.0, ge=0, description="淡出时长（秒）")


# ============================================================================
# 渲染配置模型
# ============================================================================


class RenderProfile(BaseModel):
    """渲染配置"""
    name: str = Field(..., description="配置名称")
    width: int = Field(..., gt=0, description="宽度")
    height: int = Field(..., gt=0, description="高度")
    fps: int = Field(default=30, description="帧率")
    aspect_ratio: AspectRatio = Field(..., description="画幅比例")
    output_format: OutputFormat = Field(default=OutputFormat.MP4, description="输出格式")
    codec: str = Field(default="libx264", description="视频编码器")
    crf: int = Field(default=23, ge=0, le=51, description="CRF 值（越小越清晰）")
    preset: str = Field(default="medium", description="编码预设")
    audio_codec: str = Field(default="aac", description="音频编码器")
    audio_bitrate: str = Field(default="192k", description="音频码率")
    audio_sample_rate: int = Field(default=44100, description="音频采样率")

    @property
    def resolution_str(self) -> str:
        """返回分辨率字符串"""
        return f"{self.width}x{self.height}"


# ============================================================================
# 项目模型
# ============================================================================


class ProjectStatus(str, Enum):
    """项目状态"""
    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    SCRIPT_GENERATED = "script_generated"
    GENERATING = "generating"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """VJ 项目"""
    id: str = Field(..., description="项目唯一ID")
    name: str = Field(..., description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    status: ProjectStatus = Field(default=ProjectStatus.CREATED, description="项目状态")
    audio_path: Optional[str] = Field(default=None, description="音频文件路径")
    lyric_path: Optional[str] = Field(default=None, description="歌词文件路径")
    audio_analysis: Optional[AudioAnalysisResult] = Field(default=None, description="音频分析结果")
    lyric_analysis: Optional[LyricAnalysis] = Field(default=None, description="歌词分析结果")
    shot_script: Optional[ShotScript] = Field(default=None, description="镜头脚本")
    timeline: Optional[VJTimeline] = Field(default=None, description="时间线")
    clips: list[VJClip] = Field(default_factory=list, description="生成的片段列表")
    workflow: Optional[Workflow] = Field(default=None, description="工作流")
    render_profiles: list[RenderProfile] = Field(
        default_factory=lambda: [RenderProfile(
            name="1080p",
            width=1920,
            height=1080,
            aspect_ratio=AspectRatio.RATIO_16_9,
        )],
        description="渲染配置列表"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


# ============================================================================
# API 响应模型
# ============================================================================


class APIResponse(BaseModel):
    """通用 API 响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")
    error_code: Optional[str] = Field(default=None, description="错误码")


class ProjectCreateRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    description: Optional[str] = Field(default=None, max_length=1000, description="项目描述")


class ProjectUploadRequest(BaseModel):
    """上传文件请求"""
    project_id: str = Field(..., description="项目ID")
    file_type: Literal["audio", "lyric"] = Field(..., description="文件类型")
    filename: str = Field(..., description="文件名")


class GenerateRequest(BaseModel):
    """触发生成请求"""
    project_id: str = Field(..., description="项目ID")
    keyframe_only: bool = Field(default=False, description="仅生成关键帧")
    video_quality: Literal["fast", "standard", "high"] = Field(default="standard", description="视频质量")


class RenderRequest(BaseModel):
    """渲染请求"""
    project_id: str = Field(..., description="项目ID")
    profiles: list[str] = Field(..., description="渲染配置名称列表")
