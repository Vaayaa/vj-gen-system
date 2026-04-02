# 多模型 VJ 生成系统架构蓝图
**版本：V0.1 | 日期：2026-04-02 | 状态：架构草图**

---

## 一、系统定位

**类比产品**：LoveArt / TapNow / Runway + 专业VJ工具

**核心价值**：从「音频 + 歌词」到「完整VJ素材」的全自动生产管线

---

## 二、系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层 (Frontend)                              │
│   Web UI / API Gateway / 文件上传 / 进度预览 / 多画幅导出                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           任务编排层 (Orchestrator)                          │
│   Workflow Engine │ Task Queue │ 任务状态机 │ 断点续跑 │ 重试机制           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  音频分析管线  │           │   歌词NLP管线  │           │  视觉生成管线  │
│               │           │               │           │               │
│ • BPM检测     │           │ • 分句分词    │           │ • 静帧生成    │
│ • 节拍提取    │           │ • 情绪分析    │           │ • 视频生成    │
│ • 段落结构    │           │ • Prompt生成  │           │ • 超分/补帧   │
│ • 能量曲线    │           │ • 时间对齐    │           │ • 风格化处理  │
└───────────────┘           └───────────────┘           └───────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          时间线编排层 (Timeline)                             │
│   片段拼接 │ 转场处理 │ 节拍对齐 │ 多画幅渲染 │ ffmpeg 管线                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           存储层 (Storage)                                  │
│   原始文件 │ 中间产物 │ 最终成品 │ 对象存储 (S3/MinIO) │ 分布式              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块设计

### 3.1 任务编排层 (Orchestrator)

```typescript
// 任务状态机
enum TaskStatus {
  PENDING = 'pending',
  RUNNING = 'running', 
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// 任务节点
interface TaskNode {
  id: string;
  type: 'audio_analysis' | 'lyric_nlp' | 'shot_script' | 
        'keyframe_gen' | 'video_gen' | 'timeline_compile' | 'render';
  status: TaskStatus;
  input: Record<string, any>;
  output: Record<string, any>;
  depends_on: string[];  // 依赖的任务ID列表
  retry_count: number;
  created_at: Date;
  updated_at: Date;
}

// 工作流定义
interface Workflow {
  id: string;
  name: string;
  nodes: TaskNode[];
  on_complete?: string;  // 完成后的回调
}
```

### 3.2 模型适配层 (Model Adapters)

```typescript
// 统一适配器接口
interface BaseAdapter {
  provider: string;
  model: string;
  capabilities: string[];
  
  // 统一调用接口
  invoke(input: any): Promise<any>;
  
  // 健康检查
  healthCheck(): Promise<boolean>;
  
  // 获取能力描述
  getCapabilities(): string[];
}

// 音频分析适配器
interface AudioAnalysisAdapter extends BaseAdapter {
  analyze(audioPath: string): Promise<AudioAnalysisResult>;
}

// LLM 适配器
interface LLMAdapter extends BaseAdapter {
  chat(prompt: string, system?: string): Promise<string>;
  structuredOutput(schema: object, prompt: string): Promise<any>;
}

// 图像生成适配器
interface ImageGenAdapter extends BaseAdapter {
  generate(prompt: string, params?: ImageGenParams): Promise<ImageResult>;
}

// 视频生成适配器  
interface VideoGenAdapter extends BaseAdapter {
  generate(keyframe: string, prompt: string, duration: number): Promise<VideoResult>;
}

// 超分适配器
interface UpscaleAdapter extends BaseAdapter {
  upscale(input: string, scale: number): Promise<string>;
}
```

### 3.3 核心数据结构

```typescript
// 音频分析结果
interface AudioAnalysisResult {
  bpm: number;
  time_signature: string;
  duration: number;
  sections: AudioSection[];
  energy_curve: EnergyPoint[];
}

interface AudioSection {
  start: number;      // 秒
  end: number;        // 秒
  type: 'intro' | 'verse' | 'pre_chorus' | 'chorus' | 'drop' | 'bridge' | 'outro';
  energy: number;     // 0-1
  mood: string[];
}

// 歌词分析结果
interface LyricAnalysis {
  lines: LyricLine[];
}

interface LyricLine {
  start_time: number;  // 秒
  end_time: number;
  text: string;
  sentiment: 'calm' | 'build' | 'climax' | 'dark' | 'bright';
  keywords: string[];
  imagery: string[];   // 场景意象
  visual_prompt: string;  // 生成用的Prompt
}

// VJ 静帧脚本
interface ShotScriptItem {
  time_start: number;
  time_end: number;
  section_type: string;
  lyric: string;
  audio_emotion: string;
  energy: number;
  visual_style: string;
  visual_prompt: string;
  motion_design: string;
  color_palette: string[];
  camera_behavior: string;
  transition_hint: string;
}

// VJ 片段
interface VJClip {
  id: string;
  time_start: number;
  time_end: number;
  script_item: ShotScriptItem;
  keyframe_path?: string;
  video_path?: string;
  metadata: {
    width: number;
    height: number;
    fps: number;
    duration: number;
  };
}

// 时间线
interface VJTimeline {
  clips: VJClip[];
  audio_path: string;
  total_duration: number;
  resolution: [number, number];
  fps: number;
}

// 渲染配置
interface RenderProfile {
  name: string;
  width: number;
  height: number;
  fps: number;
  aspect_ratio: string;
  output_format: 'mp4' | 'mov' | 'webm';
  codec: string;
}
```

