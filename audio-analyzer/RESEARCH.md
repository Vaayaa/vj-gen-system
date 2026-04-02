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
