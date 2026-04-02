#!/usr/bin/env python3
"""
音频分析三种方法对比 v2
1. librosa - 学术标准
2. Essentia - 工业级 (Spotify同款)
3. madmom - 深度学习 SOTA (conda环境)
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
    
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120, tightness=100)
    tempo = float(tempo)
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512).tolist()
    
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    mean_chroma = np.mean(chroma, axis=1)
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    key = keys[np.argmax(mean_chroma)]
    
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    energy = float(np.mean(rms) * 100)
    
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
        y = y.astype(np.float32)
        rhythm = RhythmExtractor2013()
        bpm, _, _, _, _ = rhythm(y)
        
        key_extractor = KeyExtractor()
        key_str, scale, _ = key_extractor(y)
        key = str(key_str).replace('maj', '').replace('min', 'm')
        
        energy = float(np.sqrt(np.mean(y**2)) * 100)
        sections = detect_sections(duration, bpm)
        
        return {
            'method': 'essentia',
            'description': 'Spotify同款，工业级标准',
            'bpm': round(float(bpm), 1),
            'key': key,
            'energy': round(energy, 1),
            'duration': round(duration, 2),
            'sections': sections,
            'beats': []
        }
    except Exception as e:
        return {'method': 'essentia', 'error': str(e)}

# ============== METHOD 3: madmom ==============
def analyze_madmom(y, sr, duration):
    """madmom深度学习分析"""
    try:
        import madmom
        from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor
    except ImportError as e:
        return {'method': 'madmom', 'error': f'not installed: {e}'}
    
    try:
        # Ensure float32
        y = y.astype(np.float32)
        
        # Use RNN beat processor (more robust)
        rnn_proc = RNNBeatProcessor()
        act = rnn_proc(y)
        
        # Then DBN tracker
        beat_proc = DBNBeatTrackingProcessor(fps=100)
        beats = beat_proc(act)
        
        if len(beats) > 1:
            intervals = np.diff(beats)
            bpm = 60.0 / np.median(intervals)
        else:
            bpm = 120.0
        
        beat_times = [float(x) for x in beats]
        sections = detect_sections(duration, bpm)
        
        return {
            'method': 'madmom',
            'description': '深度学习SOTA，RNN+DBN',
            'bpm': round(float(bpm), 1),
            'key': '-',  # madmom不直接支持调性
            'energy': 50,
            'duration': round(duration, 2),
            'sections': sections,
            'beats': beat_times[:100]
        }
    except Exception as e:
        return {'method': 'madmom', 'error': str(e)}

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
    
    print("\n[1/3] 🔬 librosa 分析中...")
    results['librosa'] = analyze_librosa(y, sr, duration)
    
    print("[2/3] ⚙️  Essentia 分析中...")
    results['essentia'] = analyze_essentia(y, sr, duration)
    
    print("[3/3] 🧠 madmom 分析中...")
    results['madmom'] = analyze_madmom(y, sr, duration)
    
    # Print comparison
    print("\n" + "="*60)
    print("📊 结果对比")
    print("="*60)
    
    print("\n┌─────────────┬────────┬────────┬────────┐")
    print("│   指标      │librosa │essentia│ madmom │")
    print("├─────────────┼────────┼────────┼────────┤")
    
    for metric, label in [('BPM', 'bpm'), ('Key', 'key'), ('Energy', 'energy')]:
        vals = []
        for m in ['librosa', 'essentia', 'madmom']:
            r = results[m]
            if 'error' in r:
                vals.append('❌')
            else:
                vals.append(str(r.get(label, '-')))
        print(f"│ {metric:10} │{vals[0]:^8}│{vals[1]:^8}│{vals[2]:^8} │")
    
    print("└─────────────┴────────┴────────┴────────┘")
    
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
        print("注意: madmom需要conda环境:")
        print("  conda activate madmom-env")
        sys.exit(1)
    
    results = compare_methods(sys.argv[1])
    
    output_path = sys.argv[1].replace('.mp3', '_analysis.json').replace('.wav', '_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存: {output_path}")
