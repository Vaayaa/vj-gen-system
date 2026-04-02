# VJ-Gen 系统架构评审报告

**评审日期**：2026-04-02  
**评审人**：架构评审 sub-agent  
**版本**：V0.2（基于 ARCHITECTURE.md V0.1）

---

## 一、模型选型建议（2025最新）

### 1.1 音频分析

| 任务 | 当前方案 | 最新最优方案 | 建议 |
|------|----------|-------------|------|
| BPM/节拍检测 | librosa | librosa + BeatNet | **保持 librosa**，增加 BeatNet 作为 beat tracking 备选 |
| 人声分离 | demucs | **Demucs v4 (HTDemucs)** | demucs v4 已超越 UVR5，GPU 加速更强 |
| 段落检测 | librosa (手动特征) | 深度学习结构检测 | 可考虑 OpenL3 embeddings + 聚类 |

**详细分析**：
- **librosa** 仍是本地 BPM/节拍检测的标准选择，稳定可靠
- **Demucs v4** (2024): Facebook 开源，4  stems 分离（vocals/drums/bass/other），GPU 加速，泛化能力强
- **BeatNet** (2021+): Transformer-based beat tracking，精度更高但计算量更大
- **段落检测**: 传统 librosa 方法依赖手工特征，建议后续引入深度学习

### 1.2 LLM（歌词分析/情绪识别）

| 任务 | 当前方案 | 最新最优方案 | 建议 |
|------|----------|-------------|------|
| 歌词情绪分析 | GPT-4o-mini | **GPT-4o** | GPT-4o 成本下降，多模态能力更强 |
| Prompt 增强 | GPT-4o | GPT-4o 或 **Claude 3.5 Sonnet** | Claude 3.5 Sonnet 推理更强 |
| 结构化输出 | JSON Schema | 原生 **function_calling / tool_use** | GPT-4o 和 Claude 都支持 |

**详细分析**：
- **GPT-4o** (2024年5月): 128K 上下文，原生多模态，结构化输出能力强，成本比 GPT-4 降低 50%
- **Claude 3.5 Sonnet** (2024年10月): 200K 上下文，Instruction following 最佳，工具调用（tool use）成熟
- **Gemini 1.5 Pro**: 1M 上下文，适合超长歌词分析，但成本高
- **建议优先级**: GPT-4o（性价比） > Claude 3.5 Sonnet（质量） > Gemini（超长文本）

### 1.3 图像生成

| 任务 | 当前方案 | 最新最优方案 | 建议 |
|------|----------|-------------|------|
| 关键帧生成（速度） | SDXL-Turbo | **FLUX.1 schnell** | FLUX.1 schnell 速度相当，质量更好 |
| 关键帧生成（质量） | DALL-E 3 | **FLUX.1 dev** 或 DALL-E 3 | FLUX.1 dev 质量更好但更慢 |
| 风格化 | Leonardo | FLUX.1 + ControlNet | 更灵活 |

**详细分析**：
- **FLUX.1** (Black Forest Labs, 2024年8月): 
  - FLUX.1 [schnell]: 4步生成，速度最快，适合 VJ 实时场景
  - FLUX.1 [dev]: 质量最佳，prompt adherence 超越 DALL-E 3
  - FLUX.1 [pro]: 闭源 API，价格较高
- **DALL-E 3**: prompt following 最佳，但已落后于 FLUX.1 质量
- **Imagen 3** (Google): 仅通过 Vertex AI，集成成本高
- **Midjourney V6**: 质量最佳但 Discord 专用，不适合自动化管线
- **VJ 场景推荐**: FLUX.1 [schnell] 作为 primary（速度），DALL-E 3 作为 fallback（兼容性）

### 1.4 视频生成

