"""
VJ系统 Madmom 音频节拍检测模块
集成专业的 Madmom 库进行 downbeat（小节起点）检测

兼容性：
- Python 3.10+ / NumPy 1.24+ / NumPy 2.x 需要兼容性修复
- 参考 CutClaw 项目的 monkey-patch 方案

用法:
    from audio_madmom import MadmomAnalyzer
    analyzer = MadmomAnalyzer()
    result = analyzer.analyze("audio.wav")
"""

# ============ Python 3.10+ / NumPy 兼容性修复 ============
# 必须在导入 madmom 之前执行

import collections
import collections.abc
for attr in ('MutableSequence', 'Iterable', 'Mapping', 'MutableMapping', 'Callable'):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

import numpy as np
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    if not hasattr(np, 'float'):
        np.float = np.float64
    if not hasattr(np, 'int'):
        np.int = np.int64
    if not hasattr(np, 'complex'):
        np.complex = np.complex128
    if not hasattr(np, 'object'):
        np.object = np.object_
    if not hasattr(np, 'bool'):
        np.bool = np.bool_
    if not hasattr(np, 'str'):
        np.str = np.str_

# ============ NumPy 2.x 兼容性修复 for DBNDownBeatTrackingProcessor ============

import madmom.features.downbeats as _downbeats_module
import itertools as _it

def _patched_dbn_process(self, activations, **kwargs):
    """修复 NumPy 2.x 兼容性的 DBNDownBeatTrackingProcessor.process 方法"""
    first = 0
    if self.threshold:
        idx = np.nonzero(activations >= self.threshold)[0]
        if idx.any():
            first = max(first, np.min(idx))
            last = min(len(activations), np.max(idx) + 1)
        else:
            last = first
        activations = activations[first:last]
    
    if not activations.any():
        return np.empty((0, 2))
    
    results = list(self.map(_downbeats_module._process_dbn, 
                            zip(self.hmms, _it.repeat(activations))))
    
    # 修复: 使用列表推导式获取 log probabilities
    log_probs = [r[1] for r in results]
    best = np.argmax(log_probs)
    
    path, _ = results[best]
    st = self.hmms[best].transition_model.state_space
    om = self.hmms[best].observation_model
    positions = st.state_positions[path]
    beat_numbers = positions.astype(int) + 1
    
    if self.correct:
        beats = np.empty(0, dtype=np.int64)
        beat_range = om.pointers[path] >= 1
        idx = np.nonzero(np.diff(beat_range.astype(np.int64)))[0] + 1
        if beat_range[0]:
            idx = np.r_[0, idx]
        if beat_range[-1]:
            idx = np.r_[idx, beat_range.size]
        if idx.any():
            for left, right in idx.reshape((-1, 2)):
                peak = np.argmax(activations[left:right]) // 2 + left
                beats = np.hstack((beats, peak))
    else:
        beats = np.nonzero(np.diff(beat_numbers))[0] + 1
    
    return np.vstack(((beats + first) / float(self.fps), beat_numbers[beats])).T

# 应用 monkey-patch（延迟到实际使用时）
_MADMOM_PATCHED = False

def _ensure_madmom_patched():
    global _MADMOM_PATCHED
    if not _MADMOM_PATCHED:
        from madmom.features.downbeats import DBNDownBeatTrackingProcessor
        DBNDownBeatTrackingProcessor.process = _patched_dbn_process
        _MADMOM_PATCHED = True

# ============ 核心导入 ============

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor


# ============ 工具函数 ============

