# VJ-Gen 多模型VJ生成系统

> 从「音频+歌词」到「完整VJ素材」的全自动AI生产管线

---

## 🎯 项目定位

类比产品：**LoveArt / TapNow / Runway + 专业VJ工具**

核心价值：AI驱动的视觉内容自动生成，服务于VJ现场表演、视频制作、音乐可视化等场景。

---

## ✨ 核心功能

- 🎵 **音频分析** - BPM检测、节拍提取、段落结构、能量曲线
- 📝 **歌词NLP** - 分句分词、情绪分析、Prompt生成、时间对齐
- 🎨 **视觉生成** - 静帧生成、视频生成、风格迁移、超分补帧
- ⏱️ **时间编排** - 片段拼接、转场处理、节拍对齐、多画幅渲染

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户层 (Frontend)                      │
│         Web UI / API Gateway / 预览 / 多画幅导出           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    任务编排层 (Orchestrator)                │
│      Workflow Engine │ Task Queue │ 断点续跑 │ 重试机制    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   音频分析管线  │   │   歌词NLP管线  │   │   视觉生成管线  │
│  • BPM检测    │   │  • 分句分词    │   │  • 静帧生成    │
│  • 节拍提取    │   │  • 情绪分析    │   │  • 视频生成    │
│  • 段落结构    │   │  • Prompt生成  │   │  • 超分/补帧   │
└───────────────┘   └───────────────┘   └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    时间线编排层 (Timeline)                  │
│           片段拼接 │ 转场 │ 节拍对齐 │ ffmpeg             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI / Node.js |
| 任务队列 | Celery + Redis / BullMQ |
| 音频处理 | librosa, demucs, Essentia |
| 视频处理 | ffmpeg, moviepy, OpenCV |
| 前端 | Next.js + React + Tailwind |
| AI模型 | MiniMax / Gemini / Kling / Seedance |

---

## 📁 目录结构

```
vj-gen-system/
├── src/                    # 核心源代码
│   ├── adapters/          # 模型适配器
│   │   ├── audio/         # 音频分析 (librosa_adapter.py)
│   │   ├── llm/          # LLM调用 (openai/anthropic)
│   │   ├── image/        # 图像生成 (SD/DALL-E/Leonardo)
│   │   └── video/        # 视频生成 (Runway/Kling/Topaz)
│   ├── core/              # 核心逻辑
│   │   ├── timeline.py    # 时间线数据结构
│   │   ├── beat_sync.py  # 节拍同步
│   │   ├── transitions.py # 转场处理
│   │   └── router.py      # 模型路由
│   ├── pipelines/         # 处理管线
│   │   ├── audio_pipeline.py
│   │   ├── lyric_pipeline.py
│   │   ├── image_pipeline.py
│   │   └── video_pipeline.py
│   ├── models/           # Pydantic 数据模型
│   │   └── schemas.py
│   ├── services/         # 服务层
│   └── prompts/          # Prompt 模板
├── api/                   # FastAPI 层 (api/main.py)
├── worker/                # Celery 异步任务
├── storage/              # 存储 (audio/lyrics/output/temp)
├── config/               # 配置文件
│   ├── models.yaml       # 模型配置
│   └── routing.yaml      # 路由策略
├── demos/                # 界面原型
├── docs/                 # 文档
└── tests/                # 测试
```

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis（用于任务队列）
- ffmpeg（系统级依赖）

### 1. 克隆并安装

```bash
git clone <repo-url>
cd vj-gen-system

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入必要的 API Keys
# 必须配置：
# - OPENAI_API_KEY      (GPT-4 用于歌词分析和Prompt生成)
# - ANTHROPIC_API_KEY   (Claude 备选)
# - REPLICATE_API_TOKEN (Stable Diffusion)
# - KLING_API_KEY       (视频生成)
# 可选配置：
# - MINIMAX_API_KEY
# - RUNWAY_API_KEY
# - DEMUCS_MODEL_DIR    (人声分离模型路径)
```

### 3. 启动服务

```bash
# 方式一：一键启动（推荐）
./start.sh

# 方式二：分步启动
# 终端 1：启动 FastAPI 服务
cd api && uvicorn main:app --reload --port 8000

# 终端 2：启动 Celery Worker
celery -A worker.tasks worker --loglevel=info

# 终端 3：启动前端开发服务器
cd frontend && npm run dev
```

### 4. 访问系统

- **API 文档**: http://localhost:8000/docs
- **前端界面**: http://localhost:3000
- **健康检查**: http://localhost:8000/health

---

## 📖 工作流程

### 完整生成流程

```
1. 创建项目 → 2. 上传音频/歌词 → 3. 分析 → 4. 生成脚本 → 5. 生成视觉 → 6. 渲染导出
```

### API 调用示例（cURL）

```bash
# 1. 创建项目
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "我的VJ项目", "description": "测试项目"}'

# 2. 上传音频文件
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/upload \
  -F "audio=@song.mp3" \
  -F "lyrics=@lyrics.lrc"

# 3. 触发分析
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/analyze

# 4. 触发生成
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/generate

# 5. 触发渲染
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/render?profile=1080p

# 6. 获取下载链接
curl http://localhost:8000/api/v1/projects/{project_id}/download/1080p
```

### WebSocket 实时进度

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{project_id}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.message, data.progress);
};
```

---

## 🔧 本地开发

### 代码结构

```
src/
├── adapters/     # 适配器模式，屏蔽不同模型 API 差异
├── core/         # 核心业务逻辑，与模型无关
├── pipelines/    # 管线编排，串联各 Adapter
└── models/       # Pydantic 模型定义
```

### 添加新的模型适配器

1. 在 `src/adapters/{type}/` 下创建新文件
2. 继承 `BaseAdapter` 或对应的类型适配器基类
3. 实现抽象方法
4. 在 `config/models.yaml` 中注册

```python
from src.adapters.image.base import ImageGenAdapter

class MyImageAdapter(ImageGenAdapter):
    async def generate(self, prompt: str, **kwargs) -> str:
        # 调用新的图像生成 API
        return image_url
```

### 运行测试

```bash
pytest tests/ -v
pytest tests/adapters/ -v  # 仅测试适配器
```

---

## 📂 存储结构

```
storage/
├── {project_id}/
│   ├── audio/           # 上传的音频文件
│   ├── lyrics/          # 上传的歌词文件
│   ├── analysis/        # 分析结果缓存
│   ├── keyframes/      # 生成的静帧
│   ├── clips/          # 生成的视频片段
│   └── renders/        # 最终渲染输出
│       ├── 1080p/
│       ├── 1080p_vertical/
│       └── square/
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 详细架构设计 |
| [VJ-GEN-V4-DESIGN.md](docs/VJ-GEN-V4-DESIGN.md) | V4 UI/UX 设计方案 |
| [API.md](docs/API.md) | API 参考文档 |
| [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) | 开发计划与里程碑 |
| [CLAUDE-CODE-SOURCE-ANALYSIS.md](docs/CLAUDE-CODE-SOURCE-ANALYSIS.md) | 源码分析 |

---

## 🔗 相关项目

- [VJ-Design-AI](https://github.com/example/vj-design-ai) - 设计素材生成
- [OpenClaw](https://github.com/openclaw/openclaw) - AI助手框架

---

## 📄 许可证

MIT License

---

*VJ-Gen - 让视觉随音乐而生*
