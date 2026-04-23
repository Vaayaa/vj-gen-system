#!/usr/bin/env python3
"""VJ Audio Analysis Module v5 - 5大函数"""
import numpy as np
import librosa
import warnings
warnings.filterwarnings("ignore")
from typing import Dict, Any, List

PITCH = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MAJ = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
MIN = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])

# BPM 校正参数
BPM_MIN = 60.0
BPM_MAX = 200.0
BPM_MEDIAN_FILTER_SIZE = 5
BPM_OUTLIER_THRESHOLD = 0.20  # 偏离中位数 >20% 则剔除


def _validate_bpm(bpm: float) -> float:
    """将 BPM 钳制到合理范围，并处理 librosa 2x/0.5x 误检测"""
    if bpm <= 0:
        return 120.0
    # 处理 librosa 可能检测到 2x 或 0.5x 的情况
    if bpm > BPM_MAX * 1.5:
        bpm = bpm / 2.0
    elif bpm > BPM_MAX:
        bpm = BPM_MAX
    if bpm < BPM_MIN:
        bpm = bpm * 2.0
    if bpm < BPM_MIN:
        bpm = BPM_MIN
    if bpm > BPM_MAX:
        bpm = BPM_MAX
    return round(bpm, 2)


def _multi_frame_bpm(audio_path: str) -> float:
    """多帧平均 BPM：分段检测后取中位数，避免单帧突变"""
    y, sr = librosa.load(audio_path, sr=22050, mono=True)

    # 分 3 段检测（跳过前后静音区），取中位数
    segment_ratios = [
        (0.10, 0.40),
        (0.30, 0.70),
        (0.60, 0.95),
    ]
    bpm_candidates: List[float] = []

    for s_ratio, e_ratio in segment_ratios:
        s_sample = int(s_ratio * len(y))
        e_sample = int(e_ratio * len(y))
        if e_sample <= s_sample:
            continue
        seg_y = y[s_sample:e_sample]
        try:
            onset_env = librosa.onset.onset_strength(y=seg_y, sr=sr, hop_length=512)
            seg_tempo = float(librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0])
            seg_tempo = _validate_bpm(seg_tempo)
            bpm_candidates.append(seg_tempo)
        except Exception:
            pass

    if not bpm_candidates:
        return 120.0

    median_bpm = float(np.median(bpm_candidates))
    # 剔除偏离中位数 >20% 的异常帧
    valid = [b for b in bpm_candidates if abs(b - median_bpm) / (median_bpm + 1e-10) <= BPM_OUTLIER_THRESHOLD]
    if not valid:
        return round(median_bpm, 2)
    return round(float(np.median(valid)), 2)


def analyze_beats(path: str) -> Dict[str, Any]:
    y, sr = librosa.load(path, sr=22050)
    o = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)

    # 多帧平均 BPM（避免单帧突变）
    t = _multi_frame_bpm(path)

    _, bf = librosa.beat.beat_track(onset_envelope=o, sr=sr, start_bpm=t, tightness=100, trim=True, units="frames")
    bt = librosa.frames_to_time(bf, sr=sr, hop_length=512)
    iv = np.diff(bt) if len(bt) > 1 else np.array([0.5])
    mi = np.median(iv)
    # 异常值剔除：与中位数偏差 >20% 则不用（从 0.5x~2x 收紧到 0.8x~1.2x）
    v = iv[(iv > (1 - BPM_OUTLIER_THRESHOLD) * mi) & (iv < (1 + BPM_OUTLIER_THRESHOLD) * mi)]
    c = float(1 - min(1.0, max(0.0, np.std(v) / (mi + 1e-10)))) if len(v) > 0 else 0.0

    # BPM 范围钳制（双重保护）
    t = _validate_bpm(t)

    return {"bpm": round(t, 2), "beats": [round(float(x), 4) for x in bt],
            "n": len(bt), "conf": round(c, 3), "dur": round(float(len(y)) / sr, 1)}


