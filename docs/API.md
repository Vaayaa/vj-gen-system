# VJ-Gen API 参考文档

**API 版本**: v1.0.0  
**Base URL**: `http://localhost:8000`  
**文档地址**: `http://localhost:8000/docs` (Swagger UI)

---

## 目录

- [认证](#认证)
- [项目接口](#项目接口)
- [文件上传](#文件上传)
- [分析接口](#分析接口)
- [生成接口](#生成接口)
- [渲染接口](#渲染接口)
- [WebSocket](#websocket)
- [数据类型](#数据类型)
- [错误码](#错误码)

---

## 认证

当前版本未启用认证，请在生产环境中自行添加。

---

## 项目接口

### 创建项目

`POST /api/v1/projects`

创建新的 VJ 项目。

**请求体**:

```json
{
  "name": "我的VJ项目",
  "description": "这是一个测试项目"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 项目名称 (1-255字符) |
| description | string | ❌ | 项目描述 (最多1000字符) |

**响应**:

```json
{
  "success": true,
  "message": "Project created successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "我的VJ项目",
    "status": "created"
  }
}
```

---

### 列出所有项目

`GET /api/v1/projects`

**响应**:

```json
{
  "success": true,
  "message": "Found 2 projects",
  "data": {
    "projects": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "我的VJ项目",
        "status": "completed",
        "created_at": "2026-04-02T10:00:00",
        "updated_at": "2026-04-02T12:30:00"
      }
    ]
  }
}
```

---

### 获取项目详情

`GET /api/v1/projects/{project_id}`

获取指定项目的完整信息，包括分析结果和镜头脚本。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| project_id | string | 项目ID (UUID) |

**响应**:

```json
{
  "success": true,
  "message": "Project retrieved successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "我的VJ项目",
    "status": "script_generated",
    "audio_path": "/storage/550e.../audio/song.mp3",
    "lyric_path": "/storage/550e.../lyrics/lyrics.lrc",
    "audio_analysis": {
      "bpm": 128.0,
      "time_signature": "4/4",
      "duration": 180.0,
      "beats": [...],
      "sections": [...]
    },
    "shot_script": {
      "items": [...],
      "total_duration": 180.0,
      "resolution": [1920, 1080],
      "fps": 30
    },
    "render_profiles": [
      {"name": "1080p", "width": 1920, "height": 1080}
    ],
    "created_at": "2026-04-02T10:00:00",
    "updated_at": "2026-04-02T11:00:00"
  }
}
```

---

### 删除项目

`DELETE /api/v1/projects/{project_id}`

删除项目及其所有关联文件。

**响应**:

```json
{
  "success": true,
  "message": "Project deleted successfully"
}
```

---

## 文件上传

### 上传音频/歌词

`POST /api/v1/projects/{project_id}/upload`

上传音频文件和可选的歌词文件。

**路径参数**: `project_id` - 项目ID

**表单参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| audio | file | ✅ | 音频文件 (mp3/wav/flac/ogg) |
| lyrics | file | ❌ | 歌词文件 (lrc/txt) |

**cURL 示例**:

```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/upload \
  -F "audio=@/path/to/song.mp3" \
  -F "lyrics=@/path/to/lyrics.lrc"
```

**响应**:

```json
{
  "success": true,
  "message": "Files uploaded successfully",
  "data": {
    "audio_path": "/storage/550e.../audio/song.mp3",
    "lyrics_path": "/storage/550e.../lyrics/lyrics.lrc"
  }
}
```

---

## 分析接口

### 触发分析

`POST /api/v1/projects/{project_id}/analyze`

启动音频和歌词分析管线。分析是异步执行的，使用 WebSocket 接收进度更新。

**前置条件**: 项目必须已上传音频文件

**分析流程**:

1. `audio_analysis` - 音频分析 (BPM/节拍/段落)
2. `beat_detection` - 节拍检测
3. `lyric_parsing` - 歌词解析
4. `shot_script_generation` - 镜头脚本生成
5. `completed` - 分析完成

**响应**:

```json
{
  "success": true,
  "message": "Analysis started"
}
```

**WebSocket 进度消息示例**:

```json
{
  "type": "progress",
  "project_id": "550e8400-...",
  "step": "beat_detection",
  "message": "检测节拍...",
  "progress": 40,
  "timestamp": "2026-04-02T10:05:00"
}
```

---

## 生成接口

### 触发VJ生成

`POST /api/v1/projects/{project_id}/generate`

启动 VJ 素材生成管线（静帧 + 视频片段）。

**前置条件**: 项目必须已完成分析 (`status == "script_generated"`)

**生成流程**:

1. `keyframe_generation` - 生成关键帧
2. `video_synthesis` - 合成视频片段
3. `timeline_compilation` - 编排时间线
4. `render_preparation` - 准备渲染
5. `completed` - 生成完成

**响应**:

```json
{
  "success": true,
  "message": "Generation started"
}
```

---

## 渲染接口

### 触发渲染

`POST /api/v1/projects/{project_id}/render`

启动视频渲染管线，将时间线合成为最终视频文件。

**路径参数**: `project_id` - 项目ID

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| profile | string | "1080p" | 渲染配置名称 |

**前置条件**: 项目必须已完成脚本生成

**响应**:

```json
{
  "success": true,
  "message": "Rendering started for profile: 1080p"
}
```

---

### 获取下载链接

`GET /api/v1/projects/{project_id}/download/{profile}`

获取渲染完成后的视频下载链接。

**响应**:

```json
{
  "success": true,
  "message": "Download ready",
  "data": {
    "download_url": "/api/v1/files/550e.../renders/1080p/vj_output_1080p.mp4",
    "filename": "我的VJ项目_1080p.mp4"
  }
}
```

---

### 下载文件

`GET /api/v1/files/{project_id}/renders/{profile}/{filename}`

直接下载渲染后的视频文件。

**响应**: 二进制视频文件流 (`video/mp4`)

---

### 获取项目状态

`GET /api/v1/projects/{project_id}/status`

获取项目当前状态（轻量级接口）。

**响应**:

```json
{
  "success": true,
  "message": "Status retrieved",
  "data": {
    "id": "550e8400-...",
    "name": "我的VJ项目",
    "status": "rendering",
    "updated_at": "2026-04-02T12:00:00"
  }
}
```

---

## WebSocket

### 连接

`WS /ws/{project_id}`

连接到指定项目的 WebSocket 实时进度通道。

**cURL 测试**:

```bash
wscat -c ws://localhost:8000/ws/550e8400-e29b-41d4-a716-446655440000
```

### 客户端发送

| 消息 | 说明 |
|------|------|
| `ping` | 心跳保活，服务端返回 `pong` |

### 服务端接收

#### 状态更新

```json
{
  "type": "status_update",
  "project_id": "550e8400-...",
  "status": "analyzing",
  "timestamp": "2026-04-02T10:00:00"
}
```

#### 进度更新

```json
{
  "type": "progress",
  "project_id": "550e8400-...",
  "step": "beat_detection",
  "message": "检测节拍...",
  "progress": 40,
  "timestamp": "2026-04-02T10:00:00"
}
```

#### 错误消息

```json
{
  "type": "error",
  "project_id": "550e8400-...",
  "message": "音频文件格式不支持"
}
```

---

## 渲染配置

### 列出可用配置

`GET /api/v1/profiles`

列出所有可用的渲染配置。

**响应**:

```json
{
  "success": true,
  "message": "Render profiles",
  "data": {
    "profiles": [
      {
        "name": "1080p",
        "width": 1920,
        "height": 1080,
        "aspect_ratio": "16:9",
        "fps": 30,
        "description": "Full HD landscape"
      },
      {
        "name": "1080p_vertical",
        "width": 1080,
        "height": 1920,
        "aspect_ratio": "9:16",
        "fps": 30,
        "description": "Full HD vertical (TikTok/Reels)"
      },
      {
        "name": "720p",
        "width": 1280,
        "height": 720,
        "aspect_ratio": "16:9",
        "fps": 30,
        "description": "HD ready"
      },
      {
        "name": "square",
        "width": 1080,
        "height": 1080,
        "aspect_ratio": "1:1",
        "fps": 30,
        "description": "Square format"
      }
    ]
  }
}
```

---

## 数据类型

### ProjectStatus (项目状态)

| 值 | 说明 |
|----|------|
| `created` | 项目已创建 |
| `uploading` | 文件上传中 |
| `uploaded` | 文件上传完成 |
| `analyzing` | 分析中 |
| `script_generated` | 脚本已生成 |
| `generating` | 素材生成中 |
| `rendering` | 渲染中 |
| `completed` | 完成 |
| `failed` | 失败 |

### SectionType (音频段落类型)

| 值 | 说明 |
|----|------|
| `intro` | 前奏 |
| `verse` | 主歌 |
| `pre_chorus` | 预副歌 |
| `chorus` | 副歌 |
| `drop` | Drop/高潮 |
| `bridge` | 桥段 |
| `outro` | 尾奏 |
| `break` | Break |
| `silence` | 静音 |

### AspectRatio (画幅比例)

| 值 | 说明 |
|----|------|
| `16:9` | 宽屏 (1920x1080) |
| `9:16` | 竖屏 (1080x1920) |
| `1:1` | 方形 (1080x1080) |
| `4:3` | 经典 (1440x1080) |
| `21:9` | 电影 (2560x1080) |

### LyricSentiment (歌词情绪)

| 值 | 说明 |
|----|------|
| `calm` | 平静 |
| `build` | 渐进 |
| `climax` | 高潮 |
| `dark` | 暗调 |
| `bright` | 明亮 |
| `neutral` | 中性 |

### TransitionHint (转场提示)

| 值 | 说明 |
|----|------|
| `cut` | 硬切 |
| `fade` | 淡入淡出 |
| `dissolve` | 叠化 |
| `wipe` | 擦除 |
| `zoom` | 缩放 |
| `slide` | 滑动 |
| `glitch` | 故障 |

### CameraBehavior (相机行为)

| 值 | 说明 |
|----|------|
| `static` | 静止 |
| `pan` | 水平移动 |
| `tilt` | 垂直移动 |
| `dolly` | 推进/拉远 |
| `zoom_in` | 放大 |
| `zoom_out` | 缩小 |
| `handheld` | 手持抖动 |
| `orbit` | 环绕 |
| `rise` | 上升 |
| `fall` | 下降 |

---

## 错误码

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### API 错误响应格式

```json
{
  "success": false,
  "message": "Project not found",
  "error_code": "PROJECT_NOT_FOUND"
}
```

### 常见错误

| error_code | HTTP状态 | 说明 |
|------------|----------|------|
| `PROJECT_NOT_FOUND` | 404 | 项目不存在 |
| `NO_AUDIO_FILE` | 400 | 未上传音频文件 |
| `INVALID_STATUS` | 400 | 当前状态不允许此操作 |
| `RENDER_NOT_FOUND` | 404 | 渲染文件不存在 |
| `FILE_TYPE_NOT_SUPPORTED` | 400 | 不支持的文件类型 |

---

## 完整调用流程

```bash
# 1. 创建项目
PROJECT_ID=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "测试项目"}' | jq -r '.data.id')

# 2. 打开 WebSocket 监听（后台）
wscat -c ws://localhost:8000/ws/$PROJECT_ID &

# 3. 上传文件
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/upload \
  -F "audio=@song.mp3" \
  -F "lyrics=@lyrics.lrc"

# 4. 触发分析
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/analyze

# 5. 等待分析完成（观察 WebSocket 消息）

# 6. 触发生成
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/generate

# 7. 触发渲染
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/render?profile=1080p"

# 8. 获取下载链接
curl http://localhost:8000/api/v1/projects/$PROJECT_ID/download/1080p
```

---

*API 版本: v1.0.0 | 文档更新: 2026-04-02*
