# VJ-Gen 系统开发计划
**版本：V1.0 | 日期：2026-04-02 | 状态：执行中**

---

## 一、阶段总览

| Phase | 名称 | 预计工时 | 状态 | 负责人 |
|-------|------|----------|------|--------|
| 1 | 核心数据模型 + 适配器基类 | 2天 | 🔄 进行中 | 待分配 |
| 2 | 音频分析管线 | 3天 | ⏳ 待开始 | 待分配 |
| 3 | LLM + 歌词分析管线 | 3天 | ⏳ 待开始 | 待分配 |
| 4 | 静帧生成管线 | 3天 | ⏳ 待开始 | 待分配 |
| 5 | 视频生成管线 | 3天 | ⏳ 待开始 | 待分配 |
| 6 | 时间线编排 + ffmpeg | 3天 | ⏳ 待开始 | 待分配 |
| 7 | 多画幅渲染 | 2天 | ⏳ 待开始 | 待分配 |
| 8 | API + Web UI | 5天 | ⏳ 待开始 | 待分配 |

**总计：约 24 个工作日（4-5 周）**

---

## 二、详细阶段计划

### Phase 1: 核心数据模型 + 适配器基类
**目标**：建立 TypeScript 类型定义 + Python Pydantic 模型 + 所有 Adapter 基类

#### 1.1 交付物
```
src/models/schemas.py      # Pydantic 数据模型
src/adapters/base.py       # 适配器基类
src/adapters/audio/base.py # 音频适配器基类
src/adapters/llm/base.py  # LLM 适配器基类
src/adapters/image/base.py # 图像适配器基类
src/adapters/video/base.py # 视频适配器基类
config/models.yaml         # 模型配置
config/routing.yaml        # 路由策略
```

#### 1.2 任务分解
- [ ] 定义所有 Pydantic 模型（TaskStatus, TaskNode, Workflow, AudioAnalysisResult, LyricAnalysis, ShotScriptItem, VJClip, VJTimeline, RenderProfile）
- [ ] 实现 BaseAdapter 抽象基类
- [ ] 实现 AudioAnalysisAdapter 接口
- [ ] 实现 LLMAdapter 接口
- [ ] 实现 ImageGenAdapter 接口
- [ ] 实现 VideoGenAdapter 接口
- [ ] 实现 UpscaleAdapter 接口
- [ ] 编写 models.yaml 配置模板
- [ ] 编写 routing.yaml 路由策略
- [ ] 编写单元测试

#### 1.3 验收标准
- [ ] 所有类型定义通过 mypy 检查
- [ ] 所有 Adapter 基类可实例化
- [ ] 单元测试覆盖率 > 80%

---

### Phase 2: 音频分析管线
**目标**：实现完整的音频分析功能（BPM、节拍、段落、能量）

#### 2.1 交付物
```
src/adapters/audio/librosa_adapter.py  # librosa 音频分析
src/adapters/audio/demucs_adapter.py  # 人声分离
src/pipelines/audio_pipeline.py       # 音频分析管线
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

### Phase 3: LLM + 歌词分析管线
**目标**：实现歌词 NLP 分析 + Shot Script 生成

#### 3.1 交付物
```
src/adapters/llm/openai_adapter.py    # OpenAI GPT
src/adapters/llm/anthropic_adapter.py  # Claude
src/pipelines/lyric_pipeline.py        # 歌词分析管线
src/pipelines/shot_script_pipeline.py  # 镜头脚本生成
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

### Phase 4: 静帧生成管线
**目标**：接入图像生成模型，生成关键帧

#### 4.1 交付物
```
src/adapters/image/sd_adapter.py        # Stable Diffusion
src/adapters/image/dalle_adapter.py    # DALL-E
src/adapters/image/leonardo_adapter.py  # Leonardo AI
src/pipelines/keyframe_pipeline.py      # 静帧生成管线
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

### Phase 5: 视频生成管线
**目标**：接入视频生成模型，将关键帧扩展为视频片段

#### 5.1 交付物
```
src/adapters/video/runway_adapter.py    # Runway Gen-3
src/adapters/video/kling_adapter.py     #  Kling 1.0
src/adapters/video/looperator_adapter.py # Looperator (节拍同步)
src/pipelines/video_pipeline.py          # 视频生成管线
```

#### 5.2 任务分解
- [ ] 实现 Runway Adapter
- [ ] 实现 Kling Adapter
- [ ] 设计视频生成策略（基于关键帧 + motion prompt）
- [ ] 实现运动控制（camera behavior, motion design）
- [ ] 实现时长控制（与音频节拍对齐）
- [ ] 实现 Looperator 风格化处理（可选）
- [ ] 编写 demo 脚本

#### 5.3 验收标准
- [ ] 给定关键帧 + ShotScriptItem，输出视频片段
- [ ] 视频时长与节拍对齐
- [ ] 支持多种运动风格

---

### Phase 6: 时间线编排 + ffmpeg
**目标**：实现完整的时间线拼接和渲染

#### 6.1 交付物
```
src/core/timeline.py          # 时间线数据结构
src/core/workflow.py          # 工作流编排
src/services/renderer.py       # 渲染服务
src/pipelines/timeline_pipeline.py # 时间线编排管线
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

### Phase 7: 多画幅渲染
**目标**：实现 16:9 / 9:16 / 1:1 / 4:3 等多画幅输出

#### 7.1 交付物
```
src/services/aspect_ratio.py  # 画幅管理
config/profiles.yaml           # 渲染配置
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

### Phase 8: API + Web UI
**目标**：提供完整的 Web 界面和 REST API

#### 8.1 交付物
```
api/routes.py           # FastAPI 路由
api/schemas.py          # API 请求/响应模型
worker/tasks.py         # Celery 异步任务
src/services/vj_generator.py # VJ 生成服务
web/                    # Next.js 前端
```

#### 8.2 任务分解
- [ ] 实现 FastAPI 路由（创建项目、上传、分析、生成、渲染、下载）
- [ ] 实现文件上传（音频、歌词）
- [ ] 实现任务队列（Celery + Redis）
- [ ] 实现进度追踪（WebSocket 或 SSE）
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
| backend-dev | Phase 1, 6, 7, 8 API层 | 待分配 |
| pipeline-dev | Phase 2, 3, 4, 5 | 待分配 |
| ui-dev | Phase 8 前端 | 待分配 |

**说明**：Phase 1 由首席架构师（我）亲自完成，建立基础框架和代码规范。

---

## 五、里程碑

| 里程碑 | 日期 | 内容 |
|--------|------|------|
| M1 | +2 周 | Phase 1-3 完成，基础管线可跑 |
| M2 | +4 周 | Phase 4-6 完成，端到端 demo |
| M3 | +5 周 | Phase 7-8 完成，可发布版本 |

---

## 六、风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 视频生成 API 不稳定 | 高 | 高 | 实现本地 fallback（视频插帧） |
| 音频分析精度不足 | 中 | 中 | 支持多算法融合 |
| LLM Prompt 调优耗时 | 高 | 中 | 提前准备 Prompt 模板库 |
| ffmpeg 性能瓶颈 | 中 | 中 | 实现 GPU 加速（NVENC） |

---

*文档版本：V1.0 | 待续...*
