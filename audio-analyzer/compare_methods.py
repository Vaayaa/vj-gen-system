#!/usr/bin/env python3
"""
音频分析三种方法对比
1. librosa - 学术标准 (已安装)
2. Essentia - 工业级 (已安装)
3. madmom - 深度学习 (Python3.10兼容问题，跳过)
"""

import sys
import json
import os
import numpy as np

SECTION_TYPES = {
    'intro': {'name': 'Intro', 'color': '#607D8B'},
    'verse': {'name': 'Verse', 'color': '#2196F3'},
    'preChorus': {'name': 'Pre-Chorus', 'color': '#03A9F4'},
    'chorus': {'name': 'Chorus', 'color': '#E91E63'},
    'bridge': {'name': 'Bridge', 'color': '#FF9800'},
    'outro': {'name': 'Outro', 'color': '#795548'},
}

def detect_sections(duration, tempo):
    """基于时长的段落检测"""
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
            info = SECTION_TYPES.get(sec_type, SECTION_TYPES['verse'])
            sections.append({
                'start': round(start, 2),
                'end': round(end, 2),
                'type': sec_type,
                'name': info['name'],
                'icon': '🎵',
                'color': info['color'],
            })
    return sections

# ============== METHOD 1: librosa ==============
def analyze_librosa(y, sr, duration):
    """librosa标准分析"""
    import librosa
    
    # BPM检测
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120, tightness=100)
    tempo = float(tempo)
    
    # 节拍时间
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512).tolist()
    
    # 调性检测
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    mean_chroma = np.mean(chroma, axis=1)
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    key = keys[np.argmax(mean_chroma)]
    
    # 能量
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    energy = float(np.mean(rms) * 100)
    
    # 段落
    sections = detect_sections(duration, tempo)
    
    return {
        'method': 'librosa',
        'description': '学术标准，功能全面',
        'bpm': round(tempo, 1),
        'key': key,
        'energy': round(energy, 1),
        'duration': round(duration, 2),
        'sections': sections,
        'beats': beat_times[:100]
    }

# ============== METHOD 2: Essentia ==============
def analyze_essentia(y, sr, duration):
    """Essentia工业级分析"""
    try:
        from essentia.standard import RhythmExtractor2013, KeyExtractor
    except ImportError as e:
        return {'method': 'essentia', 'error': f'not installed: {e}'}
    
    try:
        # 确保float32
        y = y.astype(np.float32)
        
        # BPM检测
        rhythm = RhythmExtractor2013()
        bpm, _, _, _, _ = rhythm(y)
        
        # 调性检测
        key_extractor = KeyExtractor()
        key_str, scale, _ = key_extractor(y)
        key = str(key_str).replace('maj', '').replace('min', 'm')
        
        # 能量估算
        energy = float(np.sqrt(np.mean(y**2)) * 100)
        
        # 段落
        sections = detect_sections(duration, bpm)
        
        # 节拍
        try:
            from essentia.standard import BeatTrackerMultiFeature
            bt = BeatTrackerMultiFeature()
            beats = bt(y)
            beat_times = [float(x) for x in beats] if hasattr(beats, 'tolist') else list(beats)
        except:
            beat_times = []
        
        return {
            'method': 'essentia',
            'description': 'Spotify同款，工业级标准',
            'bpm': round(float(bpm), 1),
            'key': key,
            'scale': scale,
            'energy': round(energy, 1),
            'duration': round(duration, 2),
            'sections': sections,
            'beats': beat_times[:100]
        }
    except Exception as e:
        return {'method': 'essentia', 'error': str(e)}

# ============== METHOD 3: madmom ==============
def analyze_madmom(y, sr, duration):
    """madmom - Python 3.10 兼容性问题，跳过"""
    return {
        'method': 'madmom',
        'error': 'Python 3.10 兼容性问题 (MutableSequence moved to collections.abc)',
        'description': '深度学习SOTA，建议使用conda环境安装',
        'note': '建议: conda create -n madmom python=3.9'
    }

def compare_methods(audio_path):
    """对比三种方法"""
    print(f"\n{'='*60}")
    print(f"🎵 音频分析对比: {os.path.basename(audio_path)}")
    print('='*60)
    
    # Load audio
    print("\n📂 加载音频...")
    import librosa
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = len(y) / sr
    print(f"   时长: {duration:.1f}s, 采样率: {sr}Hz")
    
    results = {}
    
    # Method 1: librosa
    print("\n[1/3] 🔬 librosa 分析中...")
    results['librosa'] = analyze_librosa(y, sr, duration)
    
    # Method 2: Essentia
    print("[2/3] ⚙️  Essentia 分析中...")
    results['essentia'] = analyze_essentia(y, sr, duration)
    
    # Method 3: madmom
    print("[3/3] 🧠 madmom 分析中...")
    results['madmom'] = analyze_madmom(y, sr, duration)
    
    # Print comparison
    print("\n" + "="*60)
    print("📊 结果对比")
    print("="*60)
    
    # BPM对比
    print("\n┌─────────────┬────────┬────────┬────────┐")
    print("│   指标      │librosa │essentia│ madmom │")
    print("├─────────────┼────────┼────────┼────────┤")
    
    bpm_data = []
    for m in ['librosa', 'essentia', 'madmom']:
        r = results[m]
        if 'error' in r:
            bpm_data.append('❌')
        else:
            bpm_data.append(str(r['bpm']))
    
    print(f"│ BPM        │{bpm_data[0]:^8}│{bpm_data[1]:^8}│{bpm_data[2]:^8}│")
    
    key_data = []
    for m in ['librosa', 'essentia', 'madmom']:
        r = results[m]
        if 'error' in r:
            key_data.append('❌')
        else:
            key_data.append(r.get('key', '-'))
    
    print(f"│ Key        │{key_data[0]:^8}│{key_data[1]:^8}│{key_data[2]:^8}│")
    
    energy_data = []
    for m in ['librosa', 'essentia', 'madmom']:
        r = results[m]
        if 'error' in r:
            energy_data.append('❌')
        else:
            energy_data.append(str(r.get('energy', '-')))
    
    print(f"│ Energy     │{energy_data[0]:^8}│{energy_data[1]:^8}│{energy_data[2]:^8}│")
    print("└─────────────┴────────┴────────┴────────┘")
    
    # Sections
    print("\n🎬 段落检测:")
    for m in ['librosa', 'essentia', 'madmom']:
        r = results[m]
        if 'error' in r:
            print(f"\n  ❌ {m}: {r['error']}")
        else:
            print(f"\n  ✅ {m} ({r['description']})")
            print(f"     段落数: {len(r['sections'])}")
            for s in r['sections']:
                print(f"     {s['name']:10} {s['start']:6.1f}s - {s['end']:6.1f}s")
    
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python compare_methods.py <audio_file>")
        print("示例: python compare_methods.py /path/to/song.mp3")
        sys.exit(1)
    
    results = compare_methods(sys.argv[1])
    
    # Save results
    output_path = sys.argv[1].replace('.mp3', '_analysis.json').replace('.wav', '_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存: {output_path}")
