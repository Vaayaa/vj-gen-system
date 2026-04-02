#!/usr/bin/env python3
"""
VJ-Gen 音频分析服务 - 优化版
使用librosa实现专业级BPM检测
"""

import os
import json
import base64
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np

app = Flask(__name__)
CORS(app)

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

SECTION_INFO = {
    'intro': {'name': 'Intro', 'icon': '🚀', 'color': '#607D8B'},
    'verse': {'name': 'Verse', 'icon': '📝', 'color': '#2196F3'},
    'preChorus': {'name': 'Pre-Chorus', 'icon': '📈', 'color': '#03A9F4'},
    'chorus': {'name': 'Chorus', 'icon': '🎉', 'color': '#E91E63'},
    'bridge': {'name': 'Bridge', 'icon': '🌉', 'color': '#FF9800'},
    'outro': {'name': 'Outro', 'icon': '🏁', 'color': '#795548'},
}

def detect_bpm(y, sr):
    """
    优化版BPM检测算法
    1. 使用44.1kHz原始采样率
    2. 多算法融合
    3. 自动检测half/double time
    """
    if not HAS_LIBROSA:
        return 120
    
    try:
        # 方法1: librosa beat_track (标准算法)
        tempo1, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120, tightness=100)
        tempo1 = float(tempo1)
        
        # 方法2: onset envelope autocorrelation
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
        tempo2 = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
        tempo2 = float(tempo2)
        
        # 方法3: 查看beat frames之间的间隔
        beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
        intervals = np.diff(beat_times)
        intervals = intervals[(intervals > 0.2) & (intervals < 2.0)]  # 过滤异常值
        if len(intervals) > 0:
            median_interval = np.median(intervals)
            tempo3 = 60.0 / median_interval if median_interval > 0 else tempo1
        else:
            tempo3 = tempo1
        
        # 选择最可靠的结果 (中位数，避免极端值)
        all_tempos = [tempo1, tempo2, tempo3]
        best_tempo = np.median(all_tempos)
        
        # 检测 half/double time
        # 如果BPM太低(<80)，很可能是half time
        if best_tempo < 80:
            best_tempo *= 2
        # 如果BPM太高(>180)，很可能是double time
        elif best_tempo > 180:
            best_tempo /= 2
        
        # 四舍五入到0.5
        best_tempo = round(best_tempo * 2) / 2
        
        return float(best_tempo)
        
    except Exception as e:
        print(f"BPM detection error: {e}")
        return 120

def detect_bpm_detailed(y, sr):
    """
    详细BPM分析，返回多个候选值
    """
    results = {}
    
    try:
        # 1. 标准beat_track
        tempo1, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120, tightness=100)
        results['beat_track'] = float(tempo1)
        
        # 2. onset strength tempo
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo2 = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
        results['onset_tempo'] = float(tempo2)
        
        # 3. 基于beat间隔
        beat_times = librosa.frames_to_time(beats, sr=sr)
        intervals = np.diff(beat_times)
        intervals = intervals[(intervals > 0.25) & (intervals < 1.5)]
        if len(intervals) > 0:
            results['interval_median'] = 60.0 / np.median(intervals)
        
        return results
        
    except:
        return {'error': 'detection failed'}

def detect_key(y, sr):
    """调性检测"""
    if not HAS_LIBROSA:
        return 'C'
    
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
        mean_chroma = np.mean(chroma, axis=1)
        
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 3.98, 4.21, 2.62, 5.29, 3.24, 4.63, 2.83, 3.73])
        
        best_key, best_score = 'C', -1
        
        for i in range(12):
            rotated = np.roll(mean_chroma, i)
            for profile, suffix in [(major_profile, ''), (minor_profile, 'm')]:
                corr = np.corrcoef(rotated, profile)[0, 1]
                if corr > best_score:
                    best_score = corr
                    best_key = keys[i] + suffix
        
        return best_key
        
    except:
        return 'C'

def detect_beats(y, sr, tempo):
    """检测节拍时间点"""
    if not HAS_LIBROSA:
        return []
    
    try:
        beat_frames = librosa.beat.beat_track(y=y, sr=sr, bpm=tempo)[1]
        return librosa.frames_to_time(beat_frames, sr=sr, hop_length=512).tolist()
    except:
        return []