def _ensure_wav_for_madmom(audio_path: str) -> str:
    """确保音频文件是 WAV 格式（madmom 需要）"""
    p = Path(audio_path)
    if p.suffix.lower() in {".wav", ".wave"}:
        return audio_path
    
    # 转换到临时 WAV 文件
    wav_path = p.with_name(f"{p.stem}__vj_madmom.wav")
    
    try:
        src_mtime = p.stat().st_mtime
        if wav_path.exists() and wav_path.stat().st_mtime >= src_mtime:
            return str(wav_path)
    except Exception:
        pass
    
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd = [
            ffmpeg, "-y", "-i", str(p),
            "-vn", "-ac", "1", "-acodec", "pcm_s16le",
            str(wav_path)
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0 or not wav_path.exists():
            raise RuntimeError(f"ffmpeg conversion failed: {proc.stderr.strip()}")
        return str(wav_path)
    
    raise RuntimeError(f"Cannot convert {audio_path} to WAV. Install ffmpeg or use .wav format.")


import shutil

# ============ 主分析器类 ============

class MadmomAnalyzer:
    """
    Madmom 音频分析器
    
    提供专业的 downbeat（小节起点）检测能力，
    兼容 VJ 系统的 AudioAnalysisResult 数据格式。
    """
    
    def __init__(
        self,
        beats_per_bar: int = 4,
        min_bpm: float = 55.0,
        max_bpm: float = 215.0,
        dbn_threshold: float = 0.05,
        fps: int = 100,
        transition_lambda: float = 100.0,
        observation_lambda: int = 16,
        correct_beats: bool = True,
        num_tempi: int = 60,
    ):
        """
        初始化 Madmom 分析器
        
        Args:
            beats_per_bar: 每小节拍数 (默认 4)
            min_bpm: 最小 BPM (默认 55)
            max_bpm: 最大 BPM (默认 215)
            dbn_threshold: DBN 激活阈值 (默认 0.05)
            fps: 帧率 (默认 100)
            transition_lambda: 速度变化分布参数 (默认 100)
            observation_lambda: 节拍周期分段数 (默认 16)
            correct_beats: 是否对齐节拍到峰值 (默认 True)
            num_tempi: 建模的速度数量 (默认 60)
        """
        self.beats_per_bar = [beats_per_bar]
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.dbn_threshold = dbn_threshold
        self.fps = fps
        self.transition_lambda = transition_lambda
        self.observation_lambda = observation_lambda
        self.correct_beats = correct_beats
        self.num_tempi = num_tempi
    
    def detect_downbeats(self, audio_path: str) -> Dict[str, Any]:
        """
        检测音频的 downbeat（小节起点）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            包含以下键的字典:
            - downbeats: downbeat 时间列表（秒）
            - beats: 所有节拍时间列表（秒）
            - beat_info: 原始节拍信息 [(time, type), ...]
            - tempo: 估算的 BPM
        """
        _ensure_madmom_patched()
        
        # 确保 WAV 格式
        wav_path = _ensure_wav_for_madmom(audio_path)
        
        # 使用 RNNDownBeatProcessor 获取激活值
        beat_proc = RNNDownBeatProcessor()
        beat_act = beat_proc(wav_path)
        
        # 使用 DBNDownBeatTrackingProcessor 进行节拍追踪
        beat_tracker = DBNDownBeatTrackingProcessor(
            beats_per_bar=self.beats_per_bar,
            min_bpm=self.min_bpm,
            max_bpm=self.max_bpm,
            num_tempi=self.num_tempi,
            transition_lambda=self.transition_lambda,
            observation_lambda=self.observation_lambda,
            threshold=self.dbn_threshold,
            correct=self.correct_beats,
            fps=self.fps
        )
        beat_info = beat_tracker(beat_act)
        beat_info = np.array(beat_info)
        
        # 分离 downbeat 和普通 beat
        downbeats = []
        all_beats = []
        
        if len(beat_info) > 0:
            # type == 1.0 表示 downbeat（小节起点）
            downbeat_mask = beat_info[:, 1] == 1
            downbeats = beat_info[downbeat_mask][:, 0].tolist()
            # type == 2.0 表示普通 beat
            beat_mask = beat_info[:, 1] == 2
            all_beats = beat_info[beat_mask][:, 0].tolist()
        
        # 估算 tempo
        tempo = self._estimate_tempo(beat_info)
        
        return {
            "downbeats": [float(t) for t in downbeats],
            "beats": [float(t) for t in all_beats],
            "beat_info": beat_info.tolist() if len(beat_info) > 0 else [],
            "tempo": tempo,
            "fps": self.fps,
        }
    
    def _estimate_tempo(self, beat_info: np.ndarray) -> float:
        """从节拍信息估算 BPM"""
        if len(beat_info) < 2:
            return 120.0
        
        # 提取所有 beat 时间（type == 2.0）
        beats = beat_info[beat_info[:, 1] == 2][:, 0]
        
        if len(beats) < 2:
            # 如果没有普通 beat，用所有点
            beats = beat_info[:, 0]
        
        if len(beats) < 2:
            return 120.0
        
        # 计算平均节拍间隔
        intervals = np.diff(beats)
        
        # 过滤异常值
        median_interval = np.median(intervals)
        valid_intervals = intervals[
            (intervals > 0.5 * median_interval) & 
            (intervals < 2.0 * median_interval)
        ]
        
        if len(valid_intervals) == 0:
            return 120.0
        
        avg_interval = np.mean(valid_intervals)
        bpm = 60.0 / avg_interval
        
        return round(float(bpm), 2)
    
    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        完整分析（兼容 VJ 系统格式）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            包含 downbeats, beats, tempo, segments 等的字典
        """
        result = self.detect_downbeats(audio_path)
        
        # 计算音频时长
        import librosa
        try:
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            duration = float(len(y)) / sr
        except Exception:
            # 估算时长
            if result["beat_info"]:
                duration = float(result["beat_info"][-1][0]) if result["beat_info"] else 0.0
            else:
                duration = 0.0
        
        # 构建 segments（基于 downbeats 划分）
        segments = []
        if result["downbeats"]:
            downbeats = result["downbeats"]
            for i in range(len(downbeats) - 1):
                segments.append({
                    "start": round(downbeats[i], 2),
                    "end": round(downbeats[i + 1], 2),
                    "duration": round(downbeats[i + 1] - downbeats[i], 2),
                })
            # 最后一个 segment 到结尾
            if duration > downbeats[-1]:
                segments.append({
                    "start": round(downbeats[-1], 2),
                    "end": round(duration, 2),
                    "duration": round(duration - downbeats[-1], 2),
                })
        
        return {
            "downbeats": result["downbeats"],
            "beats": result["beats"],
            "tempo": result["tempo"],
            "segments": segments,
            "duration": round(duration, 2),
            "beats_per_bar": self.beats_per_bar[0],
            "beat_info": result["beat_info"],
        }
    
    def analyze_to_vj_format(self, audio_path: str) -> Dict[str, Any]:
        """
        分析并返回兼容 VJ 系统 AudioAnalysisResult 格式的数据
        
        Returns:
            包含 beats (BeatInfo 列表), bpm, duration 等字段
        """
        result = self.analyze(audio_path)
        
        # 转换为 BeatInfo 格式
        from src.models.schemas import BeatInfo
        
        beats = []
        
        # 添加 downbeats
        for t in result["downbeats"]:
            beats.append(BeatInfo(
                timestamp=float(t),
                beat_type="downbeat",
                strength=1.0
            ))
        
        # 添加普通 beats
        for t in result["beats"]:
            beats.append(BeatInfo(
                timestamp=float(t),
                beat_type="beat",
                strength=0.7
            ))
        
        # 按时间排序
        beats.sort(key=lambda x: x.timestamp)
        
        return {
            "bpm": result["tempo"],
            "duration": result["duration"],
            "beats": beats,
            "downbeats": result["downbeats"],
            "segments": result["segments"],
        }


def detect_all_keypoints(audio_path: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    多关键点融合检测
    
    融合 downbeat + pitch + energy 三种关键点：
    - downbeat: 小节起点（最佳转场点）
    - pitch: 音调变化
    - energy: 能量突变
    
    Args:
        audio_path: 音频文件路径
        config: 配置字典
        
    Returns:
        包含各类关键点的字典
    """
    _ensure_madmom_patched()
    config = config or {}
    
    # Downbeat 检测
    analyzer = MadmomAnalyzer(
        beats_per_bar=config.get("beats_per_bar", 4),
        min_bpm=config.get("min_bpm", 55.0),
        max_bpm=config.get("max_bpm", 215.0),
    )
    downbeat_result = analyzer.detect_downbeats(audio_path)
    
    # Pitch 检测（使用 aubio）
    try:
        from aubio import source, pitch
        pitches, pitch_confidences, pitch_times = _detect_pitch_aubio(audio_path)
        pitch_keypoints = [
            {
                "time": float(t),
                "type": "pitch",
                "value": float(p),
                "confidence": float(c),
            }
            for p, c, t in zip(pitches, pitch_confidences, pitch_times)
        ]
    except ImportError:
        pitch_keypoints = []
    
    # Energy 检测
    try:
        energy_keypoints = _detect_energy_peaks(audio_path)
    except Exception:
        energy_keypoints = []
    
    return {
        "downbeats": downbeat_result["downbeats"],
        "pitches": pitch_keypoints,
        "energies": energy_keypoints,
        "tempo": downbeat_result["tempo"],
        "beat_info": downbeat_result["beat_info"],
    }


def _detect_pitch_aubio(audio_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """使用 aubio 检测 pitch"""
    from aubio import source, pitch
    
    p = Path(audio_path)
    wav_path = audio_path
    
    if p.suffix.lower() not in {".wav", ".wave"}:
        wav_path = p.with_name(f"{p.stem}__vj_pitch.wav")
        if not wav_path.exists() or wav_path.stat().st_mtime < p.stat().st_mtime:
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                cmd = [ffmpeg, "-y", "-i", str(p), "-vn", "-ac", "1", "-acodec", "pcm_s16le", str(wav_path)]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    win_s = 4096
    hop_s = 512
    
    s = source(str(wav_path), 0, hop_s)
    samplerate = s.samplerate
    
    pitch_o = pitch("yin", win_s, hop_s, samplerate)
    pitch_o.set_unit("midi")
    pitch_o.set_tolerance(0.8)
    
    pitches = []
    confidences = []
    timestamps = []
    total_frames = 0
    
    while True:
        samples, read = s()
        p_val = pitch_o(samples)[0]
        c_val = pitch_o.get_confidence()
        
        timestamps.append(total_frames / float(samplerate))
        pitches.append(p_val)
        confidences.append(c_val)
        
        total_frames += read
        if read < hop_s:
            break
    
    return np.array(pitches), np.array(confidences), np.array(timestamps)


def _detect_energy_peaks(audio_path: str, threshold_ratio: float = 0.3) -> List[Dict[str, Any]]:
    """检测能量突变点"""
    import librosa
    
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    
    # 计算 RMS 能量
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    
    # 找峰值
    max_energy = np.max(rms)
    threshold = max_energy * threshold_ratio
    
    peaks = []
    for i in range(1, len(rms) - 1):
        if rms[i] > threshold and rms[i] > rms[i-1] and rms[i] > rms[i+1]:
            peaks.append({
                "time": round(float(times[i]), 3),
                "energy": round(float(rms[i]), 4),
                "relative": round(float(rms[i] / max_energy), 3),
            })
    
    return peaks


# ============ 便捷函数 ============

def analyze_with_madmom(audio_path: str, **kwargs) -> Dict[str, Any]:
    """
    便捷函数：使用 Madmom 分析音频
    
    Args:
        audio_path: 音频文件路径
        **kwargs: 传递给 MadmomAnalyzer 的参数
        
    Returns:
        分析结果字典
    """
    analyzer = MadmomAnalyzer(**kwargs)
    return analyzer.analyze(audio_path)


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python audio_madmom.py <audio_file>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    print(f"Analyzing: {audio_path}")
    
    analyzer = MadmomAnalyzer()
    result = analyzer.analyze(audio_path)
    
    print(json.dumps(result, indent=2))
