"""
VJ-Gen Topaz 视频超分适配器
调用 Topaz Labs API 进行视频超分辨率处理
"""

import asyncio
import os
import time
import uuid
from pathlib import Path

import httpx

from src.adapters.base import AdapterConfig, AdapterResult
from src.adapters.video.base import VideoGenAdapter, VideoGenParams, VideoResult


class TopazVideoAdapter:
    """Topaz Video AI 超分适配器"""

    def __init__(self, config: AdapterConfig):
        self.config = config
        self._base_url = config.api_base or "https://api.topazlabs.io/v1"
        self._output_dir = config.extra_params.get("output_dir", "/tmp/vj-gen/upscaled")
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)

    @property
    def provider(self) -> str:
        return "topaz"

    @property
    def model(self) -> str:
        return "video-ai"

    async def upscale(
        self,
        video_path: str,
        scale: int = 2,
        model: str = "auto",
        fps_mode: str = "preserve",
    ) -> AdapterResult[str]:
        """
        视频超分辨率放大

        Args:
            video_path: 输入视频路径
            scale: 放大倍数 (2 或 4)
            model: 使用的模型 (auto/denoise/sharpen/帧率转换)
            fps_mode: 帧率模式 (preserve/original/target)

        Returns:
            放大后的视频路径
        """
        start_time = time.time()

        if scale not in [2, 4]:
            return AdapterResult.fail("Scale must be 2 or 4")

        try:
            # 读取视频文件
            with open(video_path, "rb") as f:
                video_data = f.read()

            import base64
            video_b64 = base64.b64encode(video_data).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout * 3) as client:
                response = await client.post(
                    f"{self._base_url}/video/upscale",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                    },
                    json={
                        "video": video_b64,
                        "scale": scale,
                        "model": model,
                        "fps_mode": fps_mode,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code} - {response.text}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            if not task_id:
                return AdapterResult.fail("No task ID returned")

            # 轮询直到完成
            output_path = await self._poll_until_complete(task_id, start_time)

            if output_path:
                latency_ms = (time.time() - start_time) * 1000
                return AdapterResult.ok(output_path, latency_ms)
            else:
                return AdapterResult.fail("Upscale timed out")

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def enhance(
        self,
        video_path: str,
        model: str = "interpolation",
    ) -> AdapterResult[str]:
        """
        视频增强（去噪、锐化等）

        Args:
            video_path: 输入视频路径
            model: 增强模型 (interpolation/denoise/sharpen)

        Returns:
            增强后的视频路径
        """
        start_time = time.time()

        try:
            with open(video_path, "rb") as f:
                video_data = f.read()

            import base64
            video_b64 = base64.b64encode(video_data).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout * 3) as client:
                response = await client.post(
                    f"{self._base_url}/video/enhance",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                    },
                    json={
                        "video": video_b64,
                        "model": model,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            output_path = await self._poll_until_complete(task_id, start_time)

            if output_path:
                latency_ms = (time.time() - start_time) * 1000
                return AdapterResult.ok(output_path, latency_ms)
            else:
                return AdapterResult.fail("Enhance timed out")

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def interpolate_fps(
        self,
        video_path: str,
        target_fps: int = 60,
    ) -> AdapterResult[str]:
        """
        帧率插值

        Args:
            video_path: 输入视频路径
            target_fps: 目标帧率

        Returns:
            插值后的视频路径
        """
        start_time = time.time()

        try:
            with open(video_path, "rb") as f:
                video_data = f.read()

            import base64
            video_b64 = base64.b64encode(video_data).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout * 3) as client:
                response = await client.post(
                    f"{self._base_url}/video/interpolate",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                    },
                    json={
                        "video": video_b64,
                        "target_fps": target_fps,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            output_path = await self._poll_until_complete(task_id, start_time)

            if output_path:
                latency_ms = (time.time() - start_time) * 1000
                return AdapterResult.ok(output_path, latency_ms)
            else:
                return AdapterResult.fail("Interpolation timed out")

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def health_check(self) -> "HealthStatus":
        """健康检查"""
        from src.adapters.base import HealthStatus
        import time

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self._base_url}/health",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
            latency = (time.time() - start) * 1000
            return HealthStatus(
                healthy=response.status_code == 200,
                latency_ms=latency,
                error_message="" if response.status_code == 200 else response.text,
                last_check=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                error_message=str(e),
                last_check=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

    async def _poll_until_complete(self, task_id: str, start_time: float) -> str | None:
        """轮询直到任务完成"""
        max_wait = 300  # 视频处理可能需要更长时间
        poll_interval = 5

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            while (time.time() - start_time) < max_wait:
                try:
                    response = await client.get(
                        f"{self._base_url}/task/{task_id}",
                        headers={"Authorization": f"Bearer {self.config.api_key}"},
                    )

                    if response.status_code != 200:
                        await asyncio.sleep(poll_interval)
                        continue

                    result = response.json()
                    status = result.get("status")

                    if status == "completed":
                        video_url = result.get("output", {}).get("video_url")
                        if video_url:
                            return await self._download_video(video_url)
                        return None

                    elif status == "failed":
                        return None

                except Exception:
                    pass

                await asyncio.sleep(poll_interval)

        return None

    async def _download_video(self, url: str) -> str | None:
        """下载视频到本地"""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

            filename = f"topaz_{uuid.uuid4().hex[:8]}.mp4"
            video_path = os.path.join(self._output_dir, filename)

            with open(video_path, "wb") as f:
                f.write(response.content)

            return video_path
        except Exception:
            return None


# 别名
TopazAdapter = TopazVideoAdapter
