# 音乐段落检测技术调研报告

## 一、现有技术方案

### 1. 学术/开源方案

| 方案 | 准确度 | 速度 | 依赖 | 说明 |
|------|--------|------|------|------|
| **librosa** | ⭐⭐⭐⭐ | ⭐⭐⭐ | Python | 学术标准，功能全面 |
| **Essentia** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | C++/Python | Spotify同款，工业级 |
| **madmom** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Python/DL | 深度学习，SOTA |
| **spleeter** | ⭐⭐⭐⭐ | ⭐⭐⭐ | Python/DL | 音频源分离 |
| **chromaprint** | ⭐⭐⭐ | ⭐⭐⭐⭐ | C | AcoustID指纹 |

### 2. 商业DJ软件

| 软件 | 算法特点 |
|------|---------|
| **Mixed In Key** | 独创MIX算法，4类能量检测 |
| **rekordbox** | 16-band FFT + 频谱通量 |
| **Serato** | 动态规划节拍跟踪 |
| **Traktor** | 能量包络 + 瞬态检测 |

---

## 二、核心技术算法

### 2.1 节拍检测 (Beat Tracking)

```
流程:
1. Onset Detection (瞬态检测)
   └─ 计算频谱通量 (Spectral Flux)
   └─ 检测能量突变点

2. Tempo Induction (速度估计)
   └─ 自相关 (Autocorrelation)
   └─ 互相关 (Cross-correlation)

3. Beat Tracking (节拍跟踪)
   └─ 动态规划 (Viterbi/DP)
   └─ 递归神经网络 (RNN/LSTM)
```

### 2.2 段落检测 (Structural Segmentation)

**方法A: 基于能量**

```python
# 简化的能量分段
def segment_by_energy(audio, threshold=0.7):
    energy = compute_energy_envelope(audio)
    peaks = find_peaks(energy, threshold)
    sections = merge_close_peaks(peaks, min_gap=15)
    return sections
```

**方法B: 基于自相似矩阵 (SSM)**

```python
# Self-Similarity Matrix
def compute_ssm(audio, n_fft=2048):
    # 提取MFCC特征
    mfcc = librosa.feature.mfcc(audio, n_fft=n_fft)
    
    # 计算距离矩阵
    dist = pairwise_distances(mfcc.T)
    
    # SSM = 1 - 归一化距离
    ssm = 1 - dist / dist.max()
    return ssm
```

**方法C: 基于深度学习**

```python
# SOTA: CRF + RNN 组合
# 1. 用CRNN提取特征
# 2. 用Bi-LSTM学习时序关系
# 3. 用CRF输出段落边界
```

### 2.3 调性检测 (Key Detection)

```python
# Krumhansl-Schmuckler算法
def detect_key(chroma, sr):
    # 1. 计算平均Chroma
    avg_chroma = np.mean(chroma, axis=1)
    
    # 2. 与调性轮廓匹配
    major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, ...]
    minor_profile = [6.33, 2.68, 3.52, 5.38, 3.98, 4.21, ...]
    
    # 3. 相关性最高即为调性
    key = argmax_corr(avg_chroma, profiles)
    return key
```

---

## 三、推荐实现方案

### 方案A: 轻量级 (当前实现)

```
librosa基础功能 + 规则修正
✓ 快速实现
✓ 依赖简单
✗ 准确度有限 (~60-70%)
```

### 方案B: 专业级 (推荐)

```
Essentia + 自定义后处理
✓ 准确度高 (~85-90%)
✓ 工业级标准
✗ 安装复杂
```

### 方案C: 最高精度

```
深度学习模型 (madmom/SOTA)
✓ 最高准确度 (~90-95%)
✗ 需要GPU
✗ 训练成本高
```

---

## 四、关键参数调优

### BPM检测

```python
# 关键参数
hop_length = 512      # 越小越精确但越慢
tightness = 100       # 节拍紧密程度
bpm = 120             # 初始BPM估计

# Half/Double Time检测
if bpm < 80: bpm *= 2      # 可能是half time
if bpm > 180: bpm /= 2     # 可能是double time
```

### 段落检测

```python
# 最小段落时长
min_section_duration = 15  # 秒

# 能量阈值
energy_threshold = 0.7    # 归一化能量

# 相似度阈值
similarity_threshold = 0.8 # SSM相似度
```

---

## 五、后续研究方向

