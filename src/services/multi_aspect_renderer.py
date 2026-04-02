"""
多画幅渲染器
实现批量多画幅视频渲染
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ..models.render import (
    AspectRatio,
    CropRegion,
    PRESET_PROFILES,
    RenderJob,
    RenderProfile,
)
from .cropper import SmartCropper
from .filler import BackgroundFiller, FillStrategy


class MultiAspectRenderer:
    """多画幅渲染器"""

    def __init__(self, base_video: Optional[str] = None):
        """
        初始化渲染器

        Args:
            base_video: 基础视频路径（可选）
        """
        self.base_video = base_video
        self.cropper = SmartCropper()
        self.filler = BackgroundFiller()
        self._last_jobs: List[RenderJob] = []

    def _get_video_info(self, video_path: str) -> Dict:
        """获取视频信息"""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration,codec_name",
            "-of", "json",
            video_path
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            import json
            info = json.loads(result.stdout)
            stream = info["streams"][0]

            fps_parts = stream["r_frame_rate"].split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else float(fps_parts[0])

            return {
                "width": int(stream["width"]),
                "height": int(stream["height"]),
                "fps": fps,
                "duration": float(stream.get("duration", 0)),
                "codec": stream.get("codec_name", "unknown"),
            }
        except (subprocess.CalledProcessError, FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"获取视频信息失败: {e}")

    def _get_aspect_ratio(self, width: int, height: int) -> AspectRatio:
        """根据分辨率判断画幅比例"""
        ratio = width / height
        if abs(ratio - 16/9) < 0.1:
            return AspectRatio.LANDSCAPE_16_9
        elif abs(ratio - 9/16) < 0.1:
            return AspectRatio.PORTRAIT_9_16
        elif abs(ratio - 1/1) < 0.1:
            return AspectRatio.SQUARE_1_1
        elif abs(ratio - 32/9) < 0.5:
            return AspectRatio.ULTRA_WIDE
        else:
            return AspectRatio.LANDSCAPE_16_9

    def _scale_and_crop(
        self,
        input_path: str,
        output_path: str,
        profile: RenderProfile,
        crop_region: Optional[CropRegion] = None
    ) -> str:
        """
        缩放并裁切视频

        Args:
            input_path: 输入路径
            output_path: 输出路径
            profile: 渲染配置
            crop_region: 裁切区域

        Returns:
            输出路径
        """
        filters = []

        # 如果有裁切区域，先裁切
        if crop_region:
            filters.append(f"crop={crop_region.to_ffmpeg_crop}")

        # 然后缩放到目标分辨率
        filters.append(f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=increase")
        filters.append(f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease")

        # 如果缩放后有黑边，用 padding 填充
        filters.append(f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2")

        vf = ",".join(filters)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", profile.codec,
            "-crf", str(profile.crf),
            "-preset", profile.preset,
            "-c:a", profile.audio_codec,
            "-b:a", profile.audio_bitrate,
            "-ar", str(profile.audio_sample_rate),
            "-r", str(profile.fps),
            output_path
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def render_single(
        self,
        input_video: str,
        profile: RenderProfile,
        output_path: str,
        fill_strategy: FillStrategy = FillStrategy.BLUR,
        use_smart_crop: bool = False
    ) -> str:
        """
        渲染单个画幅

        Args:
            input_video: 输入视频路径
            profile: 渲染配置
            output_path: 输出路径
            fill_strategy: 填充策略
            use_smart_crop: 是否使用智能裁切

        Returns:
            输出路径
        """
        # 1. 检查原始比例
        info = self._get_video_info(input_video)
        source_width = info["width"]
        source_height = info["height"]
        source_ratio = source_width / source_height

        # 解析目标比例
        target_ratio_map = {
            "16:9": 16/9,
            "9:16": 9/16,
            "1:1": 1.0,
            "32:9": 32/9,
        }
        target_ratio = target_ratio_map.get(profile.aspect_ratio, 16/9)

        # 2. 智能裁切或填充
        crop_region = None

        if abs(source_ratio - target_ratio) < 0.01:
            # 比例相同，直接缩放
            pass
        elif source_ratio > target_ratio:
            # 源视频更宽，需要裁切或填充
            if use_smart_crop:
                # 智能裁切
                box = self.cropper.find_main_subject(input_video)
                source_ar_enum = self._get_aspect_ratio(source_width, source_height)
                crop_region = self.cropper.calculate_crop(
                    box,
                    AspectRatio(profile.aspect_ratio),
                    source_width,
                    source_height
                )
            else:
                # 中心裁切
                if source_ratio > target_ratio:
                    new_width = int(source_height * target_ratio)
                    x = (source_width - new_width) // 2
                    crop_region = CropRegion(x=x, y=0, width=new_width, height=source_height)
        else:
            # 源视频更高，需要填充
            pass  # 缩放时会自动添加 padding

        # 3. 缩放到目标分辨率
        self._scale_and_crop(input_video, output_path, profile, crop_region)

        return output_path

    def render_all_profiles(
        self,
        profiles: List[RenderProfile],
        output_dir: str,
        input_video: Optional[str] = None,
        fill_strategy: FillStrategy = FillStrategy.BLUR,
        use_smart_crop: bool = False
    ) -> Dict[str, str]:
        """
        批量渲染所有画幅版本

        Args:
            profiles: 渲染配置列表
            output_dir: 输出目录
            input_video: 输入视频路径（覆盖构造函数中的 base_video）
            fill_strategy: 填充策略
            use_smart_crop: 是否使用智能裁切

        Returns:
            配置名称到输出路径的映射
        """
        video = input_video or self.base_video
        if not video:
            raise ValueError("未指定输入视频")

        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = {}
        jobs: List[RenderJob] = []

        for profile in profiles:
            output_path = f"{output_dir}/{profile.name}.{profile.output_format}"
            job = RenderJob(
                input_path=video,
                output_path=output_path,
                profile=profile,
                fill_method=fill_strategy.value,
            )

            try:
                self.render_single(
                    video,
                    profile,
                    output_path,
                    fill_strategy=fill_strategy,
                    use_smart_crop=use_smart_crop
                )
                job.status = "completed"
                results[profile.name] = output_path
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                results[profile.name] = None

            jobs.append(job)

        self._last_jobs = jobs
        return results

    def render_with_presets(
        self,
        preset_names: List[str],
        output_dir: str,
        input_video: Optional[str] = None,
        fill_strategy: FillStrategy = FillStrategy.BLUR,
        use_smart_crop: bool = False
    ) -> Dict[str, str]:
        """
        使用预设配置渲染

        Args:
            preset_names: 预设名称列表（如 ["landscape_16_9", "portrait_9_16"]）
            output_dir: 输出目录
            input_video: 输入视频路径
            fill_strategy: 填充策略
            use_smart_crop: 是否使用智能裁切

        Returns:
            配置名称到输出路径的映射
        """
        profiles = []
        for name in preset_names:
            if name not in PRESET_PROFILES:
                raise ValueError(f"未知的预设: {name}")
            profiles.append(PRESET_PROFILES[name])

        return self.render_all_profiles(
            profiles,
            output_dir,
            input_video=input_video,
            fill_strategy=fill_strategy,
            use_smart_crop=use_smart_crop
        )

    def get_last_jobs(self) -> List[RenderJob]:
        """获取上次渲染任务列表"""
        return self._last_jobs

    def get_render_status(self) -> Dict[str, str]:
        """获取渲染状态摘要"""
        if not self._last_jobs:
            return {"status": "no_jobs"}

        completed = sum(1 for j in self._last_jobs if j.status == "completed")
        failed = sum(1 for j in self._last_jobs if j.status == "failed")
        pending = sum(1 for j in self._last_jobs if j.status == "pending")

        return {
            "total": len(self._last_jobs),
            "completed": completed,
            "failed": failed,
            "pending": pending,
        }
