#!/usr/bin/env python3
"""
VJ-Gen 音频分析服务 - 全算法版本
支持: librosa, Essentia, madmom, MFCC, SSM, Spectral
"""

import os
import json
import subprocess
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np

app = Flask(__name__)
CORS(app)

# 库检测
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

try:
    import essentia
    import essentia.standard as es
    HAS_ESSENTIA = True
except ImportError:
    HAS_ESSENTIA = False

MADMOM_PATH = None
if os.path.exists(os.path.expanduser('~/miniconda3/envs/madmom-env/bin/python')):
    MADMOM_PATH = os.path.expanduser('~/miniconda3/envs/madmom-env/bin/python')

SECTION_INFO = {
    'intro': {'name': 'Intro', 'icon': '🚀', 'color': '#607D8B'},
    'verse': {'name': 'Verse', 'icon': '📝', 'color': '#2196F3'},
    'preChorus': {'name': 'Pre-Chorus', 'icon': '📈', 'color': '#03A9F4'},
    'chorus': {'name': 'Chorus', 'icon': '🎉', 'color': '#E91E63'},
    'bridge': {'name': 'Bridge', 'icon': '🌉', 'color': '#FF9800'},
    'outro': {'name': 'Outro', 'icon': '🏁', 'color': '#795548'},
}

def sanitize_value(v):
    """将 NaN 和 Inf 转换为 None"""
    if isinstance(v, float):
        if np.isnan(v) or np.isinf(v):
            return None
    return v

def sanitize_results(results):
    """清理结果中的 NaN 值"""
    cleaned = {}
    for algo, data in results.items():
        if isinstance(data, dict):
            cleaned[algo] = {}
            for k, v in data.items():
                if isinstance(v, list):
                    cleaned[algo][k] = [sanitize_value(item) if not isinstance(item, dict) else {kk: sanitize_value(vv) for kk, vv in item.items()} for item in v]
                else:
                    cleaned[algo][k] = sanitize_value(v)
        else:
            cleaned[algo] = sanitize_value(v)
    return cleaned

def classify_section(pos_ratio, rel_energy):
    """基于位置和能量的段落分类"""
    if pos_ratio < 0.08:
        return 'intro'
    if pos_ratio > 0.92:
        return 'outro'
    if rel_energy > 1.1:
        return 'chorus'
    elif rel_energy < 0.9:
        if 0.4 < pos_ratio < 0.7:
            return 'bridge'
        return 'verse'
    else:
        if pos_ratio < 0.3:
            return 'intro'
        elif pos_ratio > 0.7:
            return 'outro'
        return 'preChorus'

def detect_bpm_librosa(y, sr):
    """librosa BPM检测"""
    tempo1, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120, tightness=100)
    tempo1 = float(tempo1)
    
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tempo2 = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
    tempo2 = float(tempo2)
    
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
    intervals = np.diff(beat_times)
    intervals = intervals[(intervals > 0.2) & (intervals < 2.0)]
    tempo3 = 60.0 / np.median(intervals) if len(intervals) > 0 else tempo1
    
    best_tempo = np.median([tempo1, tempo2, tempo3])
    if best_tempo < 80:
        best_tempo *= 2
    elif best_tempo > 180:
        best_tempo /= 2
    
    return float(round(best_tempo * 2) / 2)