| 任务 | 当前方案 | 最新最优方案 | 建议 |
|------|----------|-------------|------|
| 短视频生成 (≤10s) | Runway Gen-3 | **Runway Gen-3 Alpha** 或 **Pika 2.0** | 两者质量相近 |
| 长视频生成 (≤30s) | Kling 1.0 | **Kling 1.5** | Kling 1.5 运动控制更好 |
| 开源备选 | 无 | **HunyuanVideo** (腾讯) | 最好的开源视频生成 |
| 风格化 | Looperator | **Runway Gen-3 + style preset** | 更原生 |

**详细分析**：
- **Runway Gen-3 Alpha** (2024年6月): 视频一致性最佳，Gen-3 Alpha Turbo 速度更快
- **Pika 2.0** (2024年12月): Motion controls 优秀，Canvas 编辑，适合 VJ 场景
- **Kling 1.5** (2025年): 30s 生成，camera motion 控制强，支持 1080p
- **HunyuanVideo** (腾讯, 2024年11月): 开源，13B 参数，质量接近闭源，商业友好
- **Sora**: 质量最佳但不对外开放
- **VJ 场景推荐**: Runway Gen-3 Alpha (一致性) + Kling 1.5 (长片段) + HunyuanVideo (开源备选)

### 1.5 视频增强（超分/补帧）

| 任务 | 当前方案 | 最新最优方案 | 建议 |
|------|----------|-------------|------|
| 视频超分 | Topaz Video AI | **Topaz Video AI 5** 或 **Real-ESRGAN** | 商业用 Topaz，本地用 Real-ESRGAN |
| 帧率插值 | Topaz | **RIFE** 或 Topaz | RIFE 更快，Topaz 质量更好 |
| 去噪 | Topaz | Topaz Video AI 5 | Gemini 噪点移除模型 |

**详细分析**：
- **Topaz Video AI 5** (2024): 独立桌面应用，API 访问有限，Gemini 模型质量提升
- **Real-ESRGAN**: 开源，可本地部署，无 API 成本
- **RIFE**: 帧率插值开源方案，速度快
- **HAT** (Hybrid Attention Transformer, 2024): 最新超分模型，超越 SwinIR

---

## 二、架构调整建议

### 2.1 模型路由策略（高优先级）

**当前问题**：
- routing.yaml 中的 `runway-gen3` 和 `kling-1.0` 已过时
- 没有考虑模型可用性动态路由
- 缺乏 API 健康检查驱动的自动 failover

**建议调整**：
```yaml
# routing.yaml 更新
video_gen:
  strategy: quality_aware  # 改为质量优先
  routes:
    - task: vj_clip_short
      provider: runway
      model: gen-3-alpha-turbo  # 更新为最新模型
      priority: 1
      health_check: true  # 启用健康检查
      fallback:
        - provider: pika
          model: pika-2.0
          priority: 2
    
    - task: vj_clip_long
      provider: kling
      model: kling-1.5  # 更新为 1.5
      priority: 1
      health_check: true
      fallback:
        - provider: hunyuan
          model: hunyuanvideo-13b
          priority: 2
```

### 2.2 适配器接口扩展（高优先级）

**问题**：当前适配器不支持最新模型特性

**需要增加的能力**：
1. **Function Calling / Tool Use** 支持
   ```python
   # LLMAdapter 需要增加
   @abstractmethod
   async def function_call(
       self,
       functions: list[dict],
       prompt: str,
       **kwargs,
   ) -> AdapterResult[FunctionCallResult]:
       """原生函数调用能力"""
       pass
   ```

2. **多模态输入支持**
   ```python
   # 图像/视频适配器需要增加
   @abstractmethod
   async def generate_with_mask(
       self,
       prompt: str,
       mask_path: str,
       **kwargs,
   ) -> AdapterResult[ImageResult]:
       """带 mask 的图像生成（Inpainting）"""
       pass
   ```

3. **模型健康状态推送**
   ```python
   # Router 需要增加
   async def get_healthy_model(self, task_type: str) -> Optional[ModelRouteConfig]:
       """获取当前健康的模型"""
       pass
   ```

