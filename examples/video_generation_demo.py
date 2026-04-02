"""
VJ-Gen 视频生成示例
演示如何使用图像和视频生成管线
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.image.base import ImageGenAdapter, ImageGenParams
from src.adapters.image.sd_adapter import StableDiffusionAdapter
from src.adapters.image.dalle_adapter import DalleAdapter
from src.adapters.video.base import VideoGenParams
from src.adapters.video.runway_adapter import RunwayAdapter
from src.adapters.video.kling_adapter import KlingAdapter
from src.adapters.video.topaz_adapter import TopazVideoAdapter
from src.adapters.base import AdapterConfig
from src.pipelines.image_pipeline import ImagePipeline
from src.pipelines.video_pipeline import VideoPipeline
from src.core.router import SimpleModelRouter, QualityAwareRouter
from src.models.schemas import (
    ShotScriptItem, ShotScript, SectionType, MotionDesign,
    CameraBehavior, TransitionHint, AspectRatio, RenderProfile,
)


def create_sample_shot_scripts() -> list[ShotScriptItem]:
    """创建示例镜头脚本"""
    return [
        ShotScriptItem(
            id="shot_001",
            time_start=0.0,
            time_end=5.0,
            section_type=SectionType.INTRO,
            lyric="The journey begins",
            audio_emotion="calm",
            energy=0.3,
            visual_style="cinematic, ethereal",
            visual_prompt="A mystical forest at dawn, soft golden light filtering through ancient trees, fog rolling gently, cinematic atmosphere",
            motion_design=MotionDesign(primary_motion="none", motion_intensity=0.2),
            color_palette=["#1a1a2e", "#eab308", "#f8fafc"],
            camera_behavior=CameraBehavior.STATIC,
            transition_hint=TransitionHint.FADE,
        ),
        ShotScriptItem(
            id="shot_002",
            time_start=5.0,
            time_end=12.0,
            section_type=SectionType.CHORUS,
            lyric="Rising up, we break through",
            audio_emotion="climax",
            energy=0.9,
            visual_style="dynamic, powerful",
            visual_prompt="Powerful ocean waves crashing against cliffs at sunset, dramatic lighting, spray particles, epic scale",
            motion_design=MotionDesign(primary_motion="waves crashing", motion_intensity=0.9),
            color_palette=["#0369a1", "#f97316", "#fef3c7"],
            camera_behavior=CameraBehavior.DOLLY,
            transition_hint=TransitionHint.CUT,
        ),
        ShotScriptItem(
            id="shot_003",
            time_start=12.0,
            time_end=18.0,
            section_type=SectionType.DROP,
            lyric="Feel the bass",
            audio_emotion="bright",
            energy=1.0,
            visual_style="neon, vibrant",
            visual_prompt="Neon-lit cyberpunk cityscape at night, holographic advertisements, rain-slicked streets reflecting colorful lights",
            motion_design=MotionDesign(primary_motion="car lights trails", motion_intensity=0.8),
            color_palette=["#ec4899", "#06b6d4", "#7c3aed"],
            camera_behavior=CameraBehavior.ORBIT,
            transition_hint=TransitionHint.GLITCH,
        ),
        ShotScriptItem(
            id="shot_004",
            time_start=18.0,
            time_end=25.0,
            section_type=SectionType.OUTRO,
            lyric="Until we meet again",
            audio_emotion="calm",
            energy=0.2,
            visual_style="peaceful, nostalgic",
            visual_prompt="Serene mountain lake at twilight, perfect reflections of snowy peaks, fireflies beginning to glow, peaceful atmosphere",
            motion_design=MotionDesign(primary_motion="fireflies", motion_intensity=0.3),
            color_palette=["#0f172a", "#334155", "#f59e0b"],
            camera_behavior=CameraBehavior.RISE,
            transition_hint=TransitionHint.DISSOLVE,
        ),
    ]


async def demo_image_pipeline():
    """演示图像生成管线"""
    print("\n" + "=" * 60)
    print("图像生成管线演示")
    print("=" * 60)

    # 创建配置
    sd_config = AdapterConfig(
        provider="stability_ai",
        model="sd-xl",
        api_key=os.getenv("STABILITY_API_KEY", "your-api-key"),
        api_base="https://api.stability.ai/v1",
        extra_params={"output_dir": "/tmp/vj-gen/images"},
    )

    dalle_config = AdapterConfig(
        provider="openai",
        model="dall-e-3",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        extra_params={"output_dir": "/tmp/vj-gen/images"},
    )

    # 创建适配器（实际使用时需要有效的 API key）
    sd_adapter = StableDiffusionAdapter(sd_config)
    dalle_adapter = DalleAdapter(dalle_config)

    # 创建路由器
    router = QualityAwareRouter()

    # 创建图像管线
    image_pipeline = ImagePipeline(
        adapters=[sd_adapter, dalle_adapter],
        router=router,
        output_dir="/tmp/vj-gen/keyframes",
    )

    # 创建示例脚本
    shot_scripts = create_sample_shot_scripts()

    print(f"\n准备生成 {len(shot_scripts)} 个关键帧...")

    # 生成关键帧
    # 注意：由于没有真实 API key，这里演示流程
    print("\n关键帧生成参数：")
    for script in shot_scripts:
        print(f"\n  [{script.id}] {script.section_type.value}")
        print(f"    视觉风格: {script.visual_style}")
        print(f"    Prompt: {script.visual_prompt[:80]}...")

    # 演示单张图像生成（需要真实 API key）
    # results = await image_pipeline.generate_keyframes(shot_scripts, quality="high")

    # print("\n生成结果：")
    # for i, result in enumerate(results):
    #     if result.success:
    #         print(f"  ✓ Shot {i+1}: {result.data}")
    #     else:
    #         print(f"  ✗ Shot {i+1}: {result.error}")

    # 获取适配器状态
    print("\n适配器统计：")
    stats = image_pipeline.get_adapter_stats()
    for name, stat in stats.items():
        print(f"  {name}: {stat.get('total_calls', 0)} calls")

    print("\n图像管线演示完成！")


async def demo_video_pipeline():
    """演示视频生成管线"""
    print("\n" + "=" * 60)
    print("视频生成管线演示")
    print("=" * 60)

    # 创建配置
    runway_config = AdapterConfig(
        provider="runway",
        model="pika-2.0",
        api_key=os.getenv("RUNWAY_API_KEY", "your-api-key"),
        api_base="https://api.dev.pika.run/v1",
        extra_params={"output_dir": "/tmp/vj-gen/videos"},
    )

    kling_config = AdapterConfig(
        provider="kling",
        model="kling-1.5",
        api_key=os.getenv("KLING_API_KEY", "your-api-key"),
        api_base="https://api.kling.ai/v1",
        extra_params={"output_dir": "/tmp/vj-gen/videos"},
    )

    topaz_config = AdapterConfig(
        provider="topaz",
        model="video-ai",
        api_key=os.getenv("TOPAZ_API_KEY", "your-api-key"),
        api_base="https://api.topazlabs.io/v1",
        extra_params={"output_dir": "/tmp/vj-gen/upscaled"},
    )

    # 创建适配器
    runway_adapter = RunwayAdapter(runway_config)
    kling_adapter = KlingAdapter(kling_config)
    topaz_adapter = TopazVideoAdapter(topaz_config)

    # 创建路由器
    router = SimpleModelRouter({
        "video_gen": "runway",
        "text_to_video": "kling",
        "image_upscale": "topaz",
    })

    # 创建视频管线
    video_pipeline = VideoPipeline(
        adapters=[runway_adapter, kling_adapter],
        router=router,
        upscale_adapter=topaz_adapter,
        output_dir="/tmp/vj-gen/clips",
    )

    # 创建示例脚本
    shot_scripts = create_sample_shot_scripts()

    print(f"\n准备生成 {len(shot_scripts)} 个视频片段...")
    print("\n视频片段参数：")
    for script in shot_scripts:
        duration = script.time_end - script.time_start
        print(f"\n  [{script.id}] {script.section_type.value} ({duration}s)")
        print(f"    相机运动: {script.camera_behavior.value}")
        print(f"    运动强度: {script.motion_design.motion_intensity}")

    # 演示视频生成流程
    # 模拟关键帧路径（实际由图像管线生成）
    keyframes = [f"/tmp/vj-gen/keyframes/kf_{i:03d}.png" for i in range(len(shot_scripts))]

    print(f"\n关键帧路径: {keyframes}")

    # 生成视频片段（需要真实 API key）
    # clips = await video_pipeline.generate_clips(
    #     keyframes=keyframes,
    #     shot_scripts=shot_scripts,
    #     quality="high",
    #     enable_upscale=True,
    # )

    # print("\n生成结果：")
    # for i, result in enumerate(clips):
    #     if result.success:
    #         clip = result.data
    #         print(f"  ✓ Clip {i+1}: {clip.video_path} ({clip.metadata.duration}s)")
    #     else:
    #         print(f"  ✗ Clip {i+1}: {result.error}")

    # 获取适配器状态
    print("\n适配器统计：")
    stats = video_pipeline.get_adapter_stats()
    for name, stat in stats.items():
        print(f"  {name}: {stat.get('total_calls', 0)} calls")

    print("\n视频管线演示完成！")


async def demo_end_to_end():
    """端到端演示：从音频到最终视频"""
    print("\n" + "=" * 60)
    print("端到端视频生成演示")
    print("=" * 60)

    # 1. 设置管线
    print("\n步骤 1: 初始化管线...")

    sd_config = AdapterConfig(
        provider="stability_ai",
        model="sd-xl",
        api_key=os.getenv("STABILITY_API_KEY", "your-api-key"),
        extra_params={"output_dir": "/tmp/vj-gen/images"},
    )

    runway_config = AdapterConfig(
        provider="runway",
        model="pika-2.0",
        api_key=os.getenv("RUNWAY_API_KEY", "your-api-key"),
        extra_params={"output_dir": "/tmp/vj-gen/videos"},
    )

    topaz_config = AdapterConfig(
        provider="topaz",
        model="video-ai",
        api_key=os.getenv("TOPAZ_API_KEY", "your-api-key"),
        extra_params={"output_dir": "/tmp/vj-gen/upscaled"},
    )

    sd_adapter = StableDiffusionAdapter(sd_config)
    runway_adapter = RunwayAdapter(runway_config)
    topaz_adapter = TopazVideoAdapter(topaz_config)

    image_router = QualityAwareRouter()
    video_router = SimpleModelRouter()

    image_pipeline = ImagePipeline(
        adapters=[sd_adapter],
        router=image_router,
    )

    video_pipeline = VideoPipeline(
        adapters=[runway_adapter],
        router=video_router,
        upscale_adapter=topaz_adapter,
    )

    # 2. 创建镜头脚本（通常由 LLM 根据音频分析生成）
    print("\n步骤 2: 生成镜头脚本...")
    shot_scripts = create_sample_shot_scripts()
    print(f"  生成了 {len(shot_scripts)} 个镜头")

    # 3. 生成关键帧
    print("\n步骤 3: 生成关键帧...")
    # keyframe_results = await image_pipeline.generate_keyframes(shot_scripts, quality="high")
    # keyframes = [r.data if r.success else None for r in keyframe_results]
    print("  [模拟] 关键帧生成完成")

    # 4. 生成视频片段
    print("\n步骤 4: 生成视频片段...")
    # clip_results = await video_pipeline.generate_clips(
    #     keyframes=[kf for kf in keyframes if kf],
    #     shot_scripts=shot_scripts,
    #     quality="high",
    #     enable_upscale=True,
    # )
    print("  [模拟] 视频片段生成完成")

    # 5. 组装时间线
    print("\n步骤 5: 组装时间线...")
    print("  [模拟] 时间线组装完成")

    print("\n" + "=" * 60)
    print("端到端演示完成！")
    print("=" * 60)
    print("\n注意: 由于没有真实 API key，以上仅为流程演示。")
    print("要实际运行，请设置以下环境变量：")
    print("  - STABILITY_API_KEY")
    print("  - OPENAI_API_KEY")
    print("  - RUNWAY_API_KEY")
    print("  - KLING_API_KEY")
    print("  - TOPAZ_API_KEY")


async def main():
    """主函数"""
    print("VJ-Gen 视频生成系统演示")
    print("=" * 60)

    # 演示图像管线
    await demo_image_pipeline()

    # 演示视频管线
    await demo_video_pipeline()

    # 端到端演示
    await demo_end_to_end()


if __name__ == "__main__":
    asyncio.run(main())
