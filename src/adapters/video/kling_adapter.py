"""
VJ-Gen 快手 Kling 视频生成适配器
调用快手 Kling API 生成视频
"""

import asyncio
import os
import time
import uuid
from pathlib import Path

import httpx

from src.adapters.base import AdapterConfig, AdapterResult
from src.adapters.video.base import VideoGenAdapter, VideoGenParams, VideoResult


class KlingAdapter(VideoGenAdapter):
    """快手 Kling 适配器"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._base_url = config.api_base or "https://api.kling.ai/v1"
        self._output_dir = config.extra_params.get("output_dir", "/tmp/vj-gen/videos")
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)

    @property
    def provider(self) -> str:
        return "kling"

    @property
    def model(self) -> str:
        return "kling-1.5"

    @property
    def max_duration(self) -> float:
        return 30.0  # Kling 最长 30 秒

    @property
    def supported_resolutions(self) -> list[str]:
        return ["540p", "720p", "1080p"]

    async def generate(
        self,
        keyframe_path: str,
        prompt: str,
        params: VideoGenParams | None = None,
    ) -> AdapterResult[VideoResult]:
        """从关键帧生成视频"""
        start_time = time.time()

        if params is None:
            params = VideoGenParams(prompt=prompt)

        try:
            # 读取关键帧
            with open(keyframe_path, "rb") as f:
                keyframe_data = f.read()

            import base64
            keyframe_b64 = base64.b64encode(keyframe_data).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self._base_url}/videos/image2video",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "kling-1.5",
                        "prompt": prompt,
                        "negative_prompt": params.negative_prompt,
                        "image_base64": keyframe_b64,
                        "duration": min(params.duration, self.max_duration),
                        "resolution": params.resolution,
                        "fps": params.fps,
                        "camera_motion": params.camera_motion,
                        "seed": params.seed if params.seed != -1 else None,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code} - {response.text}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            if not task_id:
                return AdapterResult.fail("No task ID returned")

            # 轮询直到完成
            video_result = await self._poll_until_complete(task_id, start_time)

            if video_result:
                return AdapterResult.ok(video_result, video_result.generation_time_ms)
            else:
                return AdapterResult.fail("Video generation timed out")

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def generate_from_text(
        self,
        prompt: str,
        params: VideoGenParams | None = None,
    ) -> AdapterResult[VideoResult]:
        """文本直接生成视频"""
        start_time = time.time()

        if params is None:
            params = VideoGenParams(prompt=prompt)

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self._base_url}/videos/text2video",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "kling-1.5",
                        "prompt": prompt,
                        "negative_prompt": params.negative_prompt,
                        "duration": min(params.duration, self.max_duration),
                        "resolution": params.resolution,
                        "fps": params.fps,
                        "camera_motion": params.camera_motion,
                        "seed": params.seed if params.seed != -1 else None,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            if not task_id:
                return AdapterResult.fail("No task ID returned")

            video_result = await self._poll_until_complete(task_id, start_time)

            if video_result:
                return AdapterResult.ok(video_result, video_result.generation_time_ms)
            else:
                return AdapterResult.fail("Video generation timed out")

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def extend(
        self,
        video_path: str,
        duration: float,
        prompt: str | None = None,
    ) -> AdapterResult[VideoResult]:
        """延长视频"""
        start_time = time.time()

        try:
            with open(video_path, "rb") as f:
                video_data = f.read()

            import base64
            video_b64 = base64.b64encode(video_data).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self._base_url}/videos/extend",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "kling-1.5",
                        "video_base64": video_b64,
                        "prompt": prompt or "",
                        "duration": min(duration, self.max_duration),
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            video_result = await self._poll_until_complete(task_id, start_time)

            if video_result:
                return AdapterResult.ok(video_result, video_result.generation_time_ms)
            else:
                return AdapterResult.fail("Video extension timed out")

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def stylize(
        self,
        video_path: str,
        style: str,
    ) -> AdapterResult[VideoResult]:
        """视频风格化"""
        start_time = time.time()

        try:
            with open(video_path, "rb") as f:
                video_data = f.read()

            import base64
            video_b64 = base64.b64encode(video_data).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self._base_url}/videos/style",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "kling-1.5",
                        "video_base64": video_b64,
                        "style": style,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            task_id = result_data.get("task_id")

            video_result = await self._poll_until_complete(task_id, start_time)

            if video_result:
                return AdapterResult.ok(video_result, video_result.generation_time_ms)
            else:
                return AdapterResult.fail("Video stylization timed out")

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

    async def invoke(self, input_data: any, **kwargs) -> any:
        """调用适配器"""
        if isinstance(input_data, str):
            return await self.generate_from_text(input_data, kwargs.get("params"))
        return await self.generate(
            input_data.get("keyframe_path", ""),
            input_data.get("prompt", ""),
            input_data.get("params"),
        )

    def get_capabilities(self) -> list["AdapterCapability"]:
        """获取适配器能力"""
        from src.adapters.base import AdapterCapability
        return [
            AdapterCapability(
                name="keyframe_to_video",
                description="Generate video from keyframe using Kling",
                supported_params=["keyframe_path", "prompt", "duration", "resolution"],
                limitations=["Max 30 seconds, 1080p resolution"],
                estimated_latency_ms=120000,
                cost_per_call=0.03,
            ),
            AdapterCapability(
                name="text_to_video",
                description="Generate video from text using Kling",
                supported_params=["prompt", "duration", "resolution"],
                limitations=["Max 30 seconds"],
                estimated_latency_ms=150000,
                cost_per_call=0.04,
            ),
            AdapterCapability(
                name="video_extend",
                description="Extend existing video",
                supported_params=["video_path", "duration", "prompt"],
                estimated_latency_ms=120000,
                cost_per_call=0.03,
            ),
        ]

    async def _poll_until_complete(self, task_id: str, start_time: float) -> VideoResult | None:
        """轮询直到任务完成"""
        max_wait = 180  # 最多等待 180 秒（Kling 可能更慢）
        poll_interval = 3  # 每 3 秒轮询一次

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            while (time.time() - start_time) < max_wait:
                response = await client.get(
                    f"{self._base_url}/videos/task/{task_id}",
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
                        video_path = await self._download_video(video_url)
                        if video_path:
                            return VideoResult(
                                video_path=video_path,
                                thumbnail_path=result.get("output", {}).get("cover_url", ""),
                                duration=result.get("output", {}).get("duration", 5.0),
                                width=result.get("output", {}).get("width", 1280),
                                height=result.get("output", {}).get("height", 720),
                                fps=result.get("output", {}).get("fps", 24),
                                seed=result.get("seed", 0),
                                generation_time_ms=(time.time() - start_time) * 1000,
                            )
                    return None

                elif status == "failed":
                    return None

                await asyncio.sleep(poll_interval)

        return None

    async def _download_video(self, url: str) -> str | None:
        """下载视频到本地"""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

            filename = f"kling_{uuid.uuid4().hex[:8]}.mp4"
            video_path = os.path.join(self._output_dir, filename)

            with open(video_path, "wb") as f:
                f.write(response.content)

            return video_path
        except Exception:
            return None
