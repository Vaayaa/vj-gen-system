"""
VJ-Gen LLM 适配器基类
定义大语言模型的统一接口
"""

from abc import abstractmethod
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from src.adapters.base import AdapterConfig, AdapterResult, BaseAdapter, HealthStatus


class LLMMessage(BaseModel):
    """对话消息"""
    role: Literal["system", "user", "assistant"] = Field(..., description="角色")
    content: str = Field(..., description="消息内容")


class LLMResponse(BaseModel):
    """LLM 响应"""
    content: str = Field(..., description="响应内容")
    model: str = Field(..., description="使用的模型")
    tokens_used: int = Field(default=0, description="使用的 token 数")
    latency_ms: float = Field(default=0, description="耗时（毫秒）")
    finish_reason: str = Field(default="stop", description="结束原因")


class LLMAdapter(BaseAdapter):
    """
    LLM 适配器基类
    
    统一接口：
    - 聊天补全
    - 结构化输出
    - Prompt 模板
    """

    @property
    @abstractmethod
    def context_window(self) -> int:
        """上下文窗口大小"""
        pass

    @property
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """是否支持结构化输出"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AdapterResult[LLMResponse]:
        """
        聊天补全
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 额外参数
            
        Returns:
            聊天响应
        """
        pass

    @abstractmethod
    async def chat_simple(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs,
    ) -> AdapterResult[str]:
        """
        简单聊天（单轮对话）
        
        Args:
            prompt: 用户提示
            system: 系统提示
            **kwargs: 额外参数
            
        Returns:
            响应文本
        """
        pass

    @abstractmethod
    async def structured_output(
        self,
        schema: dict[str, Any],
        prompt: str,
        system: str | None = None,
        **kwargs,
    ) -> AdapterResult[dict]:
        """
        结构化输出
        
        Args:
            schema: 输出模式（JSON Schema）
            prompt: 用户提示
            system: 系统提示
            **kwargs: 额外参数
            
        Returns:
            结构化数据
        """
        pass

    def build_messages(
        self,
        prompt: str,
        system: str | None = None,
        examples: list[tuple[str, str]] | None = None,
    ) -> list[LLMMessage]:
        """
        构建消息列表
        
        Args:
            prompt: 用户提示
            system: 系统提示
            examples: 示例对话 [(user, assistant), ...]
            
        Returns:
            消息列表
        """
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        if examples:
            for user_msg, assistant_msg in examples:
                messages.append(LLMMessage(role="user", content=user_msg))
                messages.append(LLMMessage(role="assistant", content=assistant_msg))
        messages.append(LLMMessage(role="user", content=prompt))
        return messages

    def estimate_tokens(self, text: str) -> int:
        """
        估算 token 数（粗略）
        
        Args:
            text: 文本
            
        Returns:
            估算的 token 数
        """
        # 粗略估算：中文约 2 字符/token，英文约 4 字符/token
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 2 + other_chars / 4)