---

## 四、模型路由设计

```typescript
// 模型路由配置
interface ModelRouteConfig {
  task_type: string;
  provider: string;
  model: string;
  priority: number;  // 优先级（用于fallback）
  cost_weight?: number;
  latency_weight?: number;
  quality_weight?: number;
}

// 默认路由策略
const DEFAULT_ROUTING: Record<string, ModelRouteConfig[]> = {
  audio_analysis: [
    { task_type: 'beat_detection', provider: 'local', model: 'demucs', priority: 1 },
    { task_type: 'bpm_detection', provider: 'local', model: 'librosa', priority: 1 },
  ],
  llm: [
    { task_type: 'lyric_analysis', provider: 'openai', model: 'gpt-4o', priority: 1 },
    { task_type: 'prompt_enhance', provider: 'claude', model: 'claude-3-5-sonnet', priority: 2 },
  ],
  image_gen: [
    { task_type: 'keyframe', provider: 'sd', model: 'sdxl-turbo', priority: 1 },
    { task_type: 'style_transfer', provider: 'leonardo', model: 'leonardo-vision', priority: 2 },
  ],
  video_gen: [
    { task_type: 'vj_clip', provider: 'runway', model: 'gen-3', priority: 1 },
    { task_type: 'vj_clip', provider: 'kling', model: 'kling-1.0', priority: 2 },
  ],
  upscale: [
    { task_type: 'video_upscale', provider: 'topaz', model: 'video-ai', priority: 1 },
  ],
};
```

---

## 五、技术栈建议

| 层级 | 推荐技术 |
|------|----------|
| **后端框架** | Python FastAPI / Node.js Express |
| **任务队列** | Celery + Redis / BullMQ |
| **工作流引擎** | Prefect / Temporal / 自研轻量状态机 |
| **音频处理** | librosa, demucs, Essentia |
| **视频处理** | ffmpeg, moviepy, OpenCV |
| **数据库** | PostgreSQL (元数据) + Redis (缓存/队列) |
| **对象存储** | MinIO (本地) / S3 (云) |
| **前端** | Next.js + React + Tailwind |
| **部署** | Docker Compose / K8s |

---

## 六、目录结构

```
vj-gen-system/
├── src/
│   ├── adapters/           # 模型适配器
│   │   ├── audio/
│   │   │   ├── base.py
│   │   │   ├── librosa_adapter.py
│   │   │   └── demucs_adapter.py
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── openai_adapter.py
│   │   │   └── anthropic_adapter.py
│   │   ├── image/
│   │   │   ├── base.py
│   │   │   ├── sd_adapter.py
│   │   │   └── dalle_adapter.py
│   │   └── video/
│   │       ├── base.py
│   │       ├── runway_adapter.py
│   │       └── kling_adapter.py
│   │
│   ├── core/              # 核心逻辑
│   │   ├── orchestrator.py
│   │   ├── workflow.py
│   │   ├── router.py
│   │   └── timeline.py
│   │
│   ├── pipelines/         # 处理管线
│   │   ├── audio_pipeline.py
│   │   ├── lyric_pipeline.py
│   │   ├── shot_script_pipeline.py
│   │   └── render_pipeline.py
│   │
│   ├── models/           # 数据模型
│   │   └── schemas.py
│   │
│   └── services/         # 业务服务
│       ├── vj_generator.py
│       └── renderer.py
│
├── api/                  # API 层
│   ├── routes.py
│   └── schemas.py
│
├── worker/              # 异步任务
│   └── tasks.py
│
├── storage/             # 存储管理
│   └── manager.py
│
├── config/             # 配置文件
│   ├── models.yaml     # 模型配置
│   └── routing.yaml    # 路由策略
│
├── tests/
├── Dockerfile
├── docker-compose.yaml
└── README.md
```

---

## 七、关键接口设计

```yaml
# REST API 端点
POST   /api/v1/projects              # 创建项目
GET    /api/v1/projects/{id}         # 获取项目
POST   /api/v1/projects/{id}/upload  # 上传音频/歌词
POST   /api/v1/projects/{id}/analyze # 触发分析
GET    /api/v1/projects/{id}/script  # 获取脚本
POST   /api/v1/projects/{id}/generate # 触发生成
GET    /api/v1/projects/{id}/preview  # 预览片段
POST   /api/v1/projects/{id}/render  # 触发渲染
GET    /api/v1/projects/{id}/download # 下载成品
```

---

## 八、下一步计划

| 阶段 | 内容 | 交付物 |
|------|------|--------|
| V0.2 | 核心数据模型 + 适配器基类 | TypeScript/Python 类型定义 |
| V0.3 | 音频分析管线实现 | demo 能跑通 |
| V0.4 | LLM + 歌词分析管线 | Prompt 模板 |
| V0.5 | 静帧生成 + 视频生成接入 | 实际API调用 |
| V0.6 | 时间线编排 + ffmpeg | 片段拼接demo |
| V0.7 | 多画幅渲染 | 16:9/9:16 输出 |
| V1.0 | Web UI + API | 可用产品 |

---

*文档版本：V0.1 | 待续...*
