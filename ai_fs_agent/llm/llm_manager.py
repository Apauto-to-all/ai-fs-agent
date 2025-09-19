import os
from pathlib import Path
from typing import Dict, Optional, Any, List, Literal

import tomllib  # Python 3.11+
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI  # 使用 OpenAI 兼容协议的客户端
from langchain_openai import OpenAIEmbeddings  # 使用 OpenAI 兼容协议的嵌入模型
from langchain_core.rate_limiters import InMemoryRateLimiter
from ai_fs_agent.config import LLM_CONFIG_PATH, ENV_PATH


class LlmModelSpec(BaseModel):
    id: str
    provider: Literal["openai-compatible"] = "openai-compatible"
    model: str
    base_url: str
    api_key_env: str
    extra: Dict[str, Any] = Field(default_factory=dict)
    rate_limiter: Dict[str, Any] = Field(default_factory=dict)


class RoutingConfig(BaseModel):
    default: str  # 默认模型 ID
    fast: Optional[str] = None  # 快速响应模型 ID
    reason: Optional[str] = None  # 复杂推理模型 ID
    vision: Optional[str] = None  # 图像理解模型 ID
    embedding: Optional[str] = None  # Embedding 模型 ID


class AppConfig(BaseModel):
    models: Dict[str, LlmModelSpec]
    routing: RoutingConfig


def _load_toml_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"找不到模型配置文件: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if "models" not in data or "routing" not in data:
        raise ValueError("配置无效：需要包含 'models' 与 'routing' 段落")

    models: Dict[str, LlmModelSpec] = {}
    for mid, m in data["models"].items():
        models[mid] = LlmModelSpec(id=mid, **m)

    routing = RoutingConfig(**data["routing"])

    # 校验路由引用是否存在
    refs: List[str] = [routing.default]
    if routing.fast:
        refs.append(routing.fast)
    if routing.reason:
        refs.append(routing.reason)
    if routing.vision:
        refs.append(routing.vision)
    # 添加 embedding 引用检查
    if routing.embedding:
        refs.append(routing.embedding)
    missing = [r for r in refs if r not in models]
    if missing:
        raise ValueError(f"路由引用了不存在的模型: {missing}")

    return AppConfig(models=models, routing=routing)


class LLMManager:
    def __init__(self):
        self.config = _load_toml_config(LLM_CONFIG_PATH)
        self._cache: Dict[str, Any] = {}  # id -> LLM 实例

    def list_models(self) -> List[str]:
        return list(self.config.models.keys())

    def get_by_role(
        self,
        role: Literal["default", "fast", "reason", "vision", "embedding"] = "default",
    ):
        if role == "embedding":
            getter = self._get_embedding
        else:
            getter = self._get_model

        routing_value = getattr(self.config.routing, role)
        if not routing_value:
            raise ValueError(f"未配置默认的 {role} 模型")

        return getter(routing_value)

    # 获取指定 ID 的模型实例
    def _get_model(self, model_id: str):
        if model_id in self._cache:
            return self._cache[model_id]
        spec = self.config.models.get(model_id)
        if not spec:
            raise KeyError(f"未知的模型 ID：{model_id}")
        llm = self._build_llm(spec)
        self._cache[model_id] = llm
        return llm

    # 获取指定 ID 的 Embedding 实例
    def _get_embedding(self, model_id: str):
        if model_id in self._cache:
            return self._cache[model_id]
        spec = self.config.models.get(model_id)
        if not spec:
            raise KeyError(f"未知的模型 ID：{model_id}")
        embedding_model = self._build_embedding(spec)
        self._cache[model_id] = embedding_model
        return embedding_model

    # 构造普通 LLM 模型
    def _build_llm(self, spec: LlmModelSpec):
        # 强制要求 base_url 与 api_key_env
        if not spec.base_url:
            raise ValueError(f"模型 '{spec.id}' 需要 base_url（OpenAI 兼容）")
        if not spec.api_key_env or not os.environ.get(spec.api_key_env):
            raise ValueError(
                f"模型 '{spec.id}' 需要环境变量 '{spec.api_key_env}' 来获取 API 密钥，请在 {ENV_PATH} 中设置"
            )

        params: Dict[str, Any] = {
            "model": spec.model,
            "base_url": spec.base_url,  # 指向兼容服务
            "api_key": os.environ[spec.api_key_env],  # 从指定环境变量读取
        }

        # 透传可选参数（如 timeout/max_retries/model_kwargs 等），避免覆盖核心键
        if spec.extra:
            extra = dict(spec.extra)
            for k in ("model", "base_url", "api_key"):
                extra.pop(k, None)
            params.update(extra)

        if spec.rate_limiter:
            # 配置限流器
            rate_limiter_data = dict(spec.rate_limiter)
            rate_limiter = InMemoryRateLimiter(**rate_limiter_data)
            return ChatOpenAI(**params, rate_limiter=rate_limiter)

        return ChatOpenAI(**params)

    def _build_embedding(self, spec: LlmModelSpec):
        if not spec.base_url:
            raise ValueError(f"Embedding 模型 '{spec.id}' 需要 base_url（OpenAI 兼容）")
        if not spec.api_key_env or not os.environ.get(spec.api_key_env):
            raise ValueError(
                f"Embedding 模型 '{spec.id}' 需要环境变量 '{spec.api_key_env}' 来获取 API 密钥，请在 {ENV_PATH} 中设置"
            )

        params: Dict[str, Any] = {
            "model": spec.model,
            "base_url": spec.base_url,
            "api_key": os.environ[spec.api_key_env],
        }
        # 透传可选参数（如 dimensions/timeout 等）
        if spec.extra:
            extra = dict(spec.extra)
            for k in ("model", "base_url", "api_key"):
                extra.pop(k, None)
            params.update(extra)

        return OpenAIEmbeddings(**params)
