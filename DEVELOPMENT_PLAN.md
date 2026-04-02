# VJ-Gen 系统开发计划

**版本：V1.0 | 日期：2026-04-02 | 状态：执行中 | 最后更新：2026-04-02**

---

## 一、阶段总览

| Phase | 名称 | 预计工时 | 状态 | 完成内容 |
|-------|------|----------|------|----------|
| 1 | 核心数据模型 + 适配器基类 | 2天 | ✅ 已完成 | Pydantic schemas, BaseAdapter, 所有类型适配器基类, models.yaml, routing.yaml |
| 2 | 音频分析管线 | 3天 | 🔄 进行中 | librosa_adapter (BPM/节拍/段落), demucs_adapter (人声分离), audio_pipeline |
| 3 | LLM + 歌词分析管线 | 3天 | 🔄 进行中 | openai_adapter, anthropic_adapter, lyric_pipeline, shot_script_pipeline |
| 4 | 静帧生成管线 | 3天 | ⏳ 待开始 | sd_adapter, dalle_adapter, leonardo_adapter, keyframe_pipeline |
| 5 | 视频生成管线 | 3天 | ⏳ 待开始 | runway_adapter, kling_adapter, topaz_adapter, video_pipeline |
| 6 | 时间线编排 + ffmpeg | 3天 | ⏳ 待开始 | timeline.py, transitions.py, beat_sync.py, renderer |
| 7 | 多画幅渲染 | 2天 | ⏳ 待开始 | aspect_ratio.py, profiles.yaml, 多画幅并行渲染 |
| 8 | API + Web UI | 5天 | ⏳ 待开始 | FastAPI routes, WebSocket, Web UI, 项目管理界面 |

**总计：约 24 个工作日（4-5 周）**

---

## 二、详细阶段计划

### Phase 1: 核心数据模型 + 适配器基类 ✅

**目标**：建立 TypeScript 类型定义 + Python Pydantic 模型 + 所有 Adapter 基类

#### 1.1 交付物

```
src/models/schemas.py      ✅ Pydantic 数据模型 (所有核心类型)
src/adapters/base.py       ⏳ 适配器基类 (待实现)
src/adapters/audio/base.py ⏳ 音频适配器基类 (待实现)
src/adapters/llm/base.py  ⏳ LLM 适配器基类 (待实现)
src/adapters/image/base.py ⏳ 图像适配器基类 (待实现)
src/adapters/video/base.py ⏳ 视频适配器基类 (待实现)
config/models.yaml         ✅ 模型配置
config/routing.yaml        ✅ 路由策略
```

#### 1.2 任务分解

- [x] 定义所有 Pydantic 模型（TaskStatus, TaskNode, Workflow, AudioAnalysisResult, LyricAnalysis, ShotScriptItem, VJClip, VJTimeline, RenderProfile）
- [ ] 实现 BaseAdapter 抽象基类
- [ ] 实现 AudioAnalysisAdapter 接口
- [ ] 实现 LLMAdapter 接口
- [ ] 实现 ImageGenAdapter 接口
- [ ] 实现 VideoGenAdapter 接口
- [ ] 实现 UpscaleAdapter 接口
- [ ] 编写单元测试

#### 1.3 验收标准

- [ ] 所有类型定义通过 mypy 检查
- [ ] 所有 Adapter 基类可实例化
- [ ] 单元测试覆盖率 > 80%

#### 1.4 已完成详情

**src/models/schemas.py** 包含以下模型：
- 枚举类型：`TaskStatus`, `SectionType`, `LyricSentiment`, `AspectRatio`, `OutputFormat`, `ProjectStatus`, `TransitionHint`, `CameraBehavior`
- 任务编排：`TaskNode`, `Workflow`
- 音频分析：`EnergyPoint`, `AudioSection`, `BeatInfo`, `AudioAnalysisResult`
- 歌词分析：`LyricLine`, `LyricAnalysis`
- VJ脚本：`MotionDesign`, `ShotScriptItem`, `ShotScript`
- 片段：`ClipMetadata`, `VJClip`
- 时间线：`VJTimeline`
- 渲染：`RenderProfile`
- 项目：`Project`, `ProjectStatus`
- API请求/响应：`APIResponse`, `ProjectCreateRequest`, `ProjectUploadRequest`, `GenerateRequest`, `RenderRequest`