### 2.3 本地 fallback 能力（中优先级）

**问题**：视频生成完全依赖外部 API，无本地 fallback

**建议增加**：
```
本地视频生成备选方案：
1. 帧插值 fallback: 当 API 超时，使用 RIFE 插值生成运动效果
2. 关键帧放大: 使用 Real-ESRGAN 放大关键帧作为"静态视频"
3. 循环 GIF fallback: 将关键帧转为循环 GIF，保证基本可看性
```

**新增适配器**：
```python
# src/adapters/video/rife_adapter.py
class RIFEAdapter:
    """RIFE 帧率插值适配器（本地 fallback）"""
    
# src/adapters/video/realesrgan_adapter.py  
class RealESRGANAdapter:
    """Real-ESRGAN 超分适配器（本地 fallback）"""
```

### 2.4 管线设计优化（中优先级）

**当前管线问题**：
1. `AudioPipeline` 中人声分离与节拍分析是串行执行
2. LLM 分析歌词时未利用音频特征

**优化建议**：
```python
# 并行化改造
async def process(self, audio_path: str):
    # 三个任务并行
    bpm_task = self.librosa.detect_bpm(audio_path)
    beats_task = self.librosa.extract_beats(audio_path)
    vocal_task = self.demucs.separate_vocals(audio_path)  # 并行启动
    
    bpm, beats = await bpm_task, await beats_task
    vocal_path, _ = await vocal_task  # 等待 vocals 用于歌词分析
    
    # 将 vocal_path 传给 LLM 做歌词分析（语音识别）
    lyric_result = await self.llm.analyze_lyrics_from_vocal(vocal_path)
```

### 2.5 成本控制增强（中优先级）

**建议增加**：
```yaml
# routing.yaml 新增
cost_control:
  monthly_budget: 1000  # 美元
  alert_threshold: 0.8  # 80% 时报警
  auto_degrade:
    enabled: true
    image_gen: "skip"  # 预算耗尽时跳过
    video_gen: "interpolate"
  model_swap:
    # 成本触发切换
    - condition: "cost_exceeded"
      from: dall-e-3
      to: flux-1-schnell
```

---

## 三、风险评估

### 3.1 高风险

| 风险 | 描述 | 缓解方案 |
|------|------|----------|
| **视频 API 不稳定** | Runway/Kling API 可能宕机或超时 | 1. 实现 API 健康检查 + 自动 failover<br>2. 增加本地 fallback（RIFE 插值）<br>3. 实现"静态关键帧循环"降级 |
| **视频生成成本失控** | 按帧计费，大项目成本可能很高 | 1. 设置月度预算上限<br>2. 实现成本监控 Dashboard<br>3. 默认使用低成本模型 |
| **模型更新频繁** | FLUX.1/Kling 等快速迭代 | 1. 架构支持快速替换 adapter<br>2. 不 hardcode 模型版本号<br>3. 使用 latest tag |

### 3.2 中风险

| 风险 | 描述 | 缓解方案 |
|------|------|----------|
| **Demucs v4 计算量大** | GPU 内存要求高 | 1. 提供 CPU fallback（更慢但可用）<br>2. 实现批处理减少显存峰值 |
| **LLM 结构化输出不稳定** | JSON 解析偶尔失败 | 1. 增加重试机制<br>2. 使用 function calling 替代 prompt engineering<br>3. 实现输出验证 |
| **音频段落检测精度** | 复杂音乐结构可能误判 | 1. 增加 confidence score<br>2. 提供人工校正接口<br>3. 多模型 ensemble |

### 3.3 低风险

| 风险 | 描述 | 缓解方案 |
|------|------|----------|
| **FLUX.1 许可问题** | 非商业用途限制 | 1. 确认使用场景许可<br>2. 保留 DALL-E 作为备选 |
| **跨模型时间对齐** | 音频/歌词/视频时间戳不一致 | 1. 统一时间基准（毫秒）<br>2. 实现时间戳验证<br>3. 允许人工微调 |

