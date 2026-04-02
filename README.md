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
│   │   ├── audio/         # 音频分析
│   │   ├── llm/           # LLM调用
│   │   ├── image/         # 图像生成
│   │   └── video/         # 视频生成
│   ├── core/              # 核心逻辑
│   │   ├── orchestrator.py
│   │   ├── workflow.py
│   │   └── router.py
│   └── pipelines/         # 处理管线
├── api/                   # API层
├── worker/                # 异步任务
├── storage/              # 存储管理
├── config/               # 配置文件
├── demos/                # 界面原型
├── docs/                 # 文档
└── tests/                # 测试
```

---

## 🚀 快速开始

```bash
# 克隆项目
git clone <repo-url>
cd vj-gen-system

# 安装依赖
pip install -r requirements.txt
npm install

# 配置环境
cp .env.example .env
# 编辑 .env 填入API Keys

# 启动开发服务器
./start.sh
```

---

## 📖 文档

- [架构设计](docs/ARCHITECTURE.md)
- [V4设计文档](docs/VJ-GEN-V4-DESIGN.md)
- [Claude Code源码分析](docs/CLAUDE-CODE-SOURCE-ANALYSIS.md)
- [API参考](docs/API.md)

---

## 🔗 相关项目

- [VJ-Design-AI](https://github.com/example/vj-design-ai) - 设计素材生成
- [OpenClaw](https://github.com/openclaw/openclaw) - AI助手框架

---

## 📄 许可证

MIT License

---

*VJ-Gen - 让视觉随音乐而生*
