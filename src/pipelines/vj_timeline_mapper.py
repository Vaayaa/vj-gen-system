"""
VJ Timeline Mapper — 音频特征 → 视觉参数时间线
================================================

将 BPM/节拍/能量/段落 映射为每帧视觉参数时间线

核心函数:
- map_audio_to_visual(): audio_result → 全局+段落视觉参数
- generate_visual_timeline(): → 每帧参数字典列表
- PALETTES: 调色板定义
"""

import math
from dataclasses import dataclass, field
from typing import Optional

# 调色板定义（按能量/情绪级别）
PALETTES = {
    "deep_tech": {
        "name": "Deep Tech",
        "primary": "#0a0f1a",
        "secondary": "#1a3a5c",
        "accent": "#00d4ff",
        "highlight": "#ff3366",
        "glow": "#00ffaa",
    },
    "energy_peak": {
        "name": "Energy Peak",
        "primary": "#1a0a2e",
        "secondary": "#3d1a5c",
        "accent": "#ff6600",
        "highlight": "#ffff00",
        "glow": "#ff0066",
    },
    "chill": {
        "name": "Chill",
        "primary": "#0d1b2a",
        "secondary": "#1b3a4b",
        "accent": "#48cae4",
        "highlight": "#90e0ef",
        "glow": "#caf0f8",
    },
    "dark": {
        "name": "Dark",
        "primary": "#000000",
        "secondary": "#0a0a0a",
        "accent": "#333333",
        "highlight": "#666666",
        "glow": "#999999",
    },
    "bright": {
        "name": "Bright",
        "primary": "#ffffff",
        "secondary": "#f0f0f0",
        "accent": "#ffdd00",
        "highlight": "#ff8800",
        "glow": "#ff0066",
    },
}


@dataclass
class VisualParams:
    """单个时间点的视觉参数"""
    timestamp: float = 0.0
    duration: float = 1.0
    palette: str = "deep_tech"
    color_intensity: float = 0.5
    brightness: float = 0.5
    animation_speed: float = 1.0
    particle_density: float = 0.5
    particle_speed: float = 0.5
    turbulence: float = 0.3
    scale: float = 1.0
    rotation: float = 0.0
    pulse_strength: float = 0.3
    transition_type: str = "cut"
    transition_duration: float = 0.5
    glow_amount: float = 0.5
    blur_amount: float = 0.0
    chromatic_aberration: float = 0.0
    beat_hit: bool = False
    flash_intensity: float = 0.0
    shake_amount: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "duration": self.duration,
            "palette": self.palette,
            "color_intensity": self.color_intensity,
            "brightness": self.brightness,
            "animation_speed": self.animation_speed,
            "particle_density": self.particle_density,
            "particle_speed": self.particle_speed,
            "turbulence": self.turbulence,
            "scale": self.scale,
            "rotation": self.rotation,
            "pulse_strength": self.pulse_strength,
            "transition_type": self.transition_type,
            "transition_duration": self.transition_duration,
            "glow_amount": self.glow_amount,
            "blur_amount": self.blur_amount,
            "chromatic_aberration": self.chromatic_aberration,
            "beat_hit": self.beat_hit,
            "flash_intensity": self.flash_intensity,
            "shake_amount": self.shake_amount,
        }


@dataclass
class SegmentVisual:
    """单个段落的视觉配置"""
    start: float
    end: float
    section_type: str
    bpm: float
    energy: float
    params: VisualParams = field(default_factory=VisualParams)


