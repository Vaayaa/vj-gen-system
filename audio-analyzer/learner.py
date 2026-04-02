#!/usr/bin/env python3
"""
VJ-Gen 音频分析学习系统
记录用户修正，自动学习提升分段准确性
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

LEARNING_DIR = Path(__file__).parent
FEEDBACK_FILE = LEARNING_DIR / "feedback.json"

def load_feedback():
    """加载反馈数据"""
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, 'r') as f:
            return json.load(f)
    return {"feedbacks": [], "corrections": [], "songPatterns": []}

def save_feedback(data):
    """保存反馈数据"""
    with open(FEEDBACK_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_feedback(audio_hash, duration, detected_sections, user_sections):
    """
    添加用户反馈
    audio_hash: 音频指纹(基于时长+BPM+能量)
    detected_sections: 系统检测的段落
    user_sections: 用户手动修正的段落
    """
    data = load_feedback()
    
    # 计算修正比例
    if len(detected_sections) > 0:
        correction_rate = len(user_sections) / len(detected_sections)
    else:
        correction_rate = 1.0
    
    feedback = {
        "timestamp": datetime.now().isoformat(),
        "audio_hash": audio_hash,
        "duration": duration,
        "detected_count": len(detected_sections),
        "user_count": len(user_sections),
        "correction_rate": correction_rate,
        "sections": user_sections
    }
    
    data["feedbacks"].append(feedback)
    
    # 只保留最近100条
    data["feedbacks"] = data["feedbacks"][-100:]
    
    save_feedback(data)
    return feedback

def add_correction(audio_hash, section_index, detected_start, detected_end, user_start, user_end, section_type):
    """记录单个段落的修正"""
    data = load_feedback()
    
    correction = {
        "timestamp": datetime.now().isoformat(),
        "audio_hash": audio_hash,
        "section_index": section_index,
        "detected": {"start": detected_start, "end": detected_end},
        "user": {"start": user_start, "end": user_end},
        "type": section_type
    }
    
    data["corrections"].append(correction)
    
    # 分析修正模式
    analyze_patterns(data)
    
    save_feedback(data)
    return correction

def analyze_patterns(data):
    """分析修正模式，优化检测算法"""
    corrections = data.get("corrections", [])
    
    if len(corrections) < 5:
        return
    
    # 分析每种段落类型的平均时长
    type_durations = {}
    for c in corrections:
        sec_type = c.get("type")
        user_dur = c["user"]["end"] - c["user"]["start"]
        if sec_type not in type_durations:
            type_durations[sec_type] = []
        type_durations[sec_type].append(user_dur)
    
    # 计算平均值
    avg_durations = {}
    for sec_type, durations in type_durations.items():
        if durations:
            avg_durations[sec_type] = sum(durations) / len(durations)
    
    data["songPatterns"] = avg_durations
    save_feedback(data)

def get_learned_patterns():
    """获取学习到的模式"""
    data = load_feedback()
    return data.get("songPatterns", {})

def get_statistics():
    """获取统计信息"""
    data = load_feedback()
    return {
        "total_feedbacks": len(data.get("feedbacks", [])),
        "total_corrections": len(data.get("corrections", [])),
        "learned_patterns": len(data.get("songPatterns", {})),
        "patterns": data.get("songPatterns", {})
    }

def generate_audio_hash(duration, bpm, energy):
    """生成音频指纹"""
    raw = f"{duration:.1f}_{bpm}_{energy:.1f}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]

if __name__ == "__main__":
    # 测试
    print("=== 学习系统统计 ===")
    stats = get_statistics()
    print(f"反馈数量: {stats['total_feedbacks']}")
    print(f"修正数量: {stats['total_corrections']}")
    print(f"学习模式: {stats['learned_patterns']}")
    print(f"模式详情: {stats['patterns']}")