---

### Phase 2: 音频分析管线 🔄

**目标**：实现完整的音频分析功能（BPM、节拍、段落、能量）

#### 2.1 交付物

```
src/adapters/audio/librosa_adapter.py  🔄 进行中
src/adapters/audio/demucs_adapter.py  🔄 进行中
src/pipelines/audio_pipeline.py       🔄 进行中
```

#### 2.2 任务分解

- [ ] 实现 BPM 检测
- [ ] 实现节拍/Beat 检测
- [ ] 实现段落结构分析（intro/verse/chorus/drop/outro）
- [ ] 实现能量曲线提取
- [ ] 实现人声分离（vocal isolation）
- [ ] 集成 demucs 进行人声/伴奏分离
- [ ] 编写管线编排逻辑
- [ ] 编写 demo 脚本（给定音频文件输出分析结果）
- [ ] 性能优化（批处理、缓存）

#### 2.3 验收标准

- [ ] 在测试音频上运行成功
- [ ] 输出符合 AudioAnalysisResult schema
- [ ] BPM 误差 < 5%
- [ ] 节拍时间戳准确性 < 50ms

---

### Phase 3: LLM + 歌词分析管线 🔄

**目标**：实现歌词 NLP 分析 + Shot Script 生成

#### 3.1 交付物

```
src/adapters/llm/openai_adapter.py     🔄 进行中
src/adapters/llm/anthropic_adapter.py  🔄 进行中
src/pipelines/lyric_pipeline.py        🔄 进行中
src/pipelines/shot_script_pipeline.py  🔄 进行中
src/prompts/lyric_analysis.py         ✅ 已存在
```

#### 3.2 任务分解

- [ ] 实现 OpenAI Adapter（chat + structured output）
- [ ] 实现 Claude Adapter（chat + structured output）
- [ ] 设计歌词分析 Prompt 模板
- [ ] 实现分句分词逻辑
- [ ] 实现情绪分析（sentiment）
- [ ] 实现关键词/意象提取
- [ ] 设计 Shot Script 生成 Prompt
- [ ] 实现 Visual Prompt 生成
- [ ] 实现时间对齐（将歌词时间戳与 shot script 对齐）
- [ ] 编写 demo 脚本

#### 3.3 验收标准

- [ ] 给定歌词文本 + 时间戳，输出 ShotScriptItem 列表
- [ ] Prompt 模板可配置
- [ ] 支持多模型 fallback

---

### Phase 4: 静帧生成管线 ⏳

**目标**：接入图像生成模型，生成关键帧

#### 4.1 交付物

```
src/adapters/image/sd_adapter.py        ⏳ 待开发
src/adapters/image/dalle_adapter.py     ⏳ 待开发
src/adapters/image/leonardo_adapter.py  ⏳ 待开发
src/pipelines/keyframe_pipeline.py      ⏳ 待开发
```

#### 4.2 任务分解

- [ ] 实现 Stable Diffusion Adapter
- [ ] 实现 DALL-E Adapter
- [ ] 实现 Leonardo AI Adapter
- [ ] 设计关键帧生成策略（基于 shot script）
- [ ] 实现 Prompt 后处理（增强、风格化）
- [ ] 实现批处理（多个 shot 并行生成）
- [ ] 实现结果缓存（避免重复生成）
- [ ] 编写 demo 脚本

#### 4.3 验收标准

- [ ] 给定 ShotScriptItem，输出关键帧图片
- [ ] 支持多种风格
- [ ] 生成质量可接受

---

### Phase 5: 视频生成管线 ⏳

