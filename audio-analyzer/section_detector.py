"""
基于节拍检测的段落分析
使用librosa的beat tracking来找到音乐结构
"""

import numpy as np
import json

def analyze_structure(audio_path, sr=22050, hop_length=512):
    """基于节拍的段落检测"""
    import librosa
    
    print(f"加载: {audio_path}")
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    duration = len(y) / sr
    
    # 1. 节拍跟踪
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, tightness=100)
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop_length)
    tempo = float(tempo)
    print(f"BPM: {tempo:.1f}")
    print(f"节拍数: {len(beat_times)}")
    
    # 2. 计算小节长度
    beat_duration = 60 / tempo  # 单拍时长
    bar_duration = beat_duration * 4  # 4/4拍，一小节
    
    # 3. 使用小节作为基本单位
    bars = []
    current_time = 0
    while current_time < duration:
        bars.append({
            'start': round(current_time, 2),
            'end': round(min(current_time + bar_duration, duration), 2),
            'bar': len(bars)
        })
        current_time += bar_duration
    
    # 4. 分析每小节的能量
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    energy_per_bar = []
    
    for bar in bars:
        start_frame = int(bar['start'] * sr / hop_length)
        end_frame = int(bar['end'] * sr / hop_length)
        end_frame = min(end_frame, len(rms))
        if start_frame < len(rms):
            energy_per_bar.append(float(np.mean(rms[start_frame:end_frame])))
        else:
            energy_per_bar.append(0)
    
    # 归一化
    max_energy = max(energy_per_bar) if energy_per_bar else 1
    energy_per_bar = [e / max_energy for e in energy_per_bar]
    
    # 5. 根据能量合并小节为段落
    # 使用滑动窗口平滑
    window = 4
    energy_smooth = []
    for i in range(len(energy_per_bar)):
        start = max(0, i - window // 2)
        end = min(len(energy_per_bar), i + window // 2 + 1)
        energy_smooth.append(np.mean(energy_per_bar[start:end]))
    
    # 6. 找段落边界
    sections = []
    current_section = {'bars': [], 'start': 0, 'energy': []}
    
    for i, bar in enumerate(bars):
        current_section['bars'].append(bar)
        current_section['energy'].append(energy_smooth[i])
        
        # 检查是否应该分割
        should_split = False
        
        # 条件1：能量突变
        if len(current_section['energy']) >= 2:
            energy_diff = abs(energy_smooth[i] - np.mean(current_section['energy'][:-1]))
            if energy_diff > 0.3 and len(current_section['bars']) >= 2:
                should_split = True
        
        # 条件2：小节数达到上限
        if len(current_section['bars']) >= 8:
            should_split = True
        
        # 条件3：到歌曲末尾
        if i == len(bars) - 1:
            should_split = True
        
        if should_split and current_section['bars']:
            # 确定段落类型
            avg_energy = np.mean(current_section['energy'])
            first_bar = current_section['bars'][0]['bar']
            total_bars = len(bars)
            pos_ratio = first_bar / total_bars
            
            if pos_ratio < 0.1:
                sec_type = 'intro'
            elif pos_ratio > 0.85:
                sec_type = 'outro'
            elif avg_energy > 0.7:
                sec_type = 'chorus'
            elif avg_energy > 0.5:
                sec_type = 'verse'
            else:
                sec_type = 'preChorus'
            
            sections.append({
                'index': len(sections),
                'start': current_section['bars'][0]['start'],
                'end': current_section['bars'][-1]['end'],
                'duration': current_section['bars'][-1]['end'] - current_section['bars'][0]['start'],
                'type': sec_type,
                'name': {'intro':'Intro','verse':'Verse','preChorus':'Pre-Chorus',
                        'chorus':'Chorus','bridge':'Bridge','outro':'Outro'}.get(sec_type, sec_type),
                'bars': len(current_section['bars']),
                'energy': round(avg_energy, 2)
            })
            
            current_section = {'bars': [], 'start': bar['end'], 'energy': []}
    
    return {
        'success': True,
        'sections': sections,
        'duration': round(duration, 2),
        'tempo': round(tempo, 1),
        'total_bars': len(bars),
        'bar_duration': round(bar_duration, 3)
    }

def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python section_detector.py <audio_file>")
        sys.exit(1)
    
    result = analyze_structure(sys.argv[1])
    
    if result['success']:
        print(f"\n🎵 检测结果: {result['tempo']} BPM, {result['total_bars']} 小节")
        print(f"\n✅ 检测到 {len(result['sections'])} 个段落:")
        print("-" * 60)
        print(f"{'#':<3} {'类型':12} {'开始':>8} {'结束':>8} {'时长':>6} {'小节':>5} {'能量':>6}")
        print("-" * 60)
        for s in result['sections']:
            print(f"{s['index']:<3} {s['name']:12} {s['start']:>7.2f}s {s['end']:>7.2f}s {s['duration']:>5.1f}s {s['bars']:>5} {s['energy']:>6.2f}")
        
        # 保存
        output = sys.argv[1].replace('.mp3', '_sections.json').replace('.wav', '_sections.json')
        with open(output, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 保存到: {output}")
    else:
        print(f"❌ 错误: {result.get('error', 'unknown')}")

if __name__ == '__main__':
    main()