def analyze_segments(path: str, k: int = 6, min_dur: float = 3.0) -> Dict[str, Any]:
    y, sr = librosa.load(path, sr=22050)
    dur = round(float(len(y)) / sr, 1)
    t, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=120)
    t = float(t)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    rm_mean = float(np.mean(rms))
    rm_std = float(np.std(rms))
    n_win = max(2, int(dur / min_dur))
    win_samples = len(y) // n_win
    rms_wins = []
    for i in range(n_win):
        s = i * win_samples
        e = min((i + 1) * win_samples, len(y))
        seg_rms = librosa.feature.rms(y=y[s:e], hop_length=512)[0]
        rms_wins.append(float(np.mean(seg_rms)))
    rms_wins = np.array(rms_wins)
    time_per_win = dur / n_win
    thresh = max(0.25 * rm_mean, rm_std * 0.5)
    pts = [0.0]
    for i in range(1, n_win - 1):
        d1 = abs(rms_wins[i] - rms_wins[i - 1])
        d2 = abs(rms_wins[i] - rms_wins[i + 1])
        if d1 > thresh or d2 > thresh:
            pt = round(time_per_win * i, 2)
            if not any(abs(pt - p) < min_dur * 0.8 for p in pts):
                pts.append(pt)
    pts.append(dur)
    pts = sorted(set(pts))
    rms_var = float(np.std(rms_wins)) / (rm_mean + 1e-10)
    if len(pts) <= 2 or rms_var < 0.02:
        pts = [round(x, 2) for x in np.linspace(0, dur, k + 1)]
    bd = [0.0]
    for pt in pts[1:-1]:
        if pt - bd[-1] >= min_dur:
            bd.append(round(pt, 2))
    bd.append(dur)
    bd = sorted(set(bd))
    if len(bd) < 3:
        mid = round(dur / 2, 2)
        bd = [0.0, mid, dur]
    segs = [{"s": round(bd[j], 2), "e": round(bd[j + 1], 2), "d": round(bd[j + 1] - bd[j], 2)} for j in range(len(bd) - 1)]
    conf_val = round(min(1.0, len(segs) / float(max(k, 1))), 3)
    return {"k": len(segs), "bd": bd, "segs": segs, "bpm": round(t, 2), "dur": dur,
            "conf": conf_val, "rms_var": round(rms_var, 4)}


def analyze_key(path: str) -> Dict[str, Any]:
    y, sr = librosa.load(path, sr=22050)
    dur = round(float(len(y)) / sr, 1)
    cc = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    cm = np.mean(cc, axis=1)
    scores = {}
    for s in range(12):
        cs = np.roll(cm, s)
        mc = np.corrcoef(cs, MAJ)[0, 1]
        nc = np.corrcoef(cs, MIN)[0, 1]
        kn = PITCH[s]
        scores[kn + "_M"] = float(mc) if not np.isnan(mc) else -1.0
        scores[kn + "_m"] = float(nc) if not np.isnan(nc) else -1.0
    best = max(scores.items(), key=lambda x: x[1])
    kn, mo = best[0].rsplit("_", 1)
    mo_cn = {"M": "大调", "m": "小调"}.get(mo, mo)
    vals = list(scores.values())
    rng = max(vals) - min(vals) + 1e-10
    conf = float(max(0.0, min(1.0, (best[1] - min(vals)) / rng * 0.5 + 0.5)))
    hints = []
    pent = [0, 2, 4, 7, 9]
    pe = sum(cm[i] for i in pent if i < 12) / sum(cm)
    if pe > 0.6:
        hints.append({"t": "pentatonic", "s": float(pe), "d": "五声音阶"})
    top_scores = sorted(scores.items(), key=lambda x: -x[1])[:12]
    return {"key": kn, "mode": mo, "name": kn + mo_cn, "conf": round(conf, 3), "dur": dur,
            "non_tet": hints, "all_scores": {k2: round(v, 3) for k2, v in top_scores}}


