"""
VJ Pipeline - 音频到视觉的完整处理管线
=========================================
将 audio_analysis_module 和 vj_visual_map 串联起来，
生成完整的 VJ 时间线和视觉参数。

流程:
    音频文件 → audio_analysis_module → 音频特征
                                            ↓
                              vj_visual_map → 视觉参数
                                            ↓
                              VJTimeline → JSON输出
"""

import json
import os
from pathlib import Path
from typing import Optional

# 确保能找到 audio_analysis_module
import sys

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODULE_DIR)

from audio_analysis_module import (
    analyze_beats,
    analyze_segments,
    analyze_energy,
    analyze_key,
    analyze_emotion,
    full_analysis,
)
try:
    from src.pipelines.vj_timeline_mapper import (
        map_audio_to_visual,
        generate_visual_timeline,
        PALETTES,
        VisualParams,
        SegmentVisual,
    )
except ImportError:
    # running as script from project root
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.pipelines.vj_timeline_mapper import (
        map_audio_to_visual,
        generate_visual_timeline,
        PALETTES,
        VisualParams,
        SegmentVisual,
    )


class VJPipeline:
    """
    VJ 主处理管线
    
    整合音频分析和视觉映射，输出完整的 VJ 时间线数据。
    
    用法:
        pipeline = VJPipeline()
        result = pipeline.process('/path/to/audio.mp3')
        print(result['vj']['beats'][0].params.animation_speed)
    """
    
    def __init__(self, fps: int = 60):
        """
        Args:
            fps: 每秒帧数（用于生成每帧时间线）
        """
        self.fps = fps
    
    def analyze(self, audio_path: str) -> dict:
        """
        运行完整音频分析 + 视觉映射
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            dict {
                'audio': full_analysis 结果,
                'vj': {
                    'global': VisualParams,
                    'beats': List[VisualParams],
                    'segments': List[SegmentVisual],
                    'bpm': float,
                    'total_beats': int,
                    'total_segments': int,
                },
                'timeline': List[dict],  # 每帧视觉参数
                'palettes': dict,         # 调色板定义
            }
        """
        # 1. 音频分析
        audio_result = full_analysis(audio_path)
        
        # 2. 转换格式
        bpm = audio_result.get('beat', {}).get('bpm', 120.0)
        beat_positions = audio_result.get('beat', {}).get('beats', [])
        beat_interval = 60.0 / bpm if bpm > 0 else 0.5
        
        # beats: 位置列表 → {start, strength, is_accent}
        beats = []
        for i, pos in enumerate(beat_positions):
            is_accent = (i % 4 == 0)
            strength = 1.0 if is_accent else (0.6 if i % 2 == 0 else 0.3)
            beats.append({
                'start': float(pos),
                'strength': strength,
                'is_accent': is_accent,
            })
        
        # sections: segs → [{start, end, type, energy}]
        segs_raw = audio_result.get('seg', {}).get('segs', [])
        duration = audio_result.get('beat', {}).get('dur', 30.0)
        n_segs = len(segs_raw)
        
        # 根据段落位置分配类型
        sections = []
        for i, s in enumerate(segs_raw):
            # 分配段落类型
            if n_segs <= 1:
                sec_type = 'verse'
            else:
                ratio = i / (n_segs - 1) if n_segs > 1 else 0.5
                if ratio < 0.15:
                    sec_type = 'intro'
                elif ratio < 0.35:
                    sec_type = 'verse'
                elif ratio < 0.55:
                    sec_type = 'chorus'
                elif ratio < 0.75:
                    sec_type = 'bridge'
                else:
                    sec_type = 'outro'
            
            # 计算段落能量
            sec_start = s['s']
            sec_end = s['e']
            sec_beats = [b for b in beats if sec_start <= b['start'] < sec_end]
            if sec_beats:
                avg_strength = sum(b['strength'] for b in sec_beats) / len(sec_beats)
            else:
                avg_strength = 0.5
            
            sections.append({
                'start': s['s'],
                'end': s['e'],
                'type': sec_type,
                'energy': avg_strength,
            })
        
        # energy_curve: 从 audio_result 提取或生成
        energy_data = audio_result.get('ener', audio_result.get('energy', {}))
        avg_energy = energy_data.get('avg_rms', 0.5) if isinstance(energy_data, dict) else 0.5
        energy_curve = [
            {'timestamp': 0.0, 'energy': avg_energy},
            {'timestamp': duration / 2, 'energy': min(1.0, avg_energy * 1.3)},
            {'timestamp': duration, 'energy': avg_energy * 0.8},
        ]
        
        # 3. 格式化为音频结果
        audio_formatted = {
            'bpm': bpm,
            'duration': duration,
            'beats': beats,
            'sections': sections,
            'energy_curve': energy_curve,
            'key': audio_result.get('key', {}).get('name', 'C大调'),
            'emotion': audio_result.get('emotion', {}).get('emotion', 'Exciting'),
        }
        
        # 4. 视觉映射
        vj_result = map_audio_to_visual(audio_formatted)
        
        # 5. 生成每帧时间线
        timeline = generate_visual_timeline(audio_formatted, fps=self.fps)
        
        return {
            'audio': audio_result,
            'vj': vj_result,
            'timeline': timeline,
            'palettes': PALETTES,
            'fps': self.fps,
            'duration': duration,
            'bpm': bpm,
        }
    
    def process(self, audio_path: str) -> dict:
        """analyze 的别名"""
        return self.analyze(audio_path)
    
    def export_json(self, audio_path: str, output_path: Optional[str] = None) -> str:
        """
        分析并导出为 JSON 文件
        
        Args:
            audio_path: 音频文件路径
            output_path: 输出JSON路径（可选，默认同目录）
        
        Returns:
            输出的JSON文件路径
        """
        result = self.analyze(audio_path)
        
        if output_path is None:
            audio_dir = os.path.dirname(audio_path)
            audio_name = os.path.splitext(os.path.basename(audio_path))[0]
            output_path = os.path.join(audio_dir, f"{audio_name}_vj.json")
        
        # 序列化（VisualParams/SegmentVisual → dict）
        output = {
            'meta': {
                'audio_path': audio_path,
                'fps': self.fps,
                'duration': result['duration'],
                'bpm': result['bpm'],
            },
            'global': result['vj']['global'].to_dict(),
            'beats': [b.to_dict() for b in result['vj']['beats']],
            'segments': [
                {
                    'start': sv.start,
                    'end': sv.end,
                    'section_type': sv.section_type,
                    'bpm': sv.bpm,
                    'energy': sv.energy,
                    'params': sv.params.to_dict(),
                }
                for sv in result['vj']['segments']
            ],
            'palettes': result['palettes'],
            'timeline': result['timeline'],
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def get_visual_at_time(self, result: dict, timestamp: float) -> dict:
        """
        获取指定时间的视觉参数
        
        Args:
            result: analyze() 的返回结果
            timestamp: 时间（秒）
        
        Returns:
            对应时间的帧参数字典
        """
        timeline = result['timeline']
        frame_idx = int(timestamp * self.fps)
        frame_idx = max(0, min(frame_idx, len(timeline) - 1))
        return timeline[frame_idx]


# ============================================================================
# 快捷函数
# ============================================================================

def process(audio_path: str, fps: int = 60) -> dict:
    """快捷函数：分析音频并返回完整VJ数据"""
    return VJPipeline(fps=fps).process(audio_path)


if __name__ == '__main__':
    # 测试
    test_audio = '/tmp/test_beat_120bpm.wav'
    if os.path.exists(test_audio):
        print(f"Processing: {test_audio}")
        result = VJPipeline().process(test_audio)
        print(f"\n✅ Analysis complete!")
        print(f"   BPM: {result['bpm']}")
        print(f"   Duration: {result['duration']:.1f}s")
        print(f"   Beats: {len(result['vj']['beats'])}")
        print(f"   Segments: {len(result['vj']['segments'])}")
        print(f"   Timeline frames: {len(result['timeline'])}")
        print(f"\n   Global palette: {result['vj']['global'].palette}")
        print(f"   Global animation speed: {result['vj']['global'].animation_speed:.3f}x")
        print()
        for sv in result['vj']['segments']:
            print(f"   [{sv.section_type}] {sv.start:.1f}-{sv.end:.1f}s | {sv.params.palette} | {sv.params.animation_speed:.2f}x | {sv.params.transition_type}")
    else:
        print(f"Test audio not found: {test_audio}")
