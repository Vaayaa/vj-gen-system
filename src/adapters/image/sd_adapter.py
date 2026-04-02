"""
VJ-Gen Stable Diffusion 适配器
调用 Stable Diffusion API 生成图像
"""

import asyncio
import os
import time
import uuid
from pathlib import Path

import httpx

from src.adapters.base import AdapterConfig, AdapterResult
from src.adapters.image.base import ImageGenAdapter, ImageGenParams, ImageResult


class StableDiffusionAdapter(ImageGenAdapter):
    """Stable Diffusion 适配器"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._base_url = config.api_base or "https://api.stability.ai/v1"
        self._engine = config.extra_params.get("engine", "stable-diffusion-xl-1024-v1-0")
        self._output_dir = config.extra_params.get("output_dir", "/tmp/vj-gen/images")
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)

    @property
    def provider(self) -> str:
        return "stability_ai"

    @property
    def model(self) -> str:
        return self._engine

    @property
    def max_resolution(self) -> tuple[int, int]:
        return (2048, 2048)

    @property
    def supported_styles(self) -> list[str]:
        return [
            "auto", "photographic", "digital-art", "concept-art",
            "comic-book", "fantasy-art", "line-art", "anime",
            "3d-model", "cinematic", "neon-punk", "isometric",
        ]

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

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self._base_url}/generation/{self._engine}/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text_prompts": [{"text": prompt, "weight": 1}],
                        "cfg_scale": params.guidance_scale,
                        "height": params.height,
                        "width": params.width,
                        "steps": params.steps,
                        "samples": params.num_images,
                        "seed": params.seed if params.seed != -1 else 0,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code} - {response.text}")

            result_data = response.json()
            artifacts = result_data.get("artifacts", [])

            if not artifacts:
                return AdapterResult.fail("No images generated")

            # 保存生成的图像
            seed = artifacts[0].get("seed", 0)
            image_path = os.path.join(
                self._output_dir,
                f"sd_{uuid.uuid4().hex[:8]}_{seed}.png"
            )

            import base64
            image_data = base64.b64decode(artifacts[0].get("base64", ""))
            with open(image_path, "wb") as f:
                f.write(image_data)

            latency_ms = (time.time() - start_time) * 1000
            image_result = ImageResult(
                image_path=image_path,
                seed=seed,
                prompt=prompt,
                width=params.width,
                height=params.height,
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
        """超分辨率放大"""
        start_time = time.time()

        if scale not in [2, 4]:
            return AdapterResult.fail("Scale must be 2 or 4")

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout * 2) as client:
                response = await client.post(
                    f"{self._base_url}/image-to-image/upscale",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                    },
                    json={
                        "image": image_data,
                        "scale": scale,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"Upscale failed: {response.status_code}")

            result_data = response.json()
            upscaled_path = os.path.join(
                self._output_dir,
                f"sd_upscaled_{uuid.uuid4().hex[:8]}.png"
            )

            import base64
            image_data = base64.b64decode(result_data.get("artifacts", [{}])[0].get("base64", ""))
            with open(upscaled_path, "wb") as f:
                f.write(image_data)

            latency_ms = (time.time() - start_time) * 1000
            return AdapterResult.ok(upscaled_path, latency_ms)

        except Exception as e:
            return AdapterResult.fail(str(e))

    async def variation(
        self,
        image_path: str,
        prompt: str | None = None,
        strength: float = 0.5,
    ) -> AdapterResult[ImageResult]:
        """生成图像变体"""
        start_time = time.time()

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self._base_url}/generation/{self._engine}/image-to-image",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "init_image": image_data,
                        "text_prompts": [{"text": prompt or "", "weight": 1}] if prompt else [],
                        "cfg_scale": 7.5,
                        "steps": 30,
                        "seed": 0,
                    },
                )

            if response.status_code != 200:
                return AdapterResult.fail(f"API error: {response.status_code}")

            result_data = response.json()
            artifacts = result_data.get("artifacts", [])

            if not artifacts:
                return AdapterResult.fail("No variation generated")

            seed = artifacts[0].get("seed", 0)
            variation_path = os.path.join(
                self._output_dir,
                f"sd_variation_{uuid.uuid4().hex[:8]}_{seed}.png"
            )

            import base64
            image_data = base64.b64decode(artifacts[0].get("base64", ""))
            with open(variation_path, "wb") as f:
                f.write(image_data)

            latency_ms = (time.time() - start_time) * 1000
            image_result = ImageResult(
                image_path=variation_path,
                seed=seed,
                prompt=prompt or "",
                width=0,
                height=0,
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
                    f"{self._base_url}/user/balance",
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
                description="Generate images from text prompts",
                supported_params=["prompt", "width", "height", "guidance_scale", "steps", "seed"],
                limitations=["Max 2048x2048 resolution"],
                estimated_latency_ms=5000,
                cost_per_call=0.01,
            ),
            AdapterCapability(
                name="image_variation",
                description="Generate variations of an image",
                supported_params=["image_path", "prompt", "strength"],
                estimated_latency_ms=5000,
                cost_per_call=0.01,
            ),
            AdapterCapability(
                name="image_upscale",
                description="Upscale images using AI",
                supported_params=["image_path", "scale"],
                limitations=["Only 2x and 4x scaling supported"],
                estimated_latency_ms=10000,
                cost_per_call=0.02,
            ),
        ]
