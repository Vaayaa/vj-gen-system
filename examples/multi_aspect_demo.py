#!/usr/bin/env python3
"""
多画幅渲染示例
演示如何使用 MultiAspectRenderer 批量渲染多个画幅版本
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.render import (
    AspectRatio,
    FillStrategy,
    PRESET_PROFILES,
    RenderProfile,
    get_all_presets,
)
from src.services.multi_aspect_renderer import MultiAspectRenderer


def create_sample_profile(
    name: str,
    width: int,
    height: int,
    aspect_ratio: str,
    fps: int = 30,
    output_format: str = "mp4"
) -> RenderProfile:
    """创建自定义渲染配置"""
    return RenderProfile(
        name=name,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        fps=fps,
        output_format=output_format,
    )


def demo_preset_profiles():
    """演示预设配置"""
    print("\n" + "=" * 60)
    print("预设画幅配置")
    print("=" * 60)

    for name, profile in PRESET_PROFILES.items():
        print(f"\n{name}:")
        print(f"  名称: {profile.name}")
        print(f"  分辨率: {profile.width}x{profile.height}")
        print(f"  画幅: {profile.aspect_ratio}")
        print(f"  帧率: {profile.fps}")
        print(f"  编码器: {profile.codec}")
        print(f"  CRF: {profile.crf}")


def demo_custom_profile():
    """演示自定义配置"""
    print("\n" + "=" * 60)
    print("自定义画幅配置")
    print("=" * 60)

    # 创建自定义竖屏配置
    vertical_9_16 = create_sample_profile(
        name="竖屏9:16",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        fps=30,
    )
    print(f"\n自定义竖屏配置:")
    print(f"  名称: {vertical_9_16.name}")
    print(f"  分辨率: {vertical_9_16.width}x{vertical_9_16.height}")
    print(f"  画幅: {vertical_9_16.aspect_ratio}")

    # 创建抖音风格配置
    douyin_profile = create_sample_profile(
        name="抖音竖屏",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        fps=30,
        output_format="mp4",
    )
    print(f"\n抖音风格配置:")
    print(f"  名称: {douyin_profile.name}")
    print(f"  分辨率: {douyin_profile.width}x{douyin_profile.height}")
    print(f"  画幅: {douyin_profile.aspect_ratio}")

    return [vertical_9_16, douyin_profile]


def demo_batch_render(input_video: str, output_dir: str):
    """
    演示批量渲染

    Args:
        input_video: 输入视频路径
        output_dir: 输出目录
    """
    print("\n" + "=" * 60)
    print("批量渲染演示")
    print("=" * 60)

    # 检查输入视频是否存在
    if not os.path.exists(input_video):
        print(f"\n⚠️  警告: 输入视频不存在: {input_video}")
        print("将演示配置生成，不执行实际渲染")
        print("\n可用的渲染配置:")

        renderer = MultiAspectRenderer()
        for name, profile in PRESET_PROFILES.items():
            print(f"  - {name}: {profile.width}x{profile.height} ({profile.aspect_ratio})")
        return

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 创建渲染器
    renderer = MultiAspectRenderer(base_video=input_video)

    # 选择要渲染的配置
    profiles = [
        PRESET_PROFILES["landscape_16_9"],
        PRESET_PROFILES["portrait_9_16"],
        PRESET_PROFILES["square_1_1"],
    ]

    print(f"\n输入视频: {input_video}")
    print(f"输出目录: {output_dir}")
    print(f"将渲染 {len(profiles)} 个画幅版本:")
    for p in profiles:
        print(f"  - {p.name}: {p.width}x{p.height}")

    # 执行批量渲染
    print("\n开始渲染...")
    results = renderer.render_all_profiles(
        profiles,
        output_dir,
        use_smart_crop=False,  # 使用简单中心裁切
    )

    # 输出结果
    print("\n渲染结果:")
    for name, path in results.items():
        status = "✓" if path and os.path.exists(path) else "✗"
        print(f"  {status} {name}: {path or '失败'}")

    # 显示状态摘要
    status = renderer.get_render_status()
    print(f"\n状态摘要: {status}")


def demo_single_render(
    input_video: str,
    output_video: str,
    width: int,
    height: int,
    aspect_ratio: str
):
    """
    演示单个渲染

    Args:
        input_video: 输入视频路径
        output_video: 输出视频路径
        width: 目标宽度
        height: 目标高度
        aspect_ratio: 目标画幅
    """
    print("\n" + "=" * 60)
    print("单个画幅渲染演示")
    print("=" * 60)

    if not os.path.exists(input_video):
        print(f"\n⚠️  警告: 输入视频不存在: {input_video}")
        return

    # 创建渲染配置
    profile = RenderProfile(
        name=f"custom_{width}x{height}",
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
    )

    print(f"\n输入视频: {input_video}")
    print(f"输出视频: {output_video}")
    print(f"目标分辨率: {width}x{height}")
    print(f"目标画幅: {aspect_ratio}")

    # 创建渲染器并执行
    renderer = MultiAspectRenderer()
    try:
        result = renderer.render_single(
            input_video,
            profile,
            output_video,
            use_smart_crop=False
        )
        print(f"\n✓ 渲染完成: {result}")
    except Exception as e:
        print(f"\n✗ 渲染失败: {e}")


def demo_smart_cropper(input_video: str):
    """
    演示智能裁切

    Args:
        input_video: 输入视频路径
    """
    print("\n" + "=" * 60)
    print("智能裁切演示")
    print("=" * 60)

    if not os.path.exists(input_video):
        print(f"\n⚠️  警告: 输入视频不存在: {input_video}")
        return

    from src.services.cropper import SmartCropper

    print(f"\n输入视频: {input_video}")

    # 创建裁切器
    cropper = SmartCropper(model="center")  # 使用中心检测，不依赖 YOLO

    # 找主体
    print("\n检测画面主体...")
    try:
        box = cropper.find_main_subject(input_video, sample_interval=2.0)
        if box:
            print(f"检测到主体: x={box.x}, y={box.y}, w={box.width}, h={box.height}")
            print(f"中心点: ({box.center_x}, {box.center_y})")
            print(f"置信度: {box.confidence:.2f}")
        else:
            print("未检测到主体")
    except Exception as e:
        print(f"检测失败: {e}")

    # 计算裁切区域
    print("\n计算裁切区域...")
    info = renderer._get_video_info(input_video) if 'renderer' in dir() else None
    if info:
        print(f"视频分辨率: {info['width']}x{info['height']}")


def main():
    parser = argparse.ArgumentParser(
        description="多画幅渲染示例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --demo-presets                    # 显示预设配置
  %(prog)s --demo-custom                      # 显示自定义配置
  %(prog)s --input video.mp4 --output ./out   # 批量渲染
  %(prog)s --single --input video.mp4 --output out.mp4 --width 1080 --height 1920 --aspect 9:16
        """
    )

    parser.add_argument("--demo-presets", action="store_true", help="显示预设配置")
    parser.add_argument("--demo-custom", action="store_true", help="显示自定义配置")
    parser.add_argument("--demo-cropper", action="store_true", help="演示智能裁切")

    parser.add_argument("--input", "-i", help="输入视频路径")
    parser.add_argument("--output", "-o", default="./output", help="输出目录")
    parser.add_argument("--single", action="store_true", help="单个渲染模式")
    parser.add_argument("--width", type=int, default=1920, help="目标宽度")
    parser.add_argument("--height", type=int, default=1080, help="目标高度")
    parser.add_argument("--aspect", default="16:9", help="目标画幅 (16:9, 9:16, 1:1)")

    args = parser.parse_args()

    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n--- 快速演示 ---")
        demo_preset_profiles()
        demo_custom_profile()
        return

    # 执行演示或渲染
    if args.demo_presets:
        demo_preset_profiles()

    if args.demo_custom:
        demo_custom_profile()

    if args.demo_cropper and args.input:
        demo_smart_cropper(args.input)

    if args.input:
        if args.single:
            output_path = args.output if args.output.endswith(".mp4") else f"{args.output}.mp4"
            demo_single_render(args.input, output_path, args.width, args.height, args.aspect)
        else:
            demo_batch_render(args.input, args.output)


if __name__ == "__main__":
    main()