def analyze_energy(path: str, res: float = 0.5) -> Dict[str, Any]:
    y, sr = librosa.load(path, sr=22050)
    dur = float(len(y)) / sr
    h = int(res * sr)
    rms = librosa.feature.rms(y=y, hop_length=h)[0]
    sc = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=h)[0]
    frames = np.arange(len(rms))
    rt = [round(float(x), 2) for x in librosa.frames_to_time(frames, sr=sr, hop_length=h)]
    ns = 10
    sl = max(1, len(rms) // ns)
    segs = []
    for i in range(ns):
        s, e = i * sl, (i + 1) * sl
        if e > s and s < len(rms) and e <= len(rms):
            e2 = min(e, len(rt) - 1)
            segs.append({"s": round(float(rt[s]), 1), "e": round(float(rt[e2]), 1),
                         "r": round(float(np.mean(rms[s:e])), 4)})
    pk_times = librosa.onset.onset_detect(y=y, sr=sr, hop_length=h)
    pk = [round(float(x), 2) for x in librosa.frames_to_time(pk_times, sr=sr, hop_length=h)[:20]]
    # 用percentile替代min/max，避免静音段的异常值（修复187dB问题）
    rms_lo = float(np.percentile(rms, 5))
    rms_hi = float(np.percentile(rms, 95))
    dyn = float(20 * np.log10(max(rms_hi, 1e-10)) - 20 * np.log10(max(rms_lo, 1e-10)))
    return {"t": rt, "rms": [round(float(x), 4) for x in rms],
            "sc_m": round(float(np.mean(sc)), 1), "dyn": round(dyn, 1),
            "segs": segs, "pk": pk, "dur": round(dur, 1), "res": res}


def analyze_emotion(path: str) -> Dict[str, Any]:
    y, sr = librosa.load(path, sr=22050)
    dur = float(len(y)) / sr
    rms = librosa.feature.rms(y=y)[0]
    sc = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    mf = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mf_m = np.mean(mf, axis=1)
    t, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=120)
    t = float(t)
    third = max(1, len(rms) // 3)
    lfe = float(np.mean(rms[:third]))
    hfe = float(np.mean(rms[-third:])) if len(rms) >= third else lfe
    v_val = max(0.0, min(1.0, 0.3 + 0.4 * (hfe / (lfe + 1e-10))))
    sn = min(1.0, max(0.0, float(np.mean(sc) / 4000.0)))
    a_val = min(1.0, 0.4 * sn + 0.6 * min(1.0, t / 120.0))
    e_val = min(1.0, float(np.mean(rms) * 10.0))
    ts = min(1.0, float(t / 180.0))
    if v_val > 0.5 or a_val > 0.55:
        em = "Exciting"
    elif v_val > 0.55 and a_val < 0.45:
        em = "Happy"
    elif v_val < 0.45 and a_val > 0.55:
        em = "Angry"
    elif v_val < 0.45 and a_val < 0.45:
        em = "Sad"
    elif 0.45 <= v_val <= 0.55 and a_val > 0.55:
        em = "Tense"
    else:
        em = "Calm"
    lbl = {"Happy": "快乐", "Sad": "悲伤", "Angry": "愤怒", "Calm": "平静",
           "Exciting": "兴奋", "Tense": "紧张", "Neutral": "中性"}
    gh = []
    if t > 115:
        gh.append("电子/舞曲")
    elif t < 80:
        gh.append("慢歌/民谣")
    if float(np.mean(sc)) > 3000:
        gh.append("明亮")
    else:
        gh.append("低沉")
    if float(np.mean(zcr)) > 0.15:
        gh.append("节奏感强")
    return {"v": round(v_val, 3), "a": round(a_val, 3), "e": round(e_val, 3),
            "ts": round(ts, 3), "t": round(t, 1),
            "em": em, "em_cn": lbl.get(em, em), "genre": gh,
            "sc_m": round(float(np.mean(sc)), 1),
            "mfcc_m": [round(float(x), 2) for x in mf_m.tolist()],
            "dur": round(dur, 1)}


def analyze_beats_madmom(path: str, beats_per_bar: int = 4) -> Dict[str, Any]:
    """
    使用 Madmom 进行专业的节拍和 downbeat 检测
    
    这是 librosa.analyze_beats 的高级替代方案，特点：
    - 使用深度学习模型（RNN）进行节拍检测
    - 准确的 downbeat（小节起点）检测
    - 融合 DBN 进行时序约束
    
    Args:
        path: 音频文件路径
        beats_per_bar: 每小节拍数 (默认 4)
        
    Returns:
        包含 downbeats, beats, tempo 等字段的字典
    """
    # 延迟导入，避免循环依赖
    try:
        from audio_madmom import MadmomAnalyzer
    except ImportError:
        return {"error": "audio_madmom module not available", "downbeats": [], "beats": [], "tempo": 0}
    
    try:
        analyzer = MadmomAnalyzer(beats_per_bar=beats_per_bar)
        result = analyzer.analyze(path)
        
        return {
            "bpm": result.get("tempo", 120),
            "downbeats": result.get("downbeats", []),
            "beats": result.get("beats", []),
            "segments": result.get("segments", []),
            "duration": result.get("duration", 0),
            "beats_per_bar": beats_per_bar,
            "beat_info": result.get("beat_info", []),
            # 兼容原有格式
            "n_downbeats": len(result.get("downbeats", [])),
            "n_beats": len(result.get("beats", [])),
        }
    except Exception as ex:
        return {"error": str(ex)[:100], "downbeats": [], "beats": [], "tempo": 0}


def full_analysis(path: str) -> Dict[str, Any]:
    r = {}
    for fn, key in [
        (analyze_beats, "beat"), (analyze_segments, "seg"),
        (analyze_key, "key"), (analyze_energy, "energy"), (analyze_emotion, "emotion"),
    ]:
        try:
            r[key] = fn(path)
        except Exception as ex:
            r[key] = {"error": str(ex)[:100]}
    return r


def full_analysis_with_madmom(path: str, beats_per_bar: int = 4) -> Dict[str, Any]:
    """
    完整音频分析（包含 Madmom downbeat 检测）
    
    在原有 5 大函数基础上增加 Madmom 专业的节拍/downbeat 检测。
    
    Args:
        path: 音频文件路径
        beats_per_bar: 每小节拍数 (默认 4)
        
    Returns:
        包含所有分析结果的字典
    """
    r = full_analysis(path)
    
    # 添加 Madmom 分析
    madmom_result = analyze_beats_madmom(path, beats_per_bar)
    r["madmom"] = madmom_result
    
    # 如果 Madmom 检测到了节拍，用它替换原有的节拍信息
    if madmom_result.get("downbeats") and not madmom_result.get("error"):
        # 更新节拍 BPM
        if r.get("beat") and not r["beat"].get("error"):
            r["beat"]["bpm_madmom"] = madmom_result["bpm"]
            r["beat"]["downbeats"] = madmom_result["downbeats"]
            r["beat"]["beats_per_bar"] = beats_per_bar
    
    return r


def full_analysis_all_keypoints(path: str) -> Dict[str, Any]:
    """
    完整音频分析，包含所有关键点（downbeat + pitch + energy）
    
    Returns:
        包含多模态关键点融合结果的字典
    """
    # 延迟导入
    try:
        from audio_madmom import detect_all_keypoints
    except ImportError:
        return {"error": "audio_madmom module not available"}
    
    try:
        result = full_analysis_with_madmom(path)
        
        # 添加多关键点融合
        keypoints = detect_all_keypoints(path)
        result["keypoints"] = {
            "downbeats": keypoints.get("downbeats", []),
            "pitches": keypoints.get("pitches", []),
            "energies": keypoints.get("energies", []),
            "tempo": keypoints.get("tempo", 0),
        }
        
        return result
    except Exception as ex:
        return {"error": str(ex)[:100]}


if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_beat_120bpm.wav"
    print(json.dumps(full_analysis(path), ensure_ascii=False, indent=2))
