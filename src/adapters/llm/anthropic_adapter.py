"""
VJ-Gen Anthropic LLM 适配器
"""

import json
import time
from typing import Any

import anthropic

from src.adapters.base import AdapterConfig, AdapterResult, HealthStatus
from src.adapters.llm.base import LLMAdapter as BaseLLMAdapter, LLMMessage, LLMResponse


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic LLM 适配器"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
        )
        self._model = config.model or "claude-sonnet-4-20250514"

    @property
    def provider(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    @property
    def context_window(self) -> int:
        """Anthropic 模型上下文窗口"""
        windows = {
            "claude-sonnet-4-20250514": 200000,
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-5-sonnet-latest": 200000,
            "claude-3-opus-latest": 200000,
            "claude-3-haiku-latest": 200000,
        }
        return windows.get(self._model, 200000)

    @property
    def supports_structured_output(self) -> bool:
        # Anthropic 通过 XML + JSON 实现结构化输出
        return True

    async def health_check(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            await self.client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
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
            # Convert messages format
            anthropic_messages = []
            system_msg = None
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                else:
                    anthropic_messages.append({"role": msg.role, "content": msg.content})

            response = await self.client.messages.create(
                model=self._model,
                system=system_msg,
                messages=anthropic_messages,
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
                **kwargs,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            content = response.content[0].text if response.content else ""
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            llm_response = LLMResponse(
                content=content,
                model=self._model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                finish_reason=str(response.stop_reason) if response.stop_reason else "stop",
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
        """Anthropic 结构化输出：使用 XML 标签引导 JSON 输出"""
        start = time.perf_counter()
        try:
            # 构建提示词，引导模型输出 JSON
            schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
            structured_prompt = f"""{prompt}

请严格按照以下 JSON Schema 格式输出，不要添加任何其他内容：

```json
{schema_str}
```"""

            messages = [{"role": "user", "content": structured_prompt}]
            system_msg = system or "你是一个专业的 JSON 响应生成器。请只输出 JSON，不要有任何其他文字。"

            response = await self.client.messages.create(
                model=self._model,
                system=system_msg,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            content = response.content[0].text if response.content else "{}"
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # 尝试解析 JSON
            # 移除可能的 markdown 代码块
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content.strip())
            self._record_call(True, latency_ms, tokens_used)
            return AdapterResult.ok(data, latency_ms, tokens_used)
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            self._record_call(False, latency_ms)
            return AdapterResult.fail(str(e))
