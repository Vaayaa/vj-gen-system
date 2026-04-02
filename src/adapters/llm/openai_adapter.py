"""
VJ-Gen OpenAI LLM 适配器
"""

import json
import time
from typing import Any

from openai import AsyncOpenAI

from src.adapters.base import AdapterConfig, AdapterResult, BaseAdapter, HealthStatus
from src.adapters.llm.base import LLMAdapter as BaseLLMAdapter, LLMMessage, LLMResponse


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI LLM 适配器"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base or None,
            timeout=config.timeout,
        )
        self._model = config.model or "gpt-4o"

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def context_window(self) -> int:
        """OpenAI 模型上下文窗口"""
        windows = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
        }
        return windows.get(self._model, 128000)

    @property
    def supports_structured_output(self) -> bool:
        return True

    async def health_check(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            await self.client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            return HealthStatus(healthy=True, latency_ms=latency_ms, last_check=time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return HealthStatus(healthy=False, latency_ms=latency_ms, error_message=str(e), last_check=time.strftime("%Y-%m-%d %H:%M:%S"))

    async def invoke(self, input_data: Any, **kwargs) -> Any:
        result = await self.chat_simple(input_data, **kwargs)
        return result

    async def chat(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AdapterResult[LLMResponse]:
        start = time.perf_counter()
        try:
            openai_messages = [{"role": m.role, "content": m.content} for m in messages]
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
                **kwargs,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            content = response.choices[0].message.content or ""
            usage = response.usage
            tokens_used = usage.total_tokens if usage else 0

            llm_response = LLMResponse(
                content=content,
                model=self._model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                finish_reason=response.choices[0].finish_reason,
            )
            self._record_call(True, latency_ms, tokens_used)
            return AdapterResult.ok(llm_response, latency_ms, tokens_used)
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            self._record_call(False, latency_ms)
            return AdapterResult.fail(str(e))

    async def chat_simple(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs,
    ) -> AdapterResult[str]:
        messages = self.build_messages(prompt, system)
        result = await self.chat(messages, **kwargs)
        if result.success:
            return AdapterResult.ok(result.data.content, result.latency_ms, result.tokens_used)
        return AdapterResult.fail(result.error)

    async def structured_output(
        self,
        schema: dict[str, Any],
        prompt: str,
        system: str | None = None,
        **kwargs,
    ) -> AdapterResult[dict]:
        start = time.perf_counter()
        try:
            messages = self.build_messages(prompt, system)
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object", "schema": schema},
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            content = response.choices[0].message.content or "{}"
            usage = response.usage
            tokens_used = usage.total_tokens if usage else 0

            data = json.loads(content)
            self._record_call(True, latency_ms, tokens_used)
            return AdapterResult.ok(data, latency_ms, tokens_used)
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            self._record_call(False, latency_ms)
            return AdapterResult.fail(str(e))
