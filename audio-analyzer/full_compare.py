#!/usr/bin/env python3
"""
音频分析全方法对比 v6
基于能量的智能段落分类
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

def classify_section(pos_ratio, rel_energy, section_idx, total_sections):
    """基于位置和能量的段落分类"""
    # 位置判断
    if pos_ratio < 0.08:
        return 'intro'
    if pos_ratio > 0.92:
        return 'outro'
    
    # 能量判断
    if rel_energy > 1.1:
        return 'chorus'
    elif rel_energy < 0.9:
        if pos_ratio > 0.4 and pos_ratio < 0.7:
            return 'bridge'
        return 'verse'
    else:
        # 中等能量
        if pos_ratio < 0.3:
            return 'intro'
        elif pos_ratio > 0.7:
            return 'outro'
        else:
            return 'preChorus'

def detect_sections_improved(y, sr, duration, bpm):
    """改进的段落检测"""
    import librosa
    
    beat_duration = 60 / bpm
    bar_duration = beat_duration * 4
    
    bars = []
    current_time = 0
    while current_time < duration:
        bars.append({'start': current_time, 'end': min(current_time + bar_duration, duration)})
        current_time += bar_duration
    
    # 计算每小节能量
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    energy_per_bar = []
    
    for bar in bars:
        start_frame = int(bar['start'] * sr / 512)
        end_frame = int(bar['end'] * sr / 512)
        end_frame = min(end_frame, len(rms))
        if start_frame < len(rms):
            energy_per_bar.append(float(np.mean(rms[start_frame:end_frame])))
        else:
            energy_per_bar.append(0)
    
    if not energy_per_bar:
        return []
    
    median_energy = np.median(energy_per_bar)
    
    # 平滑
    window = 3
    energy_smooth = []
    for i in range(len(energy_per_bar)):
        start = max(0, i - window // 2)
        end = min(len(energy_per_bar), i + window // 2 + 1)
        energy_smooth.append(np.mean(energy_per_bar[start:end]))
    
    # 合并小节为段落
    sections = []
    current_section = {'bars': [], 'energy': []}
    
    for i, bar in enumerate(bars):
        current_section['bars'].append(bar)
        current_section['energy'].append(energy_smooth[i])
        
        should_split = False
        
        if len(current_section['energy']) >= 2:
            prev_avg = np.mean(current_section['energy'][:-1])
            curr = energy_smooth[i]
            if prev_avg > 0:
                ratio = curr / prev_avg
                if ratio < 0.75 or ratio > 1.35:
                    should_split = True
        
        if len(current_section['bars']) >= 8:
            should_split = True
        
        if i == len(bars) - 1:
            should_split = True
        
        if should_split and current_section['bars']:
            avg_energy = np.mean(current_section['energy'])
            total_bars = len(bars)
            pos_ratio = (current_section['bars'][0]['start'] / duration) if duration > 0 else 0
            rel_energy = avg_energy / median_energy if median_energy > 0 else 1
            
            sec_type = classify_section(pos_ratio, rel_energy, len(sections), total_bars)
            info = SECTION_TYPES.get(sec_type, SECTION_TYPES['verse'])
            
            sections.append({
                'start': round(current_section['bars'][0]['start'], 2),
                'end': round(current_section['bars'][-1]['end'], 2),
                'type': sec_type,
                'name': info['name'],
                'color': info['color'],
                'bars': len(current_section['bars']),
                'energy': round(avg_energy, 3),
                'rel_energy': round(rel_energy, 2)
            })
            current_section = {'bars': [], 'energy': []}
    
    return sections

def analyze_librosa(y, sr, duration):
    import librosa
    
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120, tightness=100)
    tempo = float(tempo)
    
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    mean_chroma = np.mean(chroma, axis=1)
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    key = keys[np.argmax(mean_chroma)]
    
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    energy = float(np.mean(rms) * 100)
    
    sections = detect_sections_improved(y, sr, duration, tempo)
    
    return {'method': 'librosa', 'bpm': round(tempo, 1), 'key': key, 'energy': round(energy, 1), 'sections': sections, 'status': 'success'}

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
        sections = detect_sections_improved(y, sr, duration, bpm)
        
        return {'method': 'essentia', 'bpm': round(float(bpm), 1), 'key': key, 'energy': round(energy, 1), 'sections': sections, 'status': 'success'}
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
        
        if len(beats) > 1:
            intervals = np.diff(beats)
            bpm = 60.0 / np.median(intervals)
        else:
            bpm = 120.0
        
        sections = detect_sections_improved(y, sr, duration, bpm)
        
        return {'method': 'madmom', 'bpm': round(float(bpm), 1), 'key': '-', 'energy': 50, 'sections': sections, 'status': 'success'}
    except Exception as e:
        return {'method': 'madmom', 'status': 'error', 'error': str(e)}

def compare_all(audio_path):
    print(f"\n{'='*60}")
    print(f"🎵 音频分析全对比 v6")
    print(f"📁 {os.path.basename(audio_path)}")
    print('='*60)
    
    import librosa
    print("\n📂 加载音频...")
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = len(y) / sr
    print(f"   时长: {duration:.1f}s | 采样率: {sr}Hz")
    
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
    
    for metric, key in [('BPM', 'bpm'), ('Key', 'key'), ('Energy', 'energy'), ('段落', 'sections')]:
        vals = []
        for m in ['librosa', 'essentia', 'madmom', 'omnizart']:
            r = results[m]
            if r.get('status') != 'success':
                vals.append('❌')
            else:
                if key == 'sections':
                    vals.append(str(len(r.get(key, []))))
                else:
                    val = r.get(key, '--')
                    vals.append(str(val) if val is not None else '--')
        print(f"│ {metric:10} │{vals[0]:^8}│{vals[1]:^8}│{vals[2]:^8}│{vals[3]:^8}│")
    print("└─────────────┴────────┴────────┴────────┴────────┘")
    
    for name in ['librosa', 'essentia', 'madmom']:
        r = results[name]
        if r.get('status') == 'success':
            print(f"\n✅ {name}: BPM={r['bpm']}, Key={r['key']}")
            for s in r.get('sections', []):
                print(f"   [{s['name']:10}] {s['start']:5.1f}s-{s['end']:5.1f}s | 能量:{s.get('rel_energy',0):.2f}")
        else:
            print(f"\n❌ {name}: {r.get('error', 'unknown')}")
    
    results['audio'] = {'duration': duration, 'sample_rate': sr}
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python full_compare.py <audio_file>")
        sys.exit(1)
    
    results = compare_all(sys.argv[1])
    output_path = sys.argv[1].replace('.mp3', '_full_analysis.json').replace('.wav', '_full_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存: {output_path}")