---

## 四、优先级排序

### 🔴 高优先级（V0.2 必须解决）

1. **更新 routing.yaml 模型版本**
   - Runway Gen-3 → Gen-3 Alpha Turbo
   - Kling 1.0 → Kling 1.5
   - SDXL-Turbo → FLUX.1 [schnell]

2. **实现 API 健康检查驱动的路由**
   - 在 Router 中集成 health check
   - 失败时自动切换到备选模型

3. **增加本地 Video Fallback**
   - 集成 RIFE 帧率插值
   - 实现"静态关键帧循环"降级模式

### 🟡 中优先级（V0.3 考虑）

4. **LLM Adapter 增加 Function Calling**
   - GPT-4o 原生 function calling
   - Claude 3.5 tool use

5. **并行化管线改造**
   - 音频分析与人声分离并行
   - LLM 分析时传入 vocal features

6. **成本监控与控制**
   - 实现使用量 tracking
   - 增加月度预算配置

### 🟢 低优先级（V1.0 考虑）

7. **段落检测深度学习升级**
   - 引入 OpenL3 或 MusicNN
   - 多模型 ensemble

8. **多模态原生支持**
   - GPT-4o 直接分析 vocal 音频
   - 减少 ASR 依赖

9. **实时预览能力**
   - 低分辨率预览管线
   - WebSocket 推送生成进度

---

## 五、决策点（需要确认）

1. **视频生成 Provider 选择**：
   - Runway Gen-3 Alpha Turbo vs Pika 2.0，哪个作为 primary？
   - Kling 1.5 API 是否已开放？

2. **开源 vs 闭源策略**：
   - 是否需要本地视频生成能力（HunyuanVideo）？
   - FLUX.1 [dev] 商业使用许可是否满足需求？

3. **成本上限**：
   - 月度 API 预算多少？
   - 预算耗尽时的降级策略？

4. **Vocal 分析方式**：
   - 是否需要 ASR（语音识别）从人声中提取歌词？
   - 还是依赖用户提供的 LRC 歌词文件？

---

## 六、附录

### A. 模型版本对照表

| 模型类别 | 当前架构中的名称 | 2025最新版本 | 状态 |
|----------|------------------|-------------|------|
| 音频 - BPM | librosa | librosa + BeatNet | ⚠️ 需增量 |
| 音频 - 分离 | demucs | Demucs v4 HTDemucs | ⚠️ 需升级 |
| LLM - 分析 | GPT-4o-mini | GPT-4o | ✅ 路由更新 |
| LLM - 推理 | Claude 3.5 Sonnet | Claude 3.5 Sonnet | ✅ 已是最新 |
| 图像 - 速度 | SDXL-Turbo | FLUX.1 [schnell] | 🔴 需更换 |
| 图像 - 质量 | DALL-E 3 | FLUX.1 [dev] | 🟡 待评估 |
| 视频 - 短 | Runway Gen-3 | Gen-3 Alpha Turbo | 🔴 需更新 |
| 视频 - 长 | Kling 1.0 | Kling 1.5 | 🔴 需更新 |
| 视频 - 开源 | 无 | HunyuanVideo | 🟢 可新增 |
| 超分 | Topaz Video AI | Video AI 5 | ✅ 可选升级 |

### B. 关键文件清单

```
需要修改的文件：
- config/routing.yaml         # 更新模型版本和策略
- src/adapters/llm/base.py    # 增加 function_calling
- src/adapters/video/         # 更新 Runway/Kling adapter 版本
- src/adapters/image/         # 增加 FLUX adapter

需要新增的文件：
- src/adapters/video/rife_adapter.py       # 本地 fallback
- src/adapters/video/realesrgan_adapter.py  # 本地超分
- src/adapters/video/hunyuan_adapter.py     # 开源视频生成
```

---

*评审完成。建议按优先级排序逐步实施。*
