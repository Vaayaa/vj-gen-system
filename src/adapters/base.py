"""
VJ-Gen 适配器基类
定义所有 AI 模型适配器的统一接口
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


# ============================================================================
# 通用类型定义
# ============================================================================

T = TypeVar("T", bound=BaseModel)


class AdapterCapability(BaseModel):
    """适配器能力描述"""
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    supported_params: list[str] = Field(default_factory=list, description="支持的参数")
    limitations: list[str] = Field(default_factory=list, description="限制说明")
    estimated_latency_ms: int = Field(default=1000, description="预估延迟（毫秒）")
    cost_per_call: float = Field(default=0.0, description="每次调用成本（美元）")


class AdapterConfig(BaseModel):
    """适配器配置"""
    provider: str = Field(..., description="提供商名称")
    model: str = Field(..., description="模型名称")
    api_key: str = Field(default="", description="API Key")
    api_base: str = Field(default="", description="API 基础 URL")
    timeout: int = Field(default=60, ge=1, description="超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=4096, gt=0, description="最大 token 数")
    extra_params: dict[str, Any] = Field(default_factory=dict, description="额外参数")


class HealthStatus(BaseModel):
    """健康检查状态"""
    healthy: bool = Field(..., description="是否健康")
    latency_ms: float = Field(..., description="响应延迟（毫秒）")
    error_message: str = Field(default="", description="错误信息")
    last_check: str = Field(..., description="最后检查时间")


# ============================================================================
# 适配器结果封装
# ============================================================================


class AdapterResult(BaseModel, Generic[T]):
    """适配器调用结果封装"""
    success: bool = Field(..., description="是否成功")
    data: T | None = Field(default=None, description="返回数据")
    error: str = Field(default="", description="错误信息")
    latency_ms: float = Field(default=0.0, description="耗时（毫秒）")
    tokens_used: int = Field(default=0, description="使用的 token 数")
    model_used: str = Field(default="", description="实际使用的模型")

    @classmethod
    def ok(cls, data: T, latency_ms: float = 0, tokens_used: int = 0) -> "AdapterResult[T]":
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

    @classmethod
    def fail(cls, error: str) -> "AdapterResult[T]":
        """创建失败结果"""
        return cls(
            success=False,
            error=error,
        )


# ============================================================================
# 基础适配器抽象类
# ============================================================================


class BaseAdapter(ABC):
    """
    所有适配器的基类
    
    提供统一的接口规范，包括：
    - 配置管理
    - 健康检查
    - 能力描述
    - 调用统计
    """

    def __init__(self, config: AdapterConfig):
        """
        初始化适配器
        
        Args:
            config: 适配器配置
        """
        self.config = config
        self._stats = {
            "total_calls": 0,
            "failed_calls": 0,
            "total_latency_ms": 0.0,
            "total_tokens": 0,
        }

    @property
    @abstractmethod
    def provider(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """模型名称"""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[AdapterCapability]:
        """
        获取适配器能力列表
        
        Returns:
            能力描述列表
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        健康检查
        
        Returns:
            健康状态
        """
        pass

    @abstractmethod
    async def invoke(self, input_data: Any, **kwargs) -> Any:
        """
        调用适配器
        
        Args:
            input_data: 输入数据
            **kwargs: 额外参数
            
        Returns:
            调用结果
        """
        pass

    def get_stats(self) -> dict[str, Any]:
        """
        获取调用统计
        
        Returns:
            统计信息
        """
        avg_latency = (
            self._stats["total_latency_ms"] / self._stats["total_calls"]
            if self._stats["total_calls"] > 0
            else 0
        )
        success_rate = (
            (self._stats["total_calls"] - self._stats["failed_calls"])
            / self._stats["total_calls"]
            if self._stats["total_calls"] > 0
            else 0
        )
        return {
            **self._stats,
            "avg_latency_ms": avg_latency,
            "success_rate": success_rate,
        }

    def _record_call(
        self,
        success: bool,
        latency_ms: float,
        tokens_used: int = 0,
    ) -> None:
        """记录调用统计"""
        self._stats["total_calls"] += 1
        self._stats["total_latency_ms"] += latency_ms
        self._stats["total_tokens"] += tokens_used
        if not success:
            self._stats["failed_calls"] += 1

    def _prepare_headers(self) -> dict[str, str]:
        """准备请求头"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider} model={self.model}>"


# ============================================================================
# 异步适配器混入
# ============================================================================


class AsyncMixin:
    """异步调用支持混入类"""

    async def invoke_async(self, input_data: Any, **kwargs) -> Any:
        """异步调用"""
        raise NotImplementedError


# ============================================================================
# 批量处理支持
# ============================================================================


class BatchableMixin:
    """批量处理支持混入类"""

    async def invoke_batch(self, inputs: list[Any], **kwargs) -> list[Any]:
        """
        批量调用
        
        Args:
            inputs: 输入数据列表
            **kwargs: 额外参数
            
        Returns:
            结果列表
        """
        results = []
        for input_data in inputs:
            result = await self.invoke(input_data, **kwargs)
            results.append(result)
        return results


# ============================================================================
# 适配器注册表
# ============================================================================


class AdapterRegistry:
    """适配器注册表，用于管理所有可用适配器"""

    _adapters: dict[str, type[BaseAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_class: type[BaseAdapter]) -> None:
        """
        注册适配器
        
        Args:
            name: 适配器名称
            adapter_class: 适配器类
        """
        cls._adapters[name] = adapter_class

    @classmethod
    def get(cls, name: str) -> type[BaseAdapter] | None:
        """
        获取适配器类
        
        Args:
            name: 适配器名称
            
        Returns:
            适配器类或 None
        """
        return cls._adapters.get(name)

    @classmethod
    def list_adapters(cls) -> list[str]:
        """
        列出所有注册的适配器
        
        Returns:
            适配器名称列表
        """
        return list(cls._adapters.keys())

    @classmethod
    def create(cls, name: str, config: AdapterConfig) -> BaseAdapter | None:
        """
        创建适配器实例
        
        Args:
            name: 适配器名称
            config: 适配器配置
            
        Returns:
            适配器实例或 None
        """
        adapter_class = cls.get(name)
        if adapter_class is None:
            return None
        return adapter_class(config)
