"""
背景填充服务
实现模糊填充、像素延展、粒子延展、镜像填充等策略
"""

import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

import cv2
import numpy as np


class FillStrategy(str, Enum):
    """填充策略"""
    BLUR = "blur"
    EXTEND = "extend"
    PARTICLE = "particle"
    MIRROR = "mirror"


class BackgroundFiller:
    """背景填充器"""

    @staticmethod
    def _get_video_info(video_path: str) -> tuple[int, int, int, float]:
        """获取视频信息"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        cap.release()
        return width, height, int(fps), duration

    @staticmethod
    def _ensure_ffmpeg():
        """确保 ffmpeg 可用"""
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise FileNotFoundError("ffmpeg 未安装或不在 PATH 中")

    @staticmethod
    def blur_fill(
        video_path: str,
        target_width: int,
        target_height: int,
        blur_radius: int = 15,
        output_path: Optional[str] = None
    ) -> str:
        """
        模糊背景填充

        将视频缩放填充到目标尺寸，周围留空部分用模糊背景填充

        Args:
            video_path: 输入视频路径
            target_width: 目标宽度
            target_height: 目标高度
            blur_radius: 模糊半径（像素）
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        BackgroundFiller._ensure_ffmpeg()

        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_blurfill{p.suffix}")

        width, height, fps, _ = BackgroundFiller._get_video_info(video_path)

        # 计算缩放比例，使视频覆盖目标尺寸
        scale_x = target_width / width
        scale_y = target_height / height
        scale = max(scale_x, scale_y)

        scaled_width = int(width * scale)
        scaled_height = int(height * scale)

        # 计算模糊背景大小
        pad_x = max(0, (target_width - scaled_width) // 2)
        pad_y = max(0, (target_height - scaled_height) // 2)

        # 使用 boxblur 滤镜进行模糊填充
        # 方案：先缩放，再加边框模糊
        filter_complex = (
            f"[0:v]scale={scaled_width}:{scaled_height}:force_original_aspect_ratio=increase,"
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"boxblur={blur_radius}:{blur_radius},"
            f"overlay=(W-w)/2:(H-h)/2[v]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:a", "copy",
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg 模糊填充失败: {e.stderr.decode() if e.stderr else str(e)}")

        return output_path

    @staticmethod
    def extend_pixels(
        video_path: str,
        direction: Literal["left", "right", "top", "bottom", "all"] = "all",
        extend_ratio: float = 0.1,
        output_path: Optional[str] = None
    ) -> str:
        """
        像素延展填充

        沿指定方向延展边缘像素来填充空白区域

        Args:
            video_path: 输入视频路径
            direction: 延展方向
            extend_ratio: 延展比例（相对于原尺寸）
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        BackgroundFiller._ensure_ffmpeg()

        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stage}_extend{p.suffix}")

        width, height, fps, duration = BackgroundFiller._get_video_info(video_path)

        # 计算延展像素数
        if direction == "all":
            pad_w = int(width * extend_ratio)
            pad_h = int(height * extend_ratio)
            pads = f"{pad_w}:{pad_h}:{pad_w}:{pad_h}"
        elif direction == "left":
            pad_w = int(width * extend_ratio)
            pads = f"{pad_w}:0:0:0"
        elif direction == "right":
            pad_w = int(width * extend_ratio)
            pads = f"{pad_w}:0:{width}:0"
        elif direction == "top":
            pad_h = int(height * extend_ratio)
            pads = f"0:{pad_h}:0:0"
        elif direction == "bottom":
            pad_h = int(height * extend_ratio)
            pads = f"0:{pad_h}:0:{height}"
        else:
            raise ValueError(f"未知的延展方向: {direction}")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"pad={width + int(width * extend_ratio) * 2}:{height + int(height * extend_ratio) * 2}:{int(width * extend_ratio) if direction in ['left', 'all'] else 0}:{int(height * extend_ratio) if direction in ['top', 'all'] else 0}:edge=extend",
            "-c:a", "copy",
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg 像素延展失败: {e.stderr.decode() if e.stderr else str(e)}")

        return output_path

    @staticmethod
    def particle_extension(
        video_path: str,
        style: Literal["snow", "rain", "stars", "confetti"] = "snow",
        particle_density: float = 0.01,
        output_path: Optional[str] = None
    ) -> str:
        """
        粒子延展填充

        在留白区域添加粒子效果作为背景

        Args:
            video_path: 输入视频路径
            style: 粒子风格
            particle_density: 粒子密度 (0-1)
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        BackgroundFiller._ensure_ffmpeg()

        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_particle{p.suffix}")

        width, height, fps, duration = BackgroundFiller._get_video_info(video_path)

        # 粒子效果使用 FFmpeg 的 frei0r 滤镜或自定义滤镜
        # 这里使用 drawbox 模拟简单粒子效果
        num_particles = int(particle_density * width * height / 1000)

        filter_parts = []
        for i in range(min(num_particles, 100)):  # 限制粒子数量
            import random
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(1, 3)
            opacity = random.uniform(0.3, 0.7)
            filter_parts.append(
                f"drawbox=x={x}:y={y}:w={size}:h={size}:color=white@{opacity}:t=fill"
            )

        if filter_parts:
            filter_str = ",".join(filter_parts)
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", filter_str,
                "-c:a", "copy",
                output_path
            ]
        else:
            # 没有粒子时直接复制
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-c:v", "copy",
                "-c:a", "copy",
                output_path
            ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # 粒子效果失败时，返回原视频
            import shutil
            shutil.copy(video_path, output_path)

        return output_path

    @staticmethod
    def mirror_fill(
        video_path: str,
        direction: Literal["horizontal", "vertical", "both"] = "horizontal",
        output_path: Optional[str] = None
    ) -> str:
        """
        镜像填充

        使用镜像反转来填充留白区域

        Args:
            video_path: 输入视频路径
            direction: 镜像方向
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        BackgroundFiller._ensure_ffmpeg()

        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_mirror{p.suffix}")

        width, height, fps, duration = BackgroundFiller._get_video_info(video_path)

        if direction == "horizontal":
            # 左右镜像拼接
            filter_str = (
                "[0:v]split=2[original][mirrored];"
                "[mirrored]hflip[flipped];"
                "[original][flipped]hstack=inputs=2[out]"
            )
        elif direction == "vertical":
            # 上下镜像拼接
            filter_str = (
                "[0:v]split=2[original][mirrored];"
                "[mirrored]vflip[flipped];"
                "[original][flipped]vstack=inputs=2[out]"
            )
        elif direction == "both":
            # 四象限镜像
            filter_str = (
                "[0:v]split=4[00][01][10][11];"
                "[01]hflip[02];"
                "[10]vflip[12];"
                "[11]hflip[vflip];[vflip]vflip[13];"
                "[00][02][10][13]xtile=2x2:padding=0:margin=0[out]"
            )
        else:
            raise ValueError(f"未知的镜像方向: {direction}")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:a", "copy",
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg 镜像填充失败: {e.stderr.decode() if e.stderr else str(e)}")

        return output_path

    @staticmethod
    def letterbox_fill(
        video_path: str,
        target_width: int,
        target_height: int,
        color: tuple[int, int, int] = (0, 0, 0),
        output_path: Optional[str] = None
    ) -> str:
        """
        黑边/白边填充（Letterbox/Pillarbox）

        保持原始宽高比，在周围添加边框

        Args:
            video_path: 输入视频路径
            target_width: 目标宽度
            target_height: 目标高度
            color: 边框颜色 (B, G, R)
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        BackgroundFiller._ensure_ffmpeg()

        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_letterbox{p.suffix}")

        # 构建 padding 滤镜参数
        color_hex = f"0x{color[2]:02x}{color[1]:02x}{color[0]:02x}"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", (
                f"scale={target_width}:{target_height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color={color_hex}"
            ),
            "-map", "0:a?",
            "-c:a", "copy",
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg letterbox 填充失败: {e.stderr.decode() if e.stderr else str(e)}")

        return output_path