class VJVisualMapper:
    """音频特征 → 视觉参数映射器"""

    _ENERGY_PALETTE_MAP = [
        (0.0, "dark"),
        (0.2, "deep_tech"),
        (0.5, "chill"),
        (0.7, "energy_peak"),
        (1.0, "bright"),
    ]

    _SECTION_TRANSITIONS = {
        "intro": "fade",
        "verse": "cut",
        "pre_chorus": "dissolve",
        "chorus": "glitch",
        "drop": "wipe",
        "bridge": "dissolve",
        "outro": "fade",
        "break": "cut",
        "silence": "fade",
    }

    _SECTION_SPEED = {
        "intro": 0.7,
        "verse": 0.9,
        "pre_chorus": 1.1,
        "chorus": 1.3,
        "drop": 1.5,
        "bridge": 0.8,
        "outro": 0.6,
        "break": 1.0,
        "silence": 0.0,
    }

    def _energy_to_palette(self, energy: float) -> str:
        for threshold, palette in self._ENERGY_PALETTE_MAP:
            if energy <= threshold:
                return palette
        return "bright"

    def _normalize_bpm(self, bpm: float) -> float:
        return max(0.0, min(1.0, (bpm - 60) / 140))

    def map_audio(self, audio_result: dict) -> dict:
        """
        将 audio_analysis_module 结果映射为视觉参数

        audio_result 格式:
        {
            'bpm': float,
            'beats': [{'start': float, 'strength': float, 'is_accent': bool}, ...],
            'sections': [{'start': float, 'end': float, 'type': str, 'energy': float}, ...],
            'energy_curve': [{'timestamp': float, 'energy': float}, ...],
            'duration': float,
        }
        """
        bpm = audio_result.get("bpm", 120.0)
        beats = audio_result.get("beats", [])
        sections = audio_result.get("sections", [])
        energy_curve = audio_result.get("energy_curve", [])

        avg_energy = (
            sum(e["energy"] for e in energy_curve) / len(energy_curve)
            if energy_curve else 0.5
        )

        # 全局参数
        global_params = VisualParams(
            timestamp=0.0,
            palette=self._energy_to_palette(avg_energy),
            animation_speed=bpm / 120.0,
            particle_speed=self._normalize_bpm(bpm) * 0.7 + 0.3,
        )

        # 节拍参数
        beat_visuals = []
        for beat in beats:
            strength = beat.get("strength", 0.5)
            is_accent = beat.get("is_accent", strength > 0.7)
            beat_visuals.append(VisualParams(
                timestamp=beat["start"],
                duration=60.0 / bpm if bpm > 0 else 0.5,
                palette=self._energy_to_palette(avg_energy),
                animation_speed=bpm / 120.0,
                beat_hit=is_accent,
                flash_intensity=strength if is_accent else strength * 0.3,
                shake_amount=strength * 0.5 if is_accent else 0.0,
                pulse_strength=strength,
                scale=1.0 + strength * 0.2 if is_accent else 1.0,
                glow_amount=0.3 + strength * 0.5,
                particle_density=strength,
            ))

        # 段落参数
        segment_visuals = []
        for sec in sections:
            sec_type = sec.get("type", "verse")
            sec_energy = sec.get("energy", 0.5)
            sec_start = sec["start"]
            sec_end = sec["end"]
            sec_beats = [b for b in beats if sec_start <= b["start"] < sec_end]
            sec_avg_strength = (
                sum(b.get("strength", 0.5) for b in sec_beats) / len(sec_beats)
                if sec_beats else sec_energy
            )

            segment_visuals.append(SegmentVisual(
                start=sec_start,
                end=sec_end,
                section_type=sec_type,
                bpm=bpm,
                energy=sec_energy,
                params=VisualParams(
                    timestamp=sec_start,
                    duration=sec_end - sec_start,
                    palette=self._energy_to_palette(sec_energy),
                    animation_speed=self._SECTION_SPEED.get(sec_type, 1.0) * (bpm / 120.0),
                    transition_type=self._SECTION_TRANSITIONS.get(sec_type, "cut"),
                    particle_density=sec_avg_strength,
                    brightness=0.3 + sec_energy * 0.5,
                    color_intensity=0.4 + sec_energy * 0.6,
                    turbulence=0.2 + sec_energy * 0.4,
                    glow_amount=0.2 + sec_energy * 0.6,
                    scale=1.0 + (sec_energy - 0.5) * 0.3,
                    pulse_strength=sec_avg_strength,
                ),
            ))

        return {
            "global": global_params,
            "beats": beat_visuals,
            "segments": segment_visuals,
            "bpm": bpm,
            "total_beats": len(beats),
            "total_segments": len(sections),
        }


_mapper = VJVisualMapper()


def map_audio_to_visual(audio_result: dict) -> dict:
    """快捷函数：从 audio_analysis_module 结果映射到视觉参数"""
    return _mapper.map_audio(audio_result)


