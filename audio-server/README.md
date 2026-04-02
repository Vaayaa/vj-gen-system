# VJ-Gen 音频分析服务

## 概述

专业级音频分析服务，使用 Python librosa 库实现 DJ 行业标准的 BPM 检测、调性分析和段落识别。

## 功能

- 🎵 **BPM 检测** - 使用 librosa.beat.beat_track() 行业标准算法
- 🎼 **调性分析** - chroma CQT + Krumhansl-Schmuckler 算法
- 📊 **能量计算** - RMS 能量分析
- 🥁 **节拍检测** - 精确到每个节拍的时间点
- 🎬 **段落识别** - 基于音乐理论的段落结构分析
- 🎸 **风格估算** - 根据 BPM 和能量估算音乐风格

## 启动服务

```bash
cd ~/openclaw-media/projects/vj-gen-system/audio-server
python3 server.py
```

服务运行在 http://localhost:5000

## API 接口

### POST /analyze
上传音频文件进行分析

```
curl -X POST -F "file=@song.mp3" http://localhost:5000/analyze
```

### POST /analyze-base64
发送 base64 编码的音频数据

### GET /health
健康检查

## 返回格式

```json
{
  "success": true,
  "bpm": 128.0,
  "key": "Am",
  "energy": 65.2,
  "duration": 195.5,
  "genre": "Electronic/Dance",
  "beats": [0.0, 0.468, 0.936, ...],
  "sections": [
    {
      "start": 0.0,
      "end": 16.0,
      "type": "intro",
      "name": "Intro",
      "icon": "🚀",
      "color": "#607D8B"
    }
  ]
}
```

## 段落类型

| 类型 | 名称 | 颜色 |
|------|------|------|
| intro | Intro | 🟣 灰蓝 |
| verse | Verse | 🔵 蓝 |
| preChorus | Pre-Chorus | 🔷 浅蓝 |
| chorus | Chorus | 🟣 粉红 |
| bridge | Bridge | 🟠 橙 |
| outro | Outro | 🟤 棕 |

## 依赖

- Python 3.8+
- flask
- flask-cors
- librosa
- numpy
- scipy

安装依赖:
```bash
pip3 install flask flask-cors librosa numpy scipy
```