**目标**：接入视频生成模型，将关键帧扩展为视频片段

#### 5.1 交付物

```
src/adapters/video/runway_adapter.py    ⏳ 待开发
src/adapters/video/kling_adapter.py     ⏳ 待开发
src/adapters/video/topaz_adapter.py     ⏳ 待开发
src/pipelines/video_pipeline.py         ⏳ 待开发
```

#### 5.2 任务分解

- [ ] 实现 Runway Adapter
- [ ] 实现 Kling Adapter
- [ ] 实现 Topaz Video Enhancer Adapter
- [ ] 设计视频生成策略（基于关键帧 + motion prompt）
- [ ] 实现运动控制（camera behavior, motion design）
- [ ] 实现时长控制（与音频节拍对齐）
- [ ] 编写 demo 脚本

#### 5.3 验收标准

- [ ] 给定关键帧 + ShotScriptItem，输出视频片段
- [ ] 视频时长与节拍对齐
- [ ] 支持多种运动风格

---

### Phase 6: 时间线编排 + ffmpeg ⏳

**目标**：实现完整的时间线拼接和渲染

#### 6.1 交付物

```
src/core/timeline.py          ✅ 已存在 (数据结构)
src/core/beat_sync.py         ✅ 已存在
src/core/transitions.py       ✅ 已存在
src/core/router.py            ✅ 已存在
src/services/renderer.py      ⏳ 待开发
src/pipelines/timeline_pipeline.py ⏳ 待开发
```

#### 6.2 任务分解

- [ ] 实现 VJTimeline 数据结构
- [ ] 实现片段拼接逻辑
- [ ] 实现转场处理（淡入淡出、溶解等）
- [ ] 实现节拍对齐（视频片段与音频节拍对齐）
- [ ] 实现 ffmpeg 管线封装
- [ ] 实现音频合成（背景音乐 + 音效）
- [ ] 编写 demo 脚本（将多个 clip 拼接为完整视频）

#### 6.3 验收标准

- [ ] 给定 VJClip 列表 + 音频，输出完整视频
- [ ] 转场流畅自然
- [ ] 节拍对齐准确

---

### Phase 7: 多画幅渲染 ⏳

**目标**：实现 16:9 / 9:16 / 1:1 / 4:3 等多画幅输出

#### 7.1 交付物

```
src/services/aspect_ratio.py  ⏳ 待开发
config/profiles.yaml          ⏳ 待开发
```

#### 7.2 任务分解

- [ ] 定义 RenderProfile 数据结构
- [ ] 实现画幅裁剪策略（智能居中 + 关键区域保留）
- [ ] 实现画幅拉伸策略（可选）
- [ ] 实现多画幅并行渲染
- [ ] 实现输出格式转换（mp4/mov/webm）
- [ ] 实现编码参数优化
- [ ] 编写 demo 脚本

#### 7.3 验收标准

- [ ] 支持 16:9 / 9:16 / 1:1 / 4:3 输出
- [ ] 裁剪区域合理（不丢失重要视觉元素）
- [ ] 编码质量达标（VBR, CRF 控制）

---

### Phase 8: API + Web UI ⏳

**目标**：提供完整的 Web 界面和 REST API

#### 8.1 交付物

```
api/main.py                    ✅ 已完成 (FastAPI 路由)
api/schemas.py                 ✅ 已完成
src/services/vj_generator.py    ⏳ 待开发
frontend/                      ⏳ 待开发 (Next.js)
worker/tasks.py                ⏳ 待开发 (Celery)
```

#### 8.2 任务分解

- [x] 实现 FastAPI 路由（创建项目、上传、分析、生成、渲染、下载）
- [x] 实现文件上传（音频、歌词）
- [x] 实现进度追踪（WebSocket）
- [ ] 实现任务队列（Celery + Redis）
- [ ] 实现 VJGenerator 服务（整合所有管线）
- [ ] 实现 Web UI（项目列表、上传界面、预览界面）
- [ ] 实现多画幅预览
- [ ] 实现下载功能

