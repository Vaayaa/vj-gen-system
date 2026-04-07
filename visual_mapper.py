#!/usr/bin/env python3
"""
VJ Visual Parameter Mapper v1
===============================
将音频分析结果 → VJ 视觉参数

映射规则：
- BPM → 视觉节奏（亮度闪烁频率、粒子扩散速度）
- 调性(Key/Mode) → 色调（暖/冷、大调明亮/小调深沉）
- 能量(Energy) → 亮度、对比度、粒子密度
- 情绪(Emotion) → 颜色倾向、动效激烈程度
- 段落(Segments) → 镜头切换时机、场景变换
"""
import numpy as np
from typing import Dict, Any, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 调性 → 色彩映射
# ─────────────────────────────────────────────────────────────────────────────
KEY_PALETTES = {
    # 大调 → 偏暖/亮
    'C_M':  {'hue_range': (30, 60),   'sat': 0.75, 'lum': 0.60, 'name': 'Golden'},
    'D_M':  {'hue_range': (40, 70),   'sat': 0.70, 'lum': 0.58, 'name': 'Amber'},
    'E_M':  {'hue_range': (50, 80),   'sat': 0.68, 'lum': 0.62, 'name': 'Citrus'},
    'F_M':  {'hue_range': (70, 100),  'sat': 0.65, 'lum': 0.55, 'name': 'Lime'},
    'G_M':  {'hue_range': (100, 140), 'sat': 0.72, 'lum': 0.50, 'name': 'Emerald'},
    'A_M':  {'hue_range': (140, 180), 'sat': 0.70, 'lum': 0.58, 'name': 'Teal'},
    'B_M':  {'hue_range': (180, 220), 'sat': 0.68, 'lum': 0.55, 'name': 'Azure'},
    # 小调 → 偏冷/深
    'Cm':   {'hue_range': (200, 260), 'sat': 0.80, 'lum': 0.35, 'name': 'Indigo'},
    'Dm':   {'hue_range': (220, 280), 'sat': 0.75, 'lum': 0.38, 'name': 'Violet'},
    'Em':   {'hue_range': (240, 300), 'sat': 0.78, 'lum': 0.40, 'name': 'Purple'},
    'Fm':   {'hue_range': (260, 320), 'sat': 0.72, 'lum': 0.36, 'name': 'Magenta'},
    'Gm':   {'hue_range': (280, 340), 'sat': 0.70, 'lum': 0.42, 'name': 'Rose'},
    'Am':   {'hue_range': (300, 360), 'sat': 0.74, 'lum': 0.38, 'name': 'Crimson'},
    'Bm':   {'hue_range': (330, 20),   'sat': 0.76, 'lum': 0.40, 'name': 'Coral'},
}

EMOTION_PALETTES = {
    'Exciting':  {'hue_bias': +15, 'sat_mult': 1.15, 'lum_mult': 1.10, 'motion_intensity': 1.0},
    'Happy':     {'hue_bias': +20, 'sat_mult': 1.10, 'lum_mult': 1.08, 'motion_intensity': 0.85},
    'Calm':      {'hue_bias': 0,   'sat_mult': 0.85, 'lum_mult': 0.95, 'motion_intensity': 0.40},
    'Tense':     {'hue_bias': -10, 'sat_mult': 1.20, 'lum_mult': 0.90, 'motion_intensity': 0.95},
    'Angry':     {'hue_bias': -15, 'sat_mult': 1.25, 'lum_mult': 0.85, 'motion_intensity': 1.0},
    'Sad':       {'hue_bias': -20, 'sat_mult': 0.70, 'lum_mult': 0.80, 'motion_intensity': 0.30},
    'Neutral':   {'hue_bias': 0,   'sat_mult': 1.0,  'lum_mult': 1.0,  'motion_intensity': 0.50},
}