1. **融合多特征**: 能量 + MFCC + 色度 + 频谱对比度
2. **参考歌曲数据库**: 建立典型歌曲结构模板
3. **用户反馈学习**: 记录修正，逐步优化
4. **音乐类型分类**: 不同类型歌曲用不同参数

---

## 六、参考资源

- librosa: https://librosa.org/doc/latest/index.html
- Essentia: https://essentia.upf.edu/
- madmom: https://madmom.readthedocs.io/
- 论文: "Joint Segmentation and Classification of Song Structures" (ISMIR 2019)

---

## 七、实测对比结果 (2026-04-02)

### 测试歌曲
- 文件: 决无绝Hadrcore.mp3
- 时长: 39.4秒
- 类型: Electronic/Hardcore

### 结果对比

| 指标 | librosa | Essentia | 差异 |
|------|---------|----------|------|
| **BPM** | 120.0 | 98.5 | 21.5 (18%) |
| **Key** | G# | C# | 不同 |
| **Energy** | 11.5% | 12.1% | 0.6% |
| **段落数** | 4 | 4 | 一致 |

### 分析

1. **BPM差异**: 
   - librosa给出120 BPM
   - Essentia给出98.5 BPM
   - 对于电子音乐，Essentia的结果可能更准确

2. **调性差异**:
   - G# vs C# (差6个半音)
   - 可能是算法对转调的处理不同
   - 需要更多测试验证

3. **段落检测**:
   - 两者基于时长规则，结果一致
   - 真正准确的段落检测需要MFCC/SSM

### 结论

**推荐方案**: librosa + Essentia 融合

```python
# 最终BPM = 加权平均
final_bpm = librosa_bpm * 0.4 + essentia_bpm * 0.6

# 段落检测优先级:
# 1. Essentia (如可用)
# 2. librosa (备选)
# 3. 用户手动修正 (最准)
```

### madmom状态

- ❌ Python 3.10 兼容性问题
- 建议使用 conda 环境安装 Python 3.9 版本
- 如需最高精度，可单独配置madmom环境

---

## 八、madmom环境配置 (2026-04-02)

### 安装结果

**Miniconda + Python 3.9 环境**
```
环境路径: ~/miniconda3/envs/madmom-env
Python版本: 3.9.25
已安装: madmom 0.16.1, librosa, numpy 1.23.5
```

### 激活方式
```bash
source ~/miniconda3/envs/madmom-env/activate.sh
```

### 测试结果
```
合成音频测试 (120 BPM):
✅ RNN Beat Processor: 检测到120.0 BPM
✅ DBN Beat Tracker: 60 beats detected
```

### 三种方法对比脚本已更新
```bash
source ~/miniconda3/envs/madmom-env/activate.sh
python compare_methods.py audio.mp3
```

### 结论
- madmom RNN+DBN组合可以精确检测节拍
- 适合作为第三种对比方法
- 需要conda环境隔离

---

## 九、四方法对比页面

### 页面位置
`/tmp/vj-audio-compare.html`
或 `~/openclaw-media/projects/vj-gen-system/audio-analyzer/index.html`

### 功能
- 同时展示4种方法的结果
- BPM、调性、能量、段落数对比
- 波形播放
- 段落标签可视化

### 待实现
- omnizart 段落检测集成
- Essentia 详细分析
- madmom conda环境调用

### 激活madmom环境
```bash
source ~/miniconda3/envs/madmom-env/activate.sh
```

### 启动Python服务
```bash
cd ~/openclaw-media/projects/vj-gen-system/audio-server
python3 server.py
```

---

## 十、实测总结 (2026-04-02 深夜)

### 关键发现

| 方法 | BPM | 精度 | 特点 |
|------|-----|------|------|
| librosa | 120.0 | ⭐⭐⭐ | 可能是2x关系 |
| Essentia | 98.5 | ⭐⭐⭐⭐ | 工业级 |
| madmom | 98.4 | ⭐⭐⭐⭐⭐ | 与Essentia高度一致 |

**结论**: 歌曲真实BPM约98-100，librosa可能检测到half time。

### 准确度排序
1. madmom ⭐⭐⭐⭐⭐
2. Essentia ⭐⭐⭐⭐
3. librosa ⭐⭐⭐

### 推荐方案
最终BPM = (Essentia + madmom) / 2

### 文件
- `full_compare.py` - 三方法对比脚本
- `ANALYSIS_SUMMARY.md` - 分析总结