def generate_visual_timeline(audio_result: dict, fps: int = 60) -> list[dict]:
    """
    生成每帧的视觉参数时间线

    Args:
        audio_result: audio_analysis_module 格式的输出
        fps: 每秒帧数

    Returns:
        每帧的视觉参数字典列表
    """
    visual_map = _mapper.map_audio(audio_result)
    duration = audio_result.get("duration", 30.0)
    bpm = audio_result.get("bpm", 120.0)

    total_frames = int(duration * fps)
    frames = []

    for frame_idx in range(total_frames):
        t = frame_idx / fps

        # 找到当前节拍和下一节拍
        current_beat = None
        next_beat = None
        for beat in visual_map["beats"]:
            if beat.timestamp <= t:
                current_beat = beat
            if beat.timestamp > t and (next_beat is None or beat.timestamp < next_beat.timestamp):
                next_beat = beat

        # 计算节拍内进度
        if current_beat and next_beat:
            progress = (t - current_beat.timestamp) / (next_beat.timestamp - current_beat.timestamp)
            progress = max(0.0, min(1.0, progress))
        else:
            progress = 0.0

        # 脉冲衰减
        if current_beat:
            decay = math.exp(-progress * 4)
            pulse = current_beat.pulse_strength * decay
            flash = current_beat.flash_intensity * decay
        else:
            pulse = 0.0
            flash = 0.0

        # 段落参数
        current_segment = None
        for seg in visual_map["segments"]:
            if seg.start <= t < seg.end:
                current_segment = seg
                break

        if current_segment:
            seg_params = current_segment.params
            base_scale = seg_params.scale
            base_brightness = seg_params.brightness
            base_turbulence = seg_params.turbulence
        else:
            base_scale = 1.0
            base_brightness = 0.5
            base_turbulence = 0.3

        frames.append({
            "frame": frame_idx,
            "timestamp": round(t, 3),
            "scale": round(base_scale + pulse * 0.15, 4),
            "brightness": round(min(1.0, base_brightness + flash * 0.3), 4),
            "turbulence": round(min(1.0, base_turbulence + pulse * 0.2), 4),
            "glow": round(min(1.0, 0.3 + pulse * 0.5), 4),
            "flash": round(flash, 4),
            "shake": round(
                current_beat.shake_amount * math.exp(-progress * 6)
                if current_beat else 0.0, 4
            ),
            "beat_hit": current_beat.beat_hit if current_beat else False,
            "pulse": round(pulse, 4),
            "transition": seg_params.transition_type if current_segment else "cut",
            "particle_density": round(
                current_beat.particle_density if current_beat else 0.5, 2
            ),
        })

    return frames


if __name__ == "__main__":
    # 测试
    test_audio = {
        "bpm": 128.0,
        "duration": 10.0,
        "beats": [
            {"start": 0.0, "strength": 1.0, "is_accent": True},
            {"start": 0.468, "strength": 0.5, "is_accent": False},
            {"start": 0.937, "strength": 0.6, "is_accent": False},
            {"start": 1.406, "strength": 0.7, "is_accent": False},
            {"start": 1.875, "strength": 1.0, "is_accent": True},
        ],
        "energy_curve": [
            {"timestamp": 0.0, "energy": 0.3},
            {"timestamp": 5.0, "energy": 0.8},
            {"timestamp": 10.0, "energy": 0.5},
        ],
        "sections": [
            {"start": 0.0, "end": 4.0, "type": "intro", "energy": 0.3},
            {"start": 4.0, "end": 10.0, "type": "chorus", "energy": 0.8},
        ],
    }

    result = map_audio_to_visual(test_audio)
    print("=== VJ Timeline Mapper Test ===")
    print(f"BPM: {result['bpm']}, Beats: {result['total_beats']}, Segments: {result['total_segments']}")
    print(f"Global palette: {result['global'].palette}, speed: {result['global'].animation_speed:.2f}x")
    for sv in result["segments"]:
        print(f"  [{sv.section_type}] {sv.start:.0f}-{sv.end:.0f}s | {sv.params.palette} | {sv.params.animation_speed:.2f}x | {sv.params.transition_type}")

    timeline = generate_visual_timeline(test_audio, fps=30)
    print(f"\nTimeline: {len(timeline)} frames @ 30fps")
    print(f"  t=0.0s: scale={timeline[0]['scale']}, flash={timeline[0]['flash']}, beat={timeline[0]['beat_hit']}")
    print(f"  t=1.4s: scale={timeline[42]['scale']}, flash={timeline[42]['flash']:.3f}, beat={timeline[42]['beat_hit']}")