# ─────────────────────────────────────────────────────────────────────────────
# 能量等级 → 亮度/对比度/粒子密度
# ─────────────────────────────────────────────────────────────────────────────
def energy_to_visuals(e_result: Dict) -> Dict[str, Any]:
    """将能量分析结果映射到视觉参数"""
    rms = np.array(e_result.get('rms', []))
    dyn = e_result.get('dyn', 10)

    # 全局能量 (0-1)
    energy_avg = float(np.mean(rms)) if len(rms) > 0 else 0.5
    energy_max = float(np.max(rms)) if len(rms) > 0 else 0.5
    energy_std = float(np.std(rms)) if len(rms) > 0 else 0.0

    # 亮度：RMS均值映射到0.3-1.0
    brightness = float(np.clip(energy_avg * 4.0, 0.3, 1.0))

    # 对比度：dyn/dynamic range映射
    contrast = float(np.clip(dyn / 20.0, 0.3, 1.0))  # 假设20dB为最大对比度

    # 粒子密度：能量越高粒子越多
    particle_density = float(np.clip(energy_avg * 3.0, 0.2, 1.0))

    # 粒子速度：能量变化大 → 速度更快
    particle_speed = float(np.clip(energy_std * 10.0 + 0.5, 0.3, 1.0))

    # 辉光强度：峰值能量
    glow_intensity = float(np.clip(energy_max * 2.5, 0.4, 1.0))

    return {
        'brightness': round(brightness, 3),
        'contrast': round(contrast, 3),
        'particle_density': round(particle_density, 3),
        'particle_speed': round(particle_speed, 3),
        'glow_intensity': round(glow_intensity, 3),
        'energy_avg': round(float(energy_avg), 4),
        'energy_peak': round(float(energy_max), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# BPM → 节奏参数
# ─────────────────────────────────────────────────────────────────────────────
def bpm_to_rhythm(bpm: float) -> Dict[str, Any]:
    """将BPM映射到视觉节奏参数"""
    # 每拍对应的时间（毫秒）
    beat_ms = 60000.0 / bpm

    # 亮度脉动：跟随beat的亮度变化
    # 高BPM → 更快的闪烁
    pulse_freq = float(bpm / 60.0)  # Hz

    # 子节奏：half beat, quarter beat
    half_beat_ms = beat_ms * 2
    quarter_beat_ms = beat_ms / 2

    # strobe 效果（用于高BPM）
    strobe_threshold = 140
    strobe_on = bpm > strobe_threshold

    # 颜色变换跟随beat
    color_change_per_beat = bpm > 110  # 高于110BPM每拍变色

    # 粒子扩散周期（跟随BPM）
    particle_cycle_ms = beat_ms * 4  # 每4拍一个粒子扩散周期

    return {
        'bpm': round(bpm, 2),
        'beat_ms': round(beat_ms, 1),
        'half_beat_ms': round(half_beat_ms, 1),
        'quarter_beat_ms': round(quarter_beat_ms, 1),
        'pulse_freq_hz': round(pulse_freq, 2),
        'strobe_on': strobe_on,
        'color_change_per_beat': color_change_per_beat,
        'particle_cycle_ms': round(particle_cycle_ms, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 调性 + 情绪 → 颜色参数
# ─────────────────────────────────────────────────────────────────────────────
def key_emotion_to_color(key_result: Dict, em_result: Dict) -> Dict[str, Any]:
    """将调性 + 情绪映射到颜色参数"""
    key_id = key_result.get('key', 'C')
    mode = key_result.get('mode', 'M')
    key_str = f"{key_id}_{mode}"

    emotion = em_result.get('em', 'Neutral')
    em_pal = EMOTION_PALETTES.get(emotion, EMOTION_PALETTES['Neutral'])
    key_pal = KEY_PALETTES.get(key_str, KEY_PALETTES.get(f"{key_id}_M", {
        'hue_range': (0, 360), 'sat': 0.7, 'lum': 0.5, 'name': 'Neutral'
    }))

    # 基础色相范围
    h_min, h_max = key_pal['hue_range']
    h_mid = (h_min + h_max) / 2

    # 情绪影响：偏移色相
    hue_bias = em_pal['hue_bias']
    hue_actual = (h_mid + hue_bias) % 360

    # 饱和度和亮度
    sat = float(np.clip(key_pal['sat'] * em_pal['sat_mult'], 0.3, 1.0))
    lum = float(np.clip(key_pal['lum'] * em_pal['lum_mult'], 0.3, 0.9))

    # 生成互补色（用于高光）
    comp_hue = (hue_actual + 180) % 360

    return {
        'hue': round(hue_actual, 1),
        'hue_min': round(h_min, 1),
        'hue_max': round(h_max, 1),
        'comp_hue': round(comp_hue, 1),
        'saturation': round(sat, 3),
        'lightness': round(lum, 3),
        'motion_intensity': round(em_pal['motion_intensity'], 2),
        'key_name': key_pal['name'],
        'emotion': emotion,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 段落 → 镜头切换
# ─────────────────────────────────────────────────────────────────────────────
def segments_to_cuts(seg_result: Dict) -> List[Dict]:
    """将段落分析结果映射到镜头切换点"""
    segs = seg_result.get('segs', [])
    cuts = []
    for i, seg in enumerate(segs):
        dur = seg.get('d', 0)
        # 镜头长度建议：跟随段时长，但限制在合理范围
        min_clip_dur = 2.0
        max_clip_dur = 8.0
        suggested_dur = float(np.clip(dur, min_clip_dur, max_clip_dur))

        cuts.append({
            'idx': i,
            'start': seg['s'],
            'end': seg['e'],
            'duration': round(dur, 2),
            'suggested_dur': round(suggested_dur, 2),
        })
    return cuts


# ─────────────────────────────────────────────────────────────────────────────
# 情绪 → 动效类型
# ─────────────────────────────────────────────────────────────────────────────
EMOTION_ANIMATIONS = {
    'Exciting': ['particle_burst', 'color_wave', 'zoom_pulse', 'flash_strobe'],
    'Happy':    ['float_bubbles', 'color_wave', 'gentle_zoom'],
    'Calm':     ['slow_particles', 'gradient_shift', 'water_ripple'],
    'Tense':    ['glitch_effect', 'rapid_pulse', 'unstable_zoom'],
    'Angry':    ['fire_particles', 'shake_effect', 'red_surge'],
    'Sad':      ['rain_particles', 'slow_fade', 'blue_shift'],
    'Neutral':   ['ambient_particles', 'subtle_shift'],
}

EMOTION_BACKGROUNDS = {
    'Exciting': ['neon_particles', 'laser_grid', 'strobe_pulse'],
    'Happy':    ['warm_gradient', 'bokeh_lights', 'color_burst'],
    'Calm':     ['deep_gradient', 'slow_mesh', 'fog_particles'],
    'Tense':    ['dark_energy', 'unstable_grid', 'red_glow'],
    'Angry':    ['fire_wall', 'red_particles', 'dark_vortex'],
    'Sad':      ['blue_rain', 'dark_fog', 'deep_space'],
    'Neutral':   ['gradient_wall', 'particle_field'],
}


# ─────────────────────────────────────────────────────────────────────────────
# 主函数：整合所有映射
# ─────────────────────────────────────────────────────────────────────────────
def map_audio_to_visual(
    audio_result: Dict,
    current_time: float = 0.0,
) -> Dict[str, Any]:
    """将完整音频分析结果映射到VJ视觉参数

    Args:
        audio_result: full_analysis() 的返回值
        current_time: 当前播放时间（秒），用于选取时间点对应的能量

    Returns:
        VJ视觉参数字典
    """
    beat = audio_result.get('beat', {})
    seg  = audio_result.get('seg', {})
    key  = audio_result.get('key', {})
    energy = audio_result.get('energy', {})
    em   = audio_result.get('emotion', {})

    # 各维度映射
    rhythm = bpm_to_rhythm(beat.get('bpm', 120))
    color = key_emotion_to_color(key, em)
    energy_vis = energy_to_visuals(energy)
    cuts = segments_to_cuts(seg)
    anims = EMOTION_ANIMATIONS.get(em.get('em', 'Neutral'), EMOTION_ANIMATIONS['Neutral'])
    bgs = EMOTION_BACKGROUNDS.get(em.get('em', 'Neutral'), EMOTION_BACKGROUNDS['Neutral'])

    # 当前时间对应的段落
    current_seg = None
    for c in cuts:
        if c['start'] <= current_time < c['end']:
            current_seg = c
            break
    if current_seg is None and cuts:
        current_seg = cuts[-1]

    # 当前时间点的能量（时间插值）
    rms = np.array(energy.get('rms', []))
    rt = energy.get('t', [])
    current_energy = 0.5
    if len(rms) > 0 and len(rt) > 0 and current_time > 0:
        # 找最近的时间点
        idx = np.argmin(np.abs(np.array(rt) - current_time))
        current_energy = float(np.clip(rms[idx] * 4.0, 0.3, 1.0))

    return {
        'rhythm': rhythm,
        'color': color,
        'energy': energy_vis,
        'current_energy': round(current_energy, 3),
        'cuts': cuts,
        'current_cut': current_seg,
        'animations': anims,
        'backgrounds': bgs,
        'emotion': em.get('em', 'Neutral'),
        'emotion_cn': em.get('em_cn', '中性'),
        'genre': em.get('genre', []),
    }


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import json, sys
    from audio_analysis_module import full_analysis

    audio_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test_beat_120bpm.wav'
    audio = full_analysis(audio_path)
    vis = map_audio_to_visual(audio)

    print("=== VJ Visual Parameters ===")
    print(json.dumps(vis, ensure_ascii=False, indent=2))
