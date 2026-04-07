#!/usr/bin/env python3
"""
VJ Visual Mapper — 音频分析 → 视觉参数映射
==========================================
将 BPM/调性/能量/情绪/段落 映射为 VJ 视觉参数
"""
import numpy as np
from typing import Dict, Any, List

# ─── 调性 → 颜色映射 ───────────────────────────────────────────
# 按感觉调色轮：暖调前进/冷调后退
KEY_PALETTE: Dict[str, List[str]] = {
    'C':  ['#FF6B6B', '#EE5A5A', '#FF8787'],   # 温暖红
    'C#': ['#E05CB0', '#C94B9B', '#D472B5'],   # 玫瑰紫
    'D':  ['#F093FB', '#E070D0', '#F5A0F8'],   # 亮粉
    'D#': ['#A855F7', '#9333EA', '#B366F7'],   # 电紫
    'E':  ['#7C3AED', '#6D28D9', '#8B5CF6'],   # 深紫蓝
    'F':  ['#3B82F6', '#2563EB', '#60A5FA'],   # 冷蓝
    'F#': ['#06B6D4', '#0891B2', '#22D3EE'],   # 青色
    'G':  ['#14B8A6', '#0D9488', '#2DD4BF'],   # 青绿
    'G#': ['#10B981', '#059669', '#34D399'],   # 翠绿
    'A':  ['#22C55E', '#16A34A', '#4ADE80'],   # 鲜绿
    'A#': ['#EAB308', '#CA8A04', '#FACC15'],   # 暖黄
    'B':  ['#F59E0B', '#D97706', '#FBBF24'],   # 琥珀
}
KEY_MODES = {'major': 'bright', 'minor': 'dark'}

# ─── 情绪 → 主视觉风格 ─────────────────────────────────────
EMOTION_VISUAL: Dict[str, Dict[str, Any]] = {
    'Happy': {
        'palette': 'vivid',
        'motion': 'lively',
        'particle_density': 'high',
        'color_temp': 'warm',
        'contrast': 'high',
        'blur': 0.0,
        'glow_intensity': 0.8,
        'motion_amplitude': 0.8,
        'beatsync_flash': True,
    },
    'Exciting': {
        'palette': 'neon',
        'motion': 'intense',
        'particle_density': 'very_high',
        'color_temp': 'hot',
        'contrast': 'maximum',
        'blur': 0.0,
        'glow_intensity': 1.0,
        'motion_amplitude': 1.0,
        'beatsync_flash': True,
    },
    'Angry': {
        'palette': 'fire',
        'motion': 'aggressive',
        'particle_density': 'high',
        'color_temp': 'hot',
        'contrast': 'very_high',
        'blur': 0.3,
        'glow_intensity': 0.9,
        'motion_amplitude': 0.9,
        'beatsync_flash': True,
    },
    'Tense': {
        'palette': 'dramatic',
        'motion': 'pulsing',
        'particle_density': 'medium',
        'color_temp': 'cold',
        'contrast': 'high',
        'blur': 0.2,
        'glow_intensity': 0.6,
        'motion_amplitude': 0.5,
        'beatsync_flash': False,
    },
    'Calm': {
        'palette': 'soothing',
        'motion': 'flowing',
        'particle_density': 'low',
        'color_temp': 'cool',
        'contrast': 'medium',
        'blur': 0.5,
        'glow_intensity': 0.3,
        'motion_amplitude': 0.2,
        'beatsync_flash': False,
    },
    'Sad': {
        'palette': 'melancholic',
        'motion': 'slow',
        'particle_density': 'low',
        'color_temp': 'cold',
        'contrast': 'low',
        'blur': 0.6,
        'glow_intensity': 0.2,
        'motion_amplitude': 0.1,
        'beatsync_flash': False,
    },
    'Neutral': {
        'palette': 'balanced',
        'motion': 'steady',
        'particle_density': 'medium',
        'color_temp': 'neutral',
        'contrast': 'medium',
        'blur': 0.1,
        'glow_intensity': 0.4,
        'motion_amplitude': 0.4,
        'beatsync_flash': False,
    },
}

# ─── BPM → 动画速度 ─────────────────────────────────────────
def bpm_to_speed(bpm: float) -> float:
    """BPM → 动画速度因子 (0-1, 1=最快)"""
    # 60BPM=0.1, 180BPM=1.0
    return float(np.clip((bpm - 60) / 120, 0, 1))

def bpm_to_motion_interval(bpm: float) -> float:
    """BPM → 帧间隔(秒)"""
    # beat间隔 = 60/bpm 秒
    beat_interval = 60.0 / max(bpm, 1)
    # 通常动画每beat变化一次
    return beat_interval

# ─── 能量 → 视觉效果 ────────────────────────────────────────
def energy_to_brightness(rms: float, rms_max: float = 1.0) -> float:
    """RMS能量 → 亮度因子 (0-1)"""
    return float(np.clip(rms / rms_max, 0, 1))

def energy_to_saturation(rms: float, rms_avg: float) -> float:
    """RMS能量 → 饱和度因子"""
    ratio = rms / (rms_avg + 1e-10)
    return float(np.clip(ratio * 0.8 + 0.2, 0.2, 1.0))

def energy_to_blur(rms: float, rms_avg: float) -> float:
    """能量高时降低模糊，保持锐度"""
    ratio = rms / (rms_avg + 1e-10)
    # 高能量=低模糊(锐利)，低能量=高模糊(柔焦)
    return float(np.clip(1.0 - ratio * 0.7, 0, 0.8))

