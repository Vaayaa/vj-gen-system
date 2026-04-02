#!/usr/bin/env python3
"""
VJ-Gen 音频分析示例

演示如何使用音频分析管线：
1. 完整音频分析（BPM、节拍、段落、能量）
2. 人声分离
3. 管线构建器使用
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.audio.base import AudioAnalysisParams
from src.adapters.audio.librosa_adapter import LibrosaAdapter
from src.adapters.audio.demucs_adapter import DemucsAdapter
from src.adapters.base import AdapterConfig
from src.pipelines.audio_pipeline import (
    AudioPipeline,
    AudioPipelineBuilder,
    analyze_audio,
)


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_analysis_result(result):
    """打印分析结果"""
    print(f"\n📊 分析结果:")
    print(f"  • BPM: {result.bpm}")
    print(f"  • 时长: {result.duration:.2f}秒")
    print(f"  • 拍号: {result.time_signature}")
    print(f"  • 节拍数: {len(result.beats)}")
    print(f"  • 段落数: {len(result.sections)}")
    print(f"  • 能量点数: {len(result.energy_curve)}")
    
    if result.vocal_path:
        print(f"\n🎤 人声分离结果:")
        print(f"  • 人声: {result.vocal_path}")
        print(f"  • 伴奏: {result.instrumental_path}")


def print_sections(sections):
    """打印段落详情"""
    print(f"\n📍 段落结构:")
    for i, sec in enumerate(sections):
        duration = sec.end - sec.start
        print(f"  {i+1}. [{sec.start:.1f}s - {sec.end:.1f}s] ({duration:.1f}s)")
        print(f"     类型: {sec.type.value}, 能量: {sec.energy:.2f}")
        if sec.mood:
            print(f"     情绪: {', '.join(sec.mood)}")


def print_beats(beats, limit=20):
    """打印节拍详情"""
    print(f"\n🥁 节拍信息 (前 {limit} 个):")
    for i, beat in enumerate(beats[:limit]):
        print(f"  {i+1}. {beat.timestamp:.3f}s | {beat.beat_type} | 强度: {beat.strength:.2f}")
    if len(beats) > limit:
        print(f"  ... 还有 {len(beats) - limit} 个节拍")


def print_energy_curve(energy_curve, limit=10):
    """打印能量曲线摘要"""
    if not energy_curve:
        print("\n⚡ 能量曲线: 无数据")
        return
    
    energies = [e.energy for e in energy_curve]
    avg = sum(energies) / len(energies)
    max_e = max(energies)
    min_e = min(energies)
    
    print(f"\n⚡ 能量曲线摘要:")
    print(f"  • 数据点数: {len(energy_curve)}")
    print(f"  • 平均能量: {avg:.3f}")
    print(f"  • 最大能量: {max_e:.3f}")
    print(f"  • 最小能量: {min_e:.3f}")
    
    # 显示前几个点
    print(f"\n  前 {limit} 个能量点:")
    for i, ep in enumerate(energy_curve[:limit]):
        bar = "█" * int(ep.energy * 20)
        print(f"    {ep.timestamp:7.3f}s | {bar:<20} {ep.energy:.3f}")


async def demo_basic_analysis(pipeline: AudioPipeline, audio_path: str):
    """基础分析演示"""
    print_section("基础音频分析")
    
    params = AudioAnalysisParams(
        compute_energy=True,
        compute_sections=True,
        compute_vocal=False,  # 基础分析不分离人声
    )
    
    result = await pipeline.analyze_only(audio_path, params)
    
    print_analysis_result(result)
    print_sections(result.sections)
    print_beats(result.beats)
    print_energy_curve(result.energy_curve)


async def demo_full_pipeline(pipeline: AudioPipeline, audio_path: str):
    """完整管线演示（包含人声分离）"""
    print_section("完整分析 + 人声分离")
    
    print("\n⏳ 注意: 人声分离可能需要较长时间（取决于音频长度）...")
    
    result = await pipeline.process(
        audio_path,
        separate_vocals=True,
    )
    
    print_analysis_result(result)


async def demo_pipeline_builder():
    """管线构建器演示"""
    print_section("管线构建器")
    
    # 使用构建器创建管线
    pipeline = (
        AudioPipelineBuilder()
        .output_dir("./output/demo")
        .compute_energy(True)
        .compute_sections(True)
        .compute_vocals(False)
        .build()
    )
    
    print("✅ 使用构建器创建管线成功")
    print(f"  • 输出目录: {pipeline.output_dir}")
    
    # 健康检查
    health = await pipeline.health_check()
    print(f"\n🏥 健康检查:")
    for adapter, status in health.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {adapter}: {'健康' if status else '异常'}")


async def demo_adapter_direct():
    """直接使用适配器演示"""
    print_section("直接使用适配器")
    
    config = AdapterConfig(provider="local", model="librosa")
    adapter = LibrosaAdapter(config)
    
    print(f"✅ 创建适配器: {adapter}")
    print(f"  • 提供商: {adapter.provider}")
    print(f"  • 模型: {adapter.model}")
    print(f"  • 支持格式: {adapter.supported_formats}")
    
    capabilities = adapter.get_capabilities()
    print(f"\n📋 适配器能力:")
    for cap in capabilities:
        print(f"  • {cap.name}: {cap.description}")


async def demo_convenience_function(audio_path: str):
    """便捷函数演示"""
    print_section("便捷函数")
    
    print("使用 analyze_audio() 便捷函数...")
    result = await analyze_audio(audio_path)
    
    print_analysis_result(result)


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("  VJ-Gen 音频分析演示")
    print("="*60)
    
    # 查找示例音频文件
    sample_audio = None
    search_paths = [
        "./test_audio.mp3",
        "./samples/audio.mp3",
        "./examples/sample.mp3",
        "/tmp/test_audio.mp3",
    ]
    
    for path in search_paths:
        if Path(path).exists():
            sample_audio = path
            break
    
    if not sample_audio:
        print("\n⚠️  未找到示例音频文件")
        print("   跳过需要音频文件的演示")
        print("\n   您可以：")
        print("   1. 准备一个 MP3 文件放到项目根目录")
        print("   2. 修改 demo 中的 sample_audio 变量指向您的音频文件")
        
        # 仍然运行不需要音频的演示
        await demo_adapter_direct()
        await demo_pipeline_builder()
        return
    
    print(f"\n🎵 使用音频文件: {sample_audio}")
    
    # 创建管线
    pipeline = AudioPipeline.create_default("./output/demo")
    
    # 运行演示
    await demo_adapter_direct()
    await demo_basic_analysis(pipeline, sample_audio)
    await demo_pipeline_builder()
    
    # 以下演示需要较长时间，跳过
    # await demo_full_pipeline(pipeline, sample_audio)
    # await demo_convenience_function(sample_audio)
    
    print("\n" + "="*60)
    print("  演示完成!")
    print("="*60)
    print("\n💡 提示:")
    print("   • 运行完整分析请调用: pipeline.process(audio_path, separate_vocals=True)")
    print("   • 使用构建器请参考: AudioPipelineBuilder")
    print("   • 便捷函数: analyze_audio(audio_path)")


if __name__ == "__main__":
    asyncio.run(main())
