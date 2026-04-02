"""
VJ-Gen DALL-E 适配器
调用 OpenAI DALL-E API 生成图像
"""

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Literal

import httpx

from src.adapters.base import AdapterConfig, AdapterResult
from src.adapters.image.base import ImageGenAdapter, ImageGenParams, ImageResult


class DalleAdapter(ImageGenAdapter):
    """DALL-E 适配器"""

    # DALL-E 3 支持的分辨率
    DALLE3_SIZES = {
        ("1024", "1024"),
        ("1792", "1024"),
        ("1024", "1792"),
    }

    # DALL-E 2 支持的分辨率
    DALLE2_SIZES = {
        ("256", "256"),
        ("512", "512"),
        ("1024", "1024"),
    }

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._base_url = "https://api.openai.com/v1"
        self._model = config.extra_params.get("model", "dall-e-3")
        self._output_dir = config.extra_params.get("output_dir", "/tmp/vj-gen/images")
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def max_resolution(self) -> tuple[int, int]:
        if self._model.startswith("dall-e-3"):
            return (1792, 1792)
        return (1024, 1024)

    @property
    def supported_styles(self) -> list[str]:
        if self._model.startswith("dall-e-3"):
            return ["auto", "vivid", "natural"]
        return ["auto"]

    async def generate(
        self,
        prompt: str,
        params: ImageGenParams | None = None,
    ) -> AdapterResult[ImageResult]:
        """生成图像"""
        start_time = time.time()

        if params is None:
            params = ImageGenParams(prompt=prompt)

        # 验证参数
        valid, msg = self.validate_params(params)
        if not valid:
            return AdapterResult.fail(msg)

        # 确定分辨率
        if self._model.startswith("dall-e-3"):
            size = self._choose_dalle3_size(params.width, params.height)
            style = params.style if params.style in ["vivid", "natural"] else "vivid"
        else:
            size = self._choose_dalle2_size(params.width, params.height)
            style = None

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                request_data = {
                    "model": self._model,
                    "prompt": prompt,
                    "n": min(params.num_images, 1),  # DALL-E 3 每次最多 1 张
                    "size": size,
                }
                if style:
                    request_data["style"] = style

                response = await client.post(
                    f"{self._base_url}/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_data,
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code} - {response.text}")

            result_data = response.json()
            image_url = result_data.get("data", [{}])[0].get("url", "")

            if not image_url:
                return AdapterResult.fail("No image URL returned")

            # 下载图像
            image_path = await self._download_image(image_url, prompt)
            if image_path is None:
                return AdapterResult.fail("Failed to download image")

            # 解析分辨率
            width, height = map(int, size.split("x"))

            latency_ms = (time.time() - start_time) * 1000
            image_result = ImageResult(
                image_path=image_path,
                seed=0,
                prompt=prompt,
                width=width,
                height=height,
                generation_time_ms=latency_ms,
            )

            self._record_call(True, latency_ms)
            return AdapterResult.ok(image_result, latency_ms)

        except Exception as e:
            self._record_call(False, 0)
            return AdapterResult.fail(str(e))

    async def generate_batch(
        self,
        prompts: list[str],
        params: ImageGenParams | None = None,
    ) -> list[AdapterResult[ImageResult]]:
        """批量生成图像"""
        tasks = [self.generate(prompt, params) for prompt in prompts]
        return await asyncio.gather(*tasks)

    async def upscale(
        self,
        image_path: str,
        scale: int = 2,
    ) -> AdapterResult[str]:
        """DALL-E 不支持超分，返回原图"""
        return AdapterResult.ok(image_path, 0)

    async def variation(
        self,
        image_path: str,
        prompt: str | None = None,
        strength: float = 0.5,
    ) -> AdapterResult[ImageResult]:
        """生成图像变体"""
        start_time = time.time()

        # DALL-E 使用 image_variations API
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                with open(image_path, "rb") as f:
                    files = {"image": f}
                    data = {"model": "dall-e-2", "n": 1, "size": "1024x1024"}

                    response = await client.post(
                        f"{self._base_url}/images/variations",
                        headers={"Authorization": f"Bearer {self.config.api_key}"},
                        data=data,
                        files=files,
                    )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            image_url = result_data.get("data", [{}])[0].get("url", "")

            if not image_url:
                return AdapterResult.fail("No variation URL returned")

            image_path = await self._download_image(image_url, "variation")
            if image_path is None:
                return AdapterResult.fail("Failed to download variation")

            latency_ms = (time.time() - start_time) * 1000
            image_result = ImageResult(
                image_path=image_path,
                seed=0,
                prompt=prompt or "",
                width=1024,
                height=1024,
                generation_time_ms=latency_ms,
            )

            return AdapterResult.ok(image_result, latency_ms)

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
                    f"{self._base_url}/models",
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
            return await self.generate(input_data, kwargs.get("params"))
        return await self.generate(input_data.get("prompt", ""), input_data.get("params"))

    def get_capabilities(self) -> list["AdapterCapability"]:
        """获取适配器能力"""
        from src.adapters.base import AdapterCapability
        return [
            AdapterCapability(
                name="text_to_image",
                description="Generate high-quality images using DALL-E 3",
                supported_params=["prompt", "width", "height", "style"],
                limitations=["Max 1792x1792 for DALL-E 3"],
                estimated_latency_ms=30000,
                cost_per_call=0.04,
            ),
            AdapterCapability(
                name="image_variation",
                description="Generate variations (DALL-E 2 only)",
                supported_params=["image_path"],
                limitations=["Only works with DALL-E 2"],
                estimated_latency_ms=20000,
                cost_per_call=0.02,
            ),
        ]

    def _choose_dalle3_size(self, width: int, height: int) -> str:
        """选择 DALL-E 3 分辨率"""
        target_ratio = width / height

        for size in self.DALLE3_SIZES:
            w, h = int(size[0]), int(size[1])
            if abs(w / h - target_ratio) < 0.2:
                return f"{w}x{h}"

        # 默认返回方形
        return "1024x1024"

    def _choose_dalle2_size(self, width: int, height: int) -> str:
        """选择 DALL-E 2 分辨率"""
        # 找最接近的尺寸
        sizes = ["1024x1024", "512x512", "256x256"]
        for size in sizes:
            w, h = map(int, size.split("x"))
            if w >= width and h >= height:
                return size
        return "1024x1024"

    async def _download_image(self, url: str, prompt: str) -> str | None:
        """下载图像到本地"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

            filename = f"dalle_{uuid.uuid4().hex[:8]}.png"
            image_path = os.path.join(self._output_dir, filename)

            with open(image_path, "wb") as f:
                f.write(response.content)

            return image_path
        except Exception:
            return None