def detect_sections(duration, tempo):
    """段落检测"""
    bar_duration = 4 * 60 / tempo
    
    if duration < 90:
        structure = [
            (0, min(bar_duration * 4, duration * 0.15), 'intro'),
            (duration * 0.15, duration * 0.55, 'chorus'),
            (duration * 0.55, duration * 0.85, 'verse'),
            (duration * 0.85, duration, 'outro'),
        ]
    elif duration < 180:
        structure = [
            (0, min(bar_duration * 4, duration * 0.05), 'intro'),
            (duration * 0.05, duration * 0.2, 'verse'),
            (duration * 0.2, duration * 0.35, 'chorus'),
            (duration * 0.35, duration * 0.5, 'verse'),
            (duration * 0.5, duration * 0.7, 'chorus'),
            (duration * 0.7, duration * 0.9, 'bridge'),
            (duration * 0.9, duration, 'outro'),
        ]
    else:
        structure = [
            (0, min(bar_duration * 4, duration * 0.04), 'intro'),
            (duration * 0.04, duration * 0.15, 'verse'),
            (duration * 0.15, duration * 0.28, 'chorus'),
            (duration * 0.28, duration * 0.42, 'verse'),
            (duration * 0.42, duration * 0.55, 'chorus'),
            (duration * 0.55, duration * 0.7, 'bridge'),
            (duration * 0.7, duration * 0.85, 'chorus'),
            (duration * 0.85, duration, 'outro'),
        ]
    
    sections = []
    for start, end, sec_type in structure:
        if start < duration and end <= duration:
            info = SECTION_INFO.get(sec_type, SECTION_INFO['verse'])
            sections.append({
                'start': round(start, 3),
                'end': round(end, 3),
                'type': sec_type,
                'name': info['name'],
                'icon': info['icon'],
                'color': info['color'],
            })
    
    return sections

def estimate_genre(tempo, energy):
    """风格估算"""
    if 120 <= tempo <= 135 and energy > 60:
        return 'Electronic/Dance'
    elif 100 <= tempo <= 130:
        return 'Pop'
    elif tempo >= 140:
        return 'Metal/Rock'
    elif tempo < 100:
        return 'R&B/Hip-Hop'
    return 'Pop/Rock'

def analyze_audio(audio_data, filename='unknown'):
    """主分析函数"""
    if not HAS_LIBROSA:
        return {'error': 'librosa not installed'}
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as f:
            f.write(audio_data)
            temp_path = f.name
        
        # 使用原始采样率 (44.1kHz) 获得最佳BPM精度
        y, sr = librosa.load(temp_path, sr=44100, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # BPM检测
        tempo = detect_bpm(y, sr)
        
        # 详细分析 (调试用)
        bpm_details = detect_bpm_detailed(y, sr)
        
        # 调性
        key = detect_key(y, sr)
        
        # 能量
        rms = librosa.feature.rms(y=y)[0]
        energy = float(np.mean(rms) * 100)
        
        # 节拍
        beats = detect_beats(y, sr, tempo)
        
        # 段落
        sections = detect_sections(duration, tempo)
        
        # 风格
        genre = estimate_genre(tempo, energy)
        
        os.unlink(temp_path)
        
        return {
            'success': True,
            'bpm': tempo,
            'bpmDetails': bpm_details,  # 详细数据用于调试
            'key': key,
            'energy': round(energy, 1),
            'duration': round(duration, 3),
            'genre': genre,
            'beats': beats,
            'sections': sections,
            'sampleRate': sr,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    result = analyze_audio(file.read(), file.filename)
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/analyze-base64', methods=['POST'])
def analyze_base64():
    data = request.get_json()
    if 'audio' not in data:
        return jsonify({'error': 'No audio data provided'}), 400
    
    try:
        audio_data = base64.b64decode(data['audio'])
        filename = data.get('filename', 'audio.mp3')
        result = analyze_audio(audio_data, filename)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'librosa': HAS_LIBROSA})

if __name__ == '__main__':
    print("🎵 VJ-Gen Audio Analysis Server (优化版)")
    print("=" * 45)
    print(f"librosa: {'✅' if HAS_LIBROSA else '❌'}")
    print("Server: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001)
