"""
智能裁切服务
使用 YOLO 等模型检测画面主体，计算最优裁切区域
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from ..models.render import AspectRatio, BoundingBox, CropRegion


class SmartCropper:
    """智能裁切器"""

    def __init__(self, model: str = "yolo", yolo_model: str = "yolov8n"):
        """
        初始化智能裁切器

        Args:
            model: 检测模型类型 ("yolo" 或 "center")
            yolo_model: YOLO 模型名称
        """
        self.model = model
        self.yolo_model = yolo_model
        self._yolo_model_instance = None

    def _load_yolo(self):
        """懒加载 YOLO 模型"""
        if self._yolo_model_instance is None:
            try:
                from ultralytics import YOLO
                self._yolo_model_instance = YOLO(self.yolo_model)
            except ImportError:
                raise ImportError(
                    "请安装 ultralytics: pip install ultralytics"
                )
        return self._yolo_model_instance

    def _detect_objects(self, frame: np.ndarray) -> list[BoundingBox]:
        """
        检测画面中的物体

        Args:
            frame: 输入帧 (BGR 格式)

        Returns:
            检测到的边界框列表
        """
        if self.model == "yolo":
            try:
                yolo = self._load_yolo()
                results = yolo(frame, verbose=False)
                boxes = []
                for result in results:
                    boxes_list = result.boxes
                    if boxes_list is not None:
                        for box in boxes_list:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0])
                            boxes.append(BoundingBox(
                                x=int(x1),
                                y=int(y1),
                                width=int(x2 - x1),
                                height=int(y2 - y1),
                                confidence=conf
                            ))
                return boxes
            except Exception as e:
                # YOLO 失败时回退到中心检测
                return self._detect_center(frame)
        else:
            return self._detect_center(frame)

    def _detect_center(self, frame: np.ndarray) -> list[BoundingBox]:
        """
        检测画面中心区域（备用方案）

        Args:
            frame: 输入帧

        Returns:
            中心区域的边界框
        """
        h, w = frame.shape[:2]
        # 返回画面中心 60% 的区域
        cx, cy = w // 2, h // 2
        bw, bh = int(w * 0.6), int(h * 0.6)
        return [BoundingBox(
            x=cx - bw // 2,
            y=cy - bh // 2,
            width=bw,
            height=bh,
            confidence=1.0
        )]

    def _get_video_info(self, video_path: str) -> Tuple[int, int, int, float]:
        """
        获取视频信息

        Args:
            video_path: 视频路径

        Returns:
            (width, height, fps, duration)
        """
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

    def find_main_subject(self, video_path: str, sample_interval: float = 1.0) -> Optional[BoundingBox]:
        """
        使用模型找到画面主体

        采样多个帧，取置信度最高的检测结果

        Args:
            video_path: 视频路径
            sample_interval: 采样间隔（秒）

        Returns:
            主体的边界框
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        if duration <= 0:
            cap.release()
            return None

        sample_positions = np.arange(0, duration, sample_interval)
        if len(sample_positions) == 0:
            sample_positions = [0]

        best_box: Optional[BoundingBox] = None
        best_score = 0.0

        for pos in sample_positions:
            frame_idx = int(pos * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue

            boxes = self._detect_objects(frame)
            if boxes:
                # 选择最大或最中心的物体
                for box in boxes:
                    # 综合考虑大小和置信度
                    area = box.width * box.height
                    score = area * box.confidence
                    if score > best_score:
                        best_score = score
                        best_box = box

        cap.release()

        if best_box is None:
            # 返回中心区域作为默认值
            _, height, _, _ = self._get_video_info(video_path)
            best_box = BoundingBox(
                x=0,
                y=height // 5,
                width=0,
                height=height * 3 // 5,
                confidence=0.5
            )

        return best_box

    def calculate_crop(
        self,
        box: BoundingBox,
        target_ratio: AspectRatio,
        video_width: int,
        video_height: int
    ) -> CropRegion:
        """
        计算最优裁切区域

        Args:
            box: 主体边界框
            target_ratio: 目标画幅比例
            video_width: 视频宽度
            video_height: 视频高度

        Returns:
            裁切区域
        """
        target_w = video_width
        target_h = video_height
        target_ar = target_ratio.ratio_float

        # 如果原视频比例接近目标比例，不需要裁切
        source_ar = video_width / video_height
        if abs(source_ar - target_ar) < 0.01:
            return CropRegion(x=0, y=0, width=video_width, height=video_height)

        # 以主体为中心计算裁切框
        # 目标宽高
        if target_ar > source_ar:
            # 目标更宽，以高度为基准计算宽度
            crop_height = min(int(box.height * 1.5), video_height)
            crop_width = int(crop_height * target_ar)
        else:
            # 目标更高，以宽度为基准计算高度
            crop_width = min(int(box.width * 1.5), video_width)
            crop_height = int(crop_width / target_ar)

        # 确保裁切框不超出边界
        crop_width = min(crop_width, video_width)
        crop_height = min(crop_height, video_height)

        # 以主体为中心
        cx = box.center_x
        cy = box.center_y

        x = max(0, cx - crop_width // 2)
        y = max(0, cy - crop_height // 2)

        # 调整确保不超出边界
        if x + crop_width > video_width:
            x = video_width - crop_width
        if y + crop_height > video_height:
            y = video_height - crop_height

        return CropRegion(
            x=x,
            y=y,
            width=crop_width,
            height=crop_height
        )

    def smart_crop(
        self,
        video_path: str,
        target_ratio: AspectRatio,
        output_path: Optional[str] = None
    ) -> str:
        """
        智能裁切视频

        Args:
            video_path: 输入视频路径
            target_ratio: 目标画幅比例
            output_path: 输出路径（可选）

        Returns:
            输出视频路径
        """
        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_{target_ratio.value}{p.suffix}")

        # 获取视频信息
        width, height, fps, _ = self._get_video_info(video_path)

        # 找主体
        box = self.find_main_subject(video_path)

        # 计算裁切区域
        crop = self.calculate_crop(box, target_ratio, width, height)

        # 执行裁切
        self._crop_video(video_path, output_path, crop, width, height)

        return output_path

    def _crop_video(
        self,
        input_path: str,
        output_path: str,
        crop: CropRegion,
        orig_width: int,
        orig_height: int
    ):
        """
        使用 ffmpeg 裁切视频

        Args:
            input_path: 输入路径
            output_path: 输出路径
            crop: 裁切区域
            orig_width: 原始宽度
            orig_height: 原始高度
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"crop={crop.to_ffmpeg_crop}",
            "-c:a", "copy",
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg 裁切失败: {e.stderr.decode() if e.stderr else str(e)}")
        except FileNotFoundError:
            raise FileNotFoundError("ffmpeg 未安装或不在 PATH 中")

    def crop_to_center(
        self,
        video_path: str,
        target_ratio: AspectRatio,
        output_path: Optional[str] = None
    ) -> str:
        """
        以中心点裁切视频（不使用检测模型）

        Args:
            video_path: 输入视频路径
            target_ratio: 目标画幅比例
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        if output_path is None:
            p = Path(video_path)
            output_path = str(p.parent / f"{p.stem}_{target_ratio.value}_center{p.suffix}")

        width, height, _, _ = self._get_video_info(video_path)

        target_ar = target_ratio.ratio_float
        source_ar = width / height

        if target_ar > source_ar:
            # 裁切宽度
            new_width = int(height * target_ar)
            x = (width - new_width) // 2
            crop = CropRegion(x=x, y=0, width=new_width, height=height)
        else:
            # 裁切高度
            new_height = int(width / target_ar)
            y = (height - new_height) // 2
            crop = CropRegion(x=0, y=y, width=width, height=new_height)

        self._crop_video(video_path, output_path, crop, width, height)
        return output_path