def detect_bpm_madmom(audio_path):
    """madmom BPM检测"""
    if not MADMOM_PATH:
        return None
    
    try:
        script = f"""
import madmom
from madmom.features.beats import RNNBeatProcessor, BeatTrackingProcessor
proc = BeatTrackingProcessor()(RNNBeatProcessor()(audio_file='{audio_path}'))
print(min(proc) if len(proc) > 0 else 120)
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.py', mode='w') as f:
            f.write(script)
            script_path = f.name
        
        result = subprocess.run([MADMOM_PATH, script_path], 
                              capture_output=True, text=True, timeout=30)
        os.unlink(script_path)
        
        if result.returncode == 0:
            bpm = float(result.stdout.strip())
            return round(bpm * 2) / 2
    except:
        pass
    return None

def analyze_librosa(y, sr, duration):
    """librosa段落检测"""
    tempo = detect_bpm_librosa(y, sr)
    beat_duration = 60 / tempo
    bar_duration = beat_duration * 4
    
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    
    bars = []
    current_time = 0
    while current_time < duration:
        bars.append({'start': current_time, 'end': min(current_time + bar_duration, duration)})
        current_time += bar_duration
    
    energy_per_bar = []
    for bar in bars:
        start_frame = int(bar['start'] * sr / 512)
        end_frame = min(int(bar['end'] * sr / 512), len(rms))
        if start_frame < len(rms):
            energy_per_bar.append(float(np.mean(rms[start_frame:end_frame])))
        else:
            energy_per_bar.append(0)
    
    if not energy_per_bar:
        return tempo, []
    
    median_energy = np.median(energy_per_bar)
    
    # 平滑
    window = 3
    energy_smooth = []
    for i in range(len(energy_per_bar)):
        start = max(0, i - window // 2)
        end = min(len(energy_per_bar), i + window // 2 + 1)
        energy_smooth.append(np.mean(energy_per_bar[start:end]))
    
    # 合并段落
    sections = []
    current = {'bars': [], 'energy': []}
    
    for i, bar in enumerate(bars):
        current['bars'].append(bar)
        current['energy'].append(energy_smooth[i])
        
        should_split = False
        if len(current['energy']) >= 2:
            prev_avg = np.mean(current['energy'][:-1])
            curr = energy_smooth[i]
            if prev_avg > 0:
                ratio = curr / prev_avg
                if ratio < 0.75 or ratio > 1.35:
                    should_split = True
        
        if len(current['bars']) >= 8:
            should_split = True
        
        if i == len(bars) - 1:
            should_split = True
        
        if should_split and current['bars']:
            avg_e = np.mean(current['energy'])
            rel_e = avg_e / median_energy if median_energy > 0 else 1
            pos_ratio = current['bars'][0]['start'] / duration
            sec_type = classify_section(pos_ratio, rel_e)
            
            sections.append({
                'start': current['bars'][0]['start'],
                'end': current['bars'][-1]['end'],
                'type': sec_type,
                'name': SECTION_INFO[sec_type]['name'],
                'bars': len(current['bars']),
                'energy': round(avg_e, 4)
            })
            current = {'bars': [], 'energy': []}
    
    return tempo, sections

def analyze_essentia(audio_path, duration):
    """Essentia段落检测"""
    if not HAS_ESSENTIA:
        return None, []
    
    try:
        # 加载音频
        loader = es.MonoLoader(filename=audio_path, sampleRate=44100)
        y = loader()
        
        if len(y) == 0:
            return None, []
        
        # 节拍检测
        rhythm_extractor = es.RhythmExtractor2013()
        rhythm = rhythm_extractor(y)
        
        # 处理不同的返回格式
        if isinstance(rhythm, (list, tuple, np.ndarray)) and len(rhythm) >= 2:
            bpm = float(rhythm[0])
        else:
            bpm = float(rhythm)
        
        if bpm < 80:
            bpm *= 2
        elif bpm > 180:
            bpm /= 2
        bpm = round(bpm * 2) / 2
        
        # 简单段落：基于能量变化
        beat_duration = 60 / max(bpm, 60)
        bar_duration = beat_duration * 4
        
        # 使用 RMS 计算能量
        fc = es.FrameCutter(frameSize=2048, hopSize=512)
        w = es.Windowing(type='hann')
        spec = es.Spectrum()
        rms_calc = es.RMS()
        
        rms_values = []
        hop = 512
        for i in range(0, len(y) - 2048, hop):
            frame = y[i:i+2048].astype('float32')
            w_frame = w(frame)
            s = spec(w_frame)
            r = rms_calc(s)
            rms_values.append(float(r))
        
        rms = np.array(rms_values)
        
        bars = []
        current_time = 0
        while current_time < duration:
            bars.append({'start': current_time, 'end': min(current_time + bar_duration, duration)})
            current_time += bar_duration
        
        energy_per_bar = []
        for bar in bars:
            start_frame = int(bar['start'] * 44100 / 512)
            end_frame = min(int(bar['end'] * 44100 / 512), len(rms))
            if start_frame < len(rms):
                energy_per_bar.append(float(np.mean(rms[start_frame:end_frame])))
            else:
                energy_per_bar.append(0)
        
        if not energy_per_bar:
            return bpm, []
        
        median_energy = np.median(energy_per_bar)
        
        # 平滑
        window = 3
        energy_smooth = []
        for i in range(len(energy_per_bar)):
            start = max(0, i - window // 2)
            end = min(len(energy_per_bar), i + window // 2 + 1)
            energy_smooth.append(np.mean(energy_per_bar[start:end]))
        
        # 合并段落
        sections = []
        current = {'bars': [], 'energy': []}
        
        for i, bar in enumerate(bars):
            current['bars'].append(bar)
            current['energy'].append(energy_smooth[i])
            
            should_split = False
            if len(current['energy']) >= 2:
                prev_avg = np.mean(current['energy'][:-1])
                curr = energy_smooth[i]
                if prev_avg > 0:
                    ratio = curr / prev_avg
                    if ratio < 0.75 or ratio > 1.35:
                        should_split = True
            
            if len(current['bars']) >= 8:
                should_split = True
            
            if i == len(bars) - 1:
                should_split = True
            
            if should_split and current['bars']:
                avg_e = np.mean(current['energy'])
                rel_e = avg_e / median_energy if median_energy > 0 else 1
                pos_ratio = current['bars'][0]['start'] / duration
                sec_type = classify_section(pos_ratio, rel_e)
                
                sections.append({
                    'start': current['bars'][0]['start'],
                    'end': current['bars'][-1]['end'],
                    'type': sec_type,
                    'name': SECTION_INFO[sec_type]['name'],
                    'bars': len(current['bars']),
                    'energy': round(avg_e, 4)
                })
                current = {'bars': [], 'energy': []}
        
        return bpm, sections
        
    except Exception as e:
        print(f"Essentia error: {e}")
        return None, []

def analyze_madmom(audio_path, duration):
    """madmom段落检测"""
    if not MADMOM_PATH:
        return None, []
    
    bpm = None
    
    try:
        # madmom BPM - 使用更稳定的方法
        script = '''
import sys
import madmom
from madmom.features.beats import RNNBeatProcessor, BeatTrackingProcessor
from madmom.features.tempo import TempoEstimationProcessor

audio_file = sys.argv[1]
beats = BeatTrackingProcessor()(RNNBeatProcessor()(audio_file=audio_file))
tempo = TempoEstimationProcessor()(beats)
if len(tempo) > 0:
    bpm = float(tempo[0][0])
    if bpm < 80:
        bpm *= 2
    elif bpm > 180:
        bpm /= 2
    bpm = round(bpm * 2) / 2
    print(bpm)
else:
    print("ERROR")
'''
        with tempfile.NamedTemporaryFile(delete=False, suffix='.py', mode='w') as f:
            f.write(script)
            script_path = f.name
        
        # 使用列表传递参数避免shell转义问题
        result = subprocess.run(
            [MADMOM_PATH, script_path, audio_path],
            capture_output=True, text=True, timeout=120
        )
        os.unlink(script_path)
        
        if result.returncode == 0 and result.stdout.strip() and not result.stdout.startswith('ERROR'):
            bpm = float(result.stdout.strip())
        else:
            # Fallback: 使用librosa的BPM
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            bpm = detect_bpm_librosa(y, sr)
            
    except Exception as e:
        print(f"madmom error: {e}")
        # Fallback
        try:
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            bpm = detect_bpm_librosa(y, sr)
        except:
            return None, []
    
    if bpm is None:
        return None, []
    
    try:
        beat_duration = 60 / max(bpm, 60)
        bar_duration = beat_duration * 4
        
        # 使用librosa计算能量
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        
        bars = []
        current_time = 0
        while current_time < duration:
            bars.append({'start': current_time, 'end': min(current_time + bar_duration, duration)})
            current_time += bar_duration
        
        energy_per_bar = []
        for bar in bars:
            start_frame = int(bar['start'] * sr / 512)
            end_frame = min(int(bar['end'] * sr / 512), len(rms))
            if start_frame < len(rms):
                energy_per_bar.append(float(np.mean(rms[start_frame:end_frame])))
            else:
                energy_per_bar.append(0)
        
        if not energy_per_bar:
            return bpm, []
        
        median_energy = np.median(energy_per_bar)
        
        # 平滑
        window = 3
        energy_smooth = []
        for i in range(len(energy_per_bar)):
            start = max(0, i - window // 2)
            end = min(len(energy_per_bar), i + window // 2 + 1)
            energy_smooth.append(np.mean(energy_per_bar[start:end]))
        
        # 合并段落
        sections = []
        current = {'bars': [], 'energy': []}
        
        for i, bar in enumerate(bars):
            current['bars'].append(bar)
            current['energy'].append(energy_smooth[i])
            
            should_split = False
            if len(current['energy']) >= 2:
                prev_avg = np.mean(current['energy'][:-1])
                curr = energy_smooth[i]
                if prev_avg > 0:
                    ratio = curr / prev_avg
                    if ratio < 0.75 or ratio > 1.35:
                        should_split = True
            
            if len(current['bars']) >= 8:
                should_split = True
            
            if i == len(bars) - 1:
                should_split = True
            
            if should_split and current['bars']:
                avg_e = np.mean(current['energy'])
                rel_e = avg_e / median_energy if median_energy > 0 else 1
                pos_ratio = current['bars'][0]['start'] / duration
                sec_type = classify_section(pos_ratio, rel_e)
                
                sections.append({
                    'start': current['bars'][0]['start'],
                    'end': current['bars'][-1]['end'],
                    'type': sec_type,
                    'name': SECTION_INFO[sec_type]['name'],
                    'bars': len(current['bars']),
                    'energy': round(avg_e, 4)
                })
                current = {'bars': [], 'energy': []}
        
        return bpm, sections
        
    except Exception as e:
        print(f"madmom section error: {e}")
        return bpm if bpm else None, []

def analyze_mfcc(y, sr, duration):
    """MFCC段落检测"""
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=512)
    
    segment_duration = 4.0
    hop_duration = 512 / sr
    n_segments = int(duration / segment_duration) + 1
    
    segments = []
    for i in range(n_segments):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, duration)
        
        start_frame = int(start_time / hop_duration)
        end_frame = int(end_time / hop_duration)
        
        if start_frame < mfccs.shape[1]:
            segment_mfcc = mfccs[:, start_frame:min(end_frame, mfccs.shape[1])]
            if segment_mfcc.size > 0:
                features = np.mean(segment_mfcc, axis=1)
                energy = float(np.mean(np.abs(segment_mfcc)))
            else:
                features = np.zeros(13)
                energy = 0
        else:
            features = np.zeros(13)
            energy = 0
        
        segments.append({
            'start': start_time,
            'end': end_time,
            'features': features.tolist(),
            'energy': energy
        })
    
    max_energy = max([s['energy'] for s in segments]) if segments else 1
    for s in segments:
        s['energy'] = s['energy'] / max_energy if max_energy > 0 else 0
    
    sections = []
    current = {'start': 0, 'energy': 0, 'count': 0}
    
    for i, seg in enumerate(segments):
        if current['count'] == 0:
            current['start'] = seg['start']
        
        current['energy'] = (current['energy'] * current['count'] + seg['energy']) / (current['count'] + 1)
        current['count'] += 1
        
        should_split = (current['count'] >= 2 and seg['end'] - current['start'] >= 8)
        
        if should_split or i == len(segments) - 1:
            avg_e = current['energy']
            pos_ratio = current['start'] / duration if duration > 0 else 0
            sec_type = classify_section(pos_ratio, avg_e)
            
            sections.append({
                'start': current['start'],
                'end': seg['end'],
                'type': sec_type,
                'name': SECTION_INFO[sec_type]['name'],
                'bars': int((seg['end'] - current['start']) / 4),
                'energy': round(avg_e, 4)
            })
            
            current = {'start': seg['end'], 'energy': 0, 'count': 0}
    
    return None, sections

def analyze_ssm(y, sr, duration):
    """SSM段落检测 - 基于自相似矩阵的结构分析"""
    hop_length = 512
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=hop_length, n_mels=64)
    log_mel = librosa.power_to_db(mel, ref=np.max)
    
    n_frames = log_mel.shape[1]
    frame_duration = hop_length / sr
    
    # 使用MFCC特征进行更稳定的段落检测
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, hop_length=hop_length)
    
    # 分段：每4秒一段
    segment_duration = 4.0
    n_segments = int(duration / segment_duration) + 1
    
    segments = []
    for i in range(n_segments):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, duration)
        
        start_frame = int(start_time / frame_duration)
        end_frame = int(end_time / frame_duration)
        
        if start_frame < mfccs.shape[1]:
            seg_mfcc = mfccs[:, start_frame:min(end_frame, mfccs.shape[1])]
            if seg_mfcc.size > 0:
                feat = np.mean(seg_mfcc, axis=1)
            else:
                feat = np.zeros(20)
        else:
            feat = np.zeros(20)
        
        # 计算该段的频谱质心作为额外特征
        if start_frame < log_mel.shape[1]:
            seg_mel = log_mel[:, start_frame:min(end_frame, log_mel.shape[1])]
            spectral = float(np.mean(seg_mel))
        else:
            spectral = 0
        
        segments.append({
            'start': start_time,
            'end': end_time,
            'feat': feat,
            'spectral': spectral
        })
    
    # 计算段落间的相似度
    n = len(segments)
    similarity = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            # 余弦相似度
            f1, f2 = segments[i]['feat'], segments[j]['feat']
            norm1, norm2 = np.linalg.norm(f1), np.linalg.norm(f2)
            if norm1 > 0 and norm2 > 0:
                similarity[i, j] = np.dot(f1, f2) / (norm1 * norm2)
    
    # 对角线路径增强 (相似的段落会在对角线附近)
    for offset in range(-2, 3):
        for i in range(n):
            j = i + offset
            if 0 <= j < n:
                similarity[i, j] *= 1.2
    
    # 计算每行的平均相似度 (与自身的相似度)
    self_similarity = np.diag(similarity).copy()
    
    # 找变化点：局部最小值 (与周围相比不相似)
    changes = []
    for i in range(1, n - 1):
        local_min = True
        for j in range(max(0, i-2), min(n, i+3)):
            if j != i and self_similarity[i] > self_similarity[j]:
                local_min = False
                break
        if local_min and i > 0:
            changes.append(i)
    
    # 如果变化点太少，使用能量变化作为补充
    if len(changes) < 3:
        spectral_vals = np.array([s['spectral'] for s in segments])
        spectral_norm = (spectral_vals - spectral_vals.min()) / (spectral_vals.max() - spectral_vals.min() + 1e-10)
        
        # 滑动窗口平滑
        kernel_size = 3
        kernel = np.ones(kernel_size) / kernel_size
        spectral_smooth = np.convolve(spectral_norm, kernel, mode='same')
        
        for i in range(1, n):
            if abs(spectral_smooth[i] - spectral_smooth[i-1]) > 0.2:
                if i not in changes:
                    changes.append(i)
        changes = sorted(set(changes))
    
    # 构建段落
    sections = []
    prev_idx = 0
    
    for idx in changes + [n]:
        if idx > prev_idx:
            start_time = segments[prev_idx]['start']
            end_time = segments[min(idx, n-1)]['end']
            
            # 计算该段的平均特征
            avg_spectral = np.mean([segments[i]['spectral'] for i in range(prev_idx, min(idx, n))])
            avg_spectral_norm = (avg_spectral - min(s['spectral'] for s in segments)) / (max(s['spectral'] for s in segments) - min(s['spectral'] for s in segments) + 1e-10)
            
            pos_ratio = start_time / duration if duration > 0 else 0
            sec_type = classify_section(pos_ratio, avg_spectral_norm)
            
            sections.append({
                'start': start_time,
                'end': end_time,
                'type': sec_type,
                'name': SECTION_INFO[sec_type]['name'],
                'bars': int((end_time - start_time) / 4),
                'energy': round(float(avg_spectral_norm), 4)
            })
            
            prev_idx = idx
    
    return None, sections if sections else [{'start': 0, 'end': duration, 'type': 'verse', 'name': 'Verse', 'bars': int(duration/4), 'energy': 0.5}]

def analyze_spectral(y, sr, duration):
    """Spectral段落检测"""
    hop_length = 512
    
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    
    sc = (spectral_centroid - spectral_centroid.min()) / (spectral_centroid.max() - spectral_centroid.min() + 1e-10)
    sb = (spectral_bandwidth - spectral_bandwidth.min()) / (spectral_bandwidth.max() - spectral_bandwidth.min() + 1e-10)
    sr_norm = (spectral_rolloff - spectral_rolloff.min()) / (spectral_rolloff.max() - spectral_rolloff.min() + 1e-10)
    zcr_norm = (zcr - zcr.min()) / (zcr.max() - zcr.min() + 1e-10)
    
    features = (sc + sb + sr_norm + zcr_norm) / 4
    
    kernel_size = 7
    kernel = np.ones(kernel_size) / kernel_size
    features_smooth = np.convolve(features, kernel, mode='same')
    
    segment_duration = 4.0
    n_segments = int(duration / segment_duration) + 1
    
    sections = []
    for i in range(n_segments):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, duration)
        
        start_frame = int(start_time * sr / hop_length)
        end_frame = int(end_time * sr / hop_length)
        
        if start_frame < len(features_smooth):
            avg_feat = float(np.mean(features_smooth[start_frame:min(end_frame, len(features_smooth))]))
        else:
            avg_feat = 0.5
        
        pos_ratio = start_time / duration if duration > 0 else 0
        sec_type = classify_section(pos_ratio, avg_feat)
        
        sections.append({
            'start': start_time,
            'end': end_time,
            'type': sec_type,
            'name': SECTION_INFO[sec_type]['name'],
            'bars': int((end_time - start_time) / 4),
            'energy': round(avg_feat, 4)
        })
    
    return None, sections

@app.route('/analyze-all', methods=['POST'])
def analyze_all():
    """分析所有算法"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    filename = file.filename or 'audio.mp3'
    audio_data = file.read()
    
    # 保存临时文件
    suffix = os.path.splitext(filename)[1] if '.' in filename else '.mp3'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(audio_data)
        temp_path = f.name
    
    try:
        # librosa
        y, sr = librosa.load(temp_path, sr=22050, mono=True)
        duration = len(y) / sr
        
        results = {
            'librosa': {'success': True, 'method': 'librosa'},
            'essentia': {'success': HAS_ESSENTIA, 'method': 'essentia'},
            'madmom': {'success': MADMOM_PATH is not None, 'method': 'madmom'},
            'mfcc': {'success': True, 'method': 'mfcc'},
            'ssm': {'success': True, 'method': 'ssm'},
            'spectral': {'success': True, 'method': 'spectral'},
        }
        
        # librosa
        bpm, sections = analyze_librosa(y, sr, duration)
        results['librosa']['bpm'] = bpm
        results['librosa']['sections'] = sections
        results['librosa']['duration'] = duration
        
        # essentia
        if HAS_ESSENTIA:
            bpm_e, sections_e = analyze_essentia(temp_path, duration)
            if bpm_e:
                results['essentia']['bpm'] = bpm_e
                results['essentia']['sections'] = sections_e
            else:
                results['essentia']['success'] = False
        else:
            results['essentia']['error'] = 'not installed'
        
        # madmom
        if MADMOM_PATH:
            bpm_m, sections_m = analyze_madmom(temp_path, duration)
            if bpm_m:
                results['madmom']['bpm'] = bpm_m
                results['madmom']['sections'] = sections_m
            else:
                results['madmom']['success'] = False
        else:
            results['madmom']['error'] = 'conda not available'
        
        # mfcc
        _, sections_mfcc = analyze_mfcc(y, sr, duration)
        results['mfcc']['sections'] = sections_mfcc
        
        # ssm
        _, sections_ssm = analyze_ssm(y, sr, duration)
        results['ssm']['sections'] = sections_ssm
        
        # spectral
        _, sections_spec = analyze_spectral(y, sr, duration)
        results['spectral']['sections'] = sections_spec
        
        # 清理 NaN 值
        results = sanitize_results(results)
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(temp_path)

@app.route('/analyze', methods=['POST'])
def analyze():
    """librosa分析"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    audio_data = file.read()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as f:
        f.write(audio_data)
        temp_path = f.name
    
    try:
        y, sr = librosa.load(temp_path, sr=22050, mono=True)
        duration = len(y) / sr
        bpm, sections = analyze_librosa(y, sr, duration)
        
        return jsonify({
            'success': True,
            'bpm': bpm,
            'duration': duration,
            'sections': sections
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(temp_path)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'librosa': HAS_LIBROSA,
        'essentia': HAS_ESSENTIA,
        'madmom': MADMOM_PATH is not None
    })

if __name__ == '__main__':
    print("🎵 VJ-Gen Audio Analysis Server (全算法版)")
    print("=" * 50)
    print(f"librosa:  {'✅' if HAS_LIBROSA else '❌'}")
    print(f"Essentia: {'✅' if HAS_ESSENTIA else '❌'}")
    print(f"madmom:   {'✅' if MADMOM_PATH else '❌'}")
    print("\nEndpoints:")
    print("  /analyze-all - 所有算法")
    print("  /analyze     - librosa")
    print("Server: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