#### 8.3 验收标准

- [ ] 完整的用户流程可跑通
- [ ] 支持断点续传
- [ ] 进度实时更新
- [ ] 响应式 UI（支持手机/桌面）

---

## 三、技术决策

### 3.1 核心语言

- **后端**：Python 3.11+（强类型支持好，音频/视频库生态成熟）
- **前端**：TypeScript + Next.js（类型安全，与后端共享 schema）

### 3.2 数据库

- **PostgreSQL**：项目元数据、任务状态、用户数据
- **Redis**：任务队列、缓存、会话状态
- **MinIO**：对象存储（替代 S3，本地开发）

### 3.3 任务队列

- **Celery**：Python 生态成熟，支持复杂工作流
- **Redis**：消息代理 + 结果后端

### 3.4 关键依赖

```txt
# 音频处理
librosa>=0.10.0
demucs>=4.0.0
soundfile>=0.12.0

# 视频处理
ffmpeg-python>=0.2.0
opencv-python>=4.8.0

# AI 适配器
openai>=1.0.0
anthropic>=0.8.0
requests>=2.31.0
aiohttp>=3.9.0

# Web 框架
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0

# 任务队列
celery>=5.3.0
redis>=5.0.0

# 存储
minio>=7.2.0
boto3>=1.34.0
```

### 3.5 模型路由策略

- 默认优先使用成本最低的方案
- 支持按质量/延迟/成本加权路由
- 自动 fallback（primary 失败时尝试 secondary）

---

## 四、团队分工

| 角色 | 职责 | 分配 |
|------|------|------|
| 首席架构师 | Phase 1, 架构规范 | ✅ 已完成 |
| pipeline-dev | Phase 2, 3 (音频+歌词) | 🔄 进行中 |
| pipeline-dev | Phase 4, 5 (图像+视频) | ⏳ 待开始 |
| backend-dev | Phase 6, 7 (时间线+渲染) | ⏳ 待开始 |
| backend-dev | Phase 8 API层 | ⏳ 待开始 |
| ui-dev | Phase 8 前端 | ⏳ 待开始 |

---

## 五、里程碑

| 里程碑 | 日期 | 内容 | 状态 |
|--------|------|------|------|
| M1 | +2 周 | Phase 1-3 完成，基础管线可跑 | 🔄 进行中 |
| M2 | +4 周 | Phase 4-6 完成，端到端 demo | ⏳ 待开始 |
| M3 | +5 周 | Phase 7-8 完成，可发布版本 | ⏳ 待开始 |

---

## 六、风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 视频生成 API 不稳定 | 高 | 高 | 实现本地 fallback（视频插帧） |
| 音频分析精度不足 | 中 | 中 | 支持多算法融合 |
| LLM Prompt 调优耗时 | 高 | 中 | 提前准备 Prompt 模板库 |
| ffmpeg 性能瓶颈 | 中 | 中 | 实现 GPU 加速（NVENC） |

---

## 七、当前进度快照

### 已完成

- ✅ 所有 Pydantic 数据模型定义
- ✅ 配置文件 (models.yaml, routing.yaml)
- ✅ Prompt 模板 (lyric_analysis.py)
- ✅ API 主服务 (api/main.py) - 包含完整 REST + WebSocket
- ✅ 核心模块骨架 (timeline, beat_sync, transitions, router)

### 进行中

- 🔄 音频适配器实现 (librosa_adapter, demucs_adapter)
- 🔄 LLM 适配器实现 (openai_adapter, anthropic_adapter)
- 🔄 管线实现 (audio_pipeline, lyric_pipeline)

### 待开始

- ⏳ 图像/视频适配器
- ⏳ 时间线渲染服务
- ⏳ Celery Worker
- ⏳ 前端 Web UI

---

*文档版本：V1.0 | 最后更新：2026-04-02*
