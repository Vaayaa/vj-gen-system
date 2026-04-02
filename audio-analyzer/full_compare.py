#!/usr/bin/env python3
"""
音频分析全方法对比 v3
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

def analyze_librosa(y, sr, duration):
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
    return {'method': 'librosa', 'description': '学术标准', 'accuracy': '⭐⭐⭐', 'bpm': round(tempo, 1), 'key': key, 'energy': round(energy, 1), 'sections': sections, 'beats': beat_times[:100], 'status': 'success'}

def analyze_essentia(y, sr, duration):
    try:
        from essentia.standard import RhythmExtractor2013, KeyExtractor
    except:
        return {'method': 'essentia', 'status': 'error', 'error': 'not installed'}
    try:
        y = y.astype(np.float32)
        rhythm = RhythmExtractor2013()
        bpm, _, _, _, _ = rhythm(y)
        key_extractor = KeyExtractor()
        key_str, scale, _ = key_extractor(y)
        key = str(key_str).replace('maj', '').replace('min', 'm')
        energy = float(np.sqrt(np.mean(y**2)) * 100)
        sections = detect_sections(duration, bpm)
        return {'method': 'essentia', 'description': 'Spotify同款', 'accuracy': '⭐⭐⭐⭐', 'bpm': round(float(bpm), 1), 'key': key, 'energy': round(energy, 1), 'sections': sections, 'beats': [], 'status': 'success'}
    except Exception as e:
        return {'method': 'essentia', 'status': 'error', 'error': str(e)}

def analyze_madmom(y, sr, duration):
    try:
        import madmom
        from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor
    except:
        return {'method': 'madmom', 'status': 'error', 'error': 'not installed'}
    try:
        y = y.astype(np.float32)
        rnn_proc = RNNBeatProcessor()
        act = rnn_proc(y)
        beat_proc = DBNBeatTrackingProcessor(fps=100)
        beats = beat_proc(act)
        bpm = 60.0 / np.median(np.diff(beats)) if len(beats) > 1 else 120.0
        sections = detect_sections(duration, bpm)
        return {'method': 'madmom', 'description': '深度学习SOTA', 'accuracy': '⭐⭐⭐⭐⭐', 'bpm': round(float(bpm), 1), 'key': '-', 'energy': 50, 'sections': sections, 'beats': [float(x) for x in beats], 'status': 'success'}
    except Exception as e:
        return {'method': 'madmom', 'status': 'error', 'error': str(e)}

def compare_all(audio_path):
    print(f"\n{'='*60}")
    print(f"🎵 音频分析全对比: {os.path.basename(audio_path)}")
    print('='*60)
    
    import librosa
    print("\n📂 加载音频...")
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = len(y) / sr
    print(f"   时长: {duration:.1f}s")
    
    results = {}
    print("\n[🔬 librosa] 分析中...")
    results['librosa'] = analyze_librosa(y, sr, duration)
    print("[⚙️  Essentia] 分析中...")
    results['essentia'] = analyze_essentia(y, sr, duration)
    print("[🧠 madmom] 分析中...")
    results['madmom'] = analyze_madmom(y, sr, duration)
    results['omnizart'] = {'method': 'omnizart', 'status': 'pending', 'error': '依赖问题'}
    
    print("\n" + "="*60)
    print("📊 结果对比")
    print("="*60)
    print("\n┌─────────────┬────────┬────────┬────────┬────────┐")
    print("│   指标      │librosa │essentia│ madmom │omnizart│")
    print("├─────────────┼────────┼────────┼────────┼────────┤")
    
    for metric, key in [('BPM', 'bpm'), ('Key', 'key'), ('Energy', 'energy'), ('Sections', 'sections')]:
        vals = []
        for m in ['librosa', 'essentia', 'madmom', 'omnizart']:
            r = results[m]
            if r.get('status') != 'success':
                vals.append('❌')
            else:
                if key == 'sections':
                    vals.append(str(len(r.get(key, []))))
                else:
                    vals.append(str(r.get(key, '--')))
        print(f"│ {metric:10} │{vals[0]:^8}│{vals[1]:^8}│{vals[2]:^8}│{vals[3]:^8}│")
    print("└─────────────┴────────┴────────┴────────┴────────┘")
    
    for name in ['librosa', 'essentia', 'madmom']:
        r = results[name]
        status = r.get('status', 'unknown')
        icon = '✅' if status == 'success' else '❌'
        acc = r.get('accuracy', '-')
        print(f"{icon} {name}: {r.get('description', '')} {acc}")
        if status == 'success':
            print(f"   BPM={r['bpm']}, Key={r['key']}, Sections={len(r.get('sections', []))}")
        else:
            print(f"   {r.get('error', 'unknown')}")
    
    print("\n❌ omnizart: 依赖问题待修复")
    
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python full_compare.py <audio_file>")
        sys.exit(1)
    
    results = compare_all(sys.argv[1])
    output_path = sys.argv[1].replace('.mp3', '_full_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存: {output_path}")