# ─── 主映射函数 ────────────────────────────────────────────
def map_analysis_to_vj(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """将音频分析结果映射为 VJ 视觉参数"""
    
    # 提取各模块结果
    beat = analysis.get('beat', {})
    seg  = analysis.get('seg', {})
    key  = analysis.get('key', {})
    energy = analysis.get('energy', {})
    emotion = analysis.get('emotion', {})
    
    bpm = float(beat.get('bpm', 120))
    key_name = key.get('key', 'C')
    mode = key.get('mode', 'M')  # M or m
    em = emotion.get('em', 'Neutral')
    em_cn = emotion.get('em_cn', '中性')
    energy_vals = energy.get('rms', [])
    energy_avg = float(np.mean(energy_vals)) if energy_vals else 0.0
    energy_max = float(np.max(energy_vals)) if energy_vals else 1.0
    
    # ── 调性色板 ──
    key_colors = KEY_PALETTE.get(key_name, KEY_PALETTE['C'])
    key_mode = KEY_MODES.get(mode, 'bright')
    
    # ── 情绪视觉参数 ──
    ev = EMOTION_VISUAL.get(em, EMOTION_VISUAL['Neutral'])
    
    # ── BPM → 速度 ──
    speed = bpm_to_speed(bpm)
    beat_interval = bpm_to_motion_interval(bpm)
    
    # ── 颜色板生成 ──
    primary = key_colors[0]
    secondary = key_colors[1]
    accent = key_colors[2] if len(key_colors) > 2 else key_colors[0]
    
    # 大调用饱和度高的色，小调用低饱和度的暗色
    if mode == 'm':
        primary = _desaturate(primary, 0.4)
        secondary = _desaturate(secondary, 0.4)
    
    # ── 节拍闪烁时间表 ──
    beats = beat.get('beats', [])
    
    # ── 段落参数 ──
    sections = seg.get('segs', [])
    
    return {
        # 基础
        'bpm': round(bpm, 2),
        'beat_interval': round(beat_interval, 3),
        'key': key_name,
        'mode': mode,
        'mode_cn': '大调' if mode == 'M' else '小调',
        'emotion': em,
        'emotion_cn': em_cn,
        'segments_k': seg.get('k', len(sections)),
        
        # 颜色
        'colors': {
            'primary': primary,
            'secondary': secondary,
            'accent': accent,
            'palette': key_colors,
        },
        
        # 速度与节奏
        'speed': round(speed, 3),
        'beat_times': [round(float(t), 3) for t in beats],
        'beat_count': len(beats),
        
        # 视觉参数
        'brightness': round(energy_to_brightness(energy_avg, energy_max), 3),
        'saturation': round(energy_to_saturation(energy_avg, energy_avg), 3),
        'blur': round(energy_to_blur(energy_avg, energy_avg), 3),
        'contrast': round(float(ev['contrast'] == 'maximum' and 1.0 or ev['contrast'] == 'high' and 0.8 or 0.5), 2),
        'glow': round(float(ev['glow_intensity']), 2),
        
        # 风格
        'palette_style': ev['palette'],
        'motion_style': ev['motion'],
        'motion_amplitude': round(float(ev['motion_amplitude']), 2),
        'motion_interval': round(beat_interval, 3),
        'particle_density': ev['particle_density'],
        'beatsync_flash': ev['beatsync_flash'],
        
        # 段落
        'sections': [
            {
                'start': s['s'],
                'end': s['e'],
                'duration': s['d'],
            }
            for s in sections
        ],
        
        # 能量曲线
        'energy_curve': energy_vals,
        'energy_avg': round(float(energy_avg), 4),
        'energy_peak': round(float(energy_max), 4),
        
        # VJ 指令摘要（用于调试/日志）
        'vj_summary': _make_summary(bpm, key_name, mode, em, ev, speed),
    }


def _desaturate(hex_color: str, amount: float = 0.5) -> str:
    """降低颜色饱和度"""
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    gray = 0.299*r + 0.587*g + 0.114*b
    r2 = r + (gray - r) * amount
    g2 = g + (gray - g) * amount
    b2 = b + (gray - b) * amount
    return '#{:02X}{:02X}{:02X}'.format(
        int(r2*255), int(g2*255), int(b2*255))


def _make_summary(bpm, key_name, mode, em, ev, speed) -> str:
    mode_cn = '大调' if mode == 'M' else '小调'
    return (
        f"BPM {bpm:.0f} / {key_name}{mode_cn} / "
        f"情绪:{em} / 速度:{speed:.0%} / "
        f"风格:{ev['palette']}+{ev['motion']}"
    )


# ─── 快速测试 ──────────────────────────────────────────────
if __name__ == '__main__':
    import sys, json
    from audio_analysis_module import full_analysis
    
    test_audio = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test_beat_120bpm.wav'
    analysis = full_analysis(test_audio)
    vj = map_analysis_to_vj(analysis)
    
    print("=== VJ Visual Parameters ===")
    print(f"BPM:        {vj['bpm']}")
    print(f"Key:       {vj['key']}{vj['mode_cn']}")
    print(f"Emotion:   {vj['emotion']} ({vj['emotion_cn']})")
    print(f"Speed:     {vj['speed']:.1%}")
    print(f"Colors:    {vj['colors']['primary']} / {vj['colors']['secondary']}")
    print(f"Palette:   {vj['palette_style']}")
    print(f"Motion:    {vj['motion_style']} @ {vj['motion_interval']:.3f}s/beat")
    print(f"Glow:      {vj['glow']}")
    print(f"Flash:     {'✓' if vj['beatsync_flash'] else '✗'}")
    print(f"Segments:  {vj['segments_k']}")
    print(f"Brightness:{vj['brightness']}")
    print()
    print("VJ Summary:", vj['vj_summary'])
