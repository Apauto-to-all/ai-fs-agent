# llm_models.toml 文件模板
LLM_CONFIG_TEMPLATE = """# 模型配置文件模板
[models.example]
# 使用 OpenAI 兼容协议
provider = "openai-compatible"
# 兼容端暴露的模型
model = "gpt-4o"
# 替换为实际兼容端的 base_url，如 OpenAI 官方 API
base_url = "https://api.openai.com/v1"
# 从该环境变量读取 API Key
api_key_env = "OPENAI_API_KEY"
# 可选参数：透传到 ChatOpenAI 的额外配置，如超时、重试等。
extra = { timeout = 30, max_retries = 3, temperature = 0.7, max_tokens = 4096 }
# 可选参数：为该模型配置限流器
rate_limiter = { requests_per_second = 1.0, check_every_n_seconds = 0.1, max_bucket_size = 1 }

# 示例 Embedding 模型配置
[models.example_embedding]
# 使用 OpenAI 兼容协议
provider = "openai-compatible"
# 兼容端暴露的模型
model = "gpt-4o-embedding"
# 替换为实际兼容端的 base_url，如 OpenAI 官方 API
base_url = "https://api.openai.com/v1"
# 从该环境变量读取 API Key
api_key_env = "OPENAI_API_KEY"
# 可选参数：透传到 OpenAIEmbeddings 的额外配置，如超时、重试等。
extra = { timeout = 30, max_retries = 3 }

[models.qwen_plus]
provider = "openai-compatible"
model = "qwen-plus"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"

[models.qwen_flash]
provider = "openai-compatible"
model = "qwen-flash"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"

[models.deepseek_r1]
provider = "openai-compatible"
model = "deepseek-r1-0528"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"


[models.qwen_vl]
provider = "openai-compatible"
model = "qwen-vl-plus"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"

[models.qwen_embedding]
provider = "openai-compatible"
model = "text-embedding-v4"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"
# 设置 check_embedding_ctx_length = false 可以直接提供字符串输入，非token IDs
# 原因：DashScope API 不支持接收 token IDs，只接受字符串输入。
extra = { check_embedding_ctx_length = false }

[routing]
# 默认模型
default = "qwen_plus"
# 快速响应模型
fast = "qwen_flash"
# 复杂推理模型
reason = "deepseek_r1"
# 图像理解模型
vision = "qwen_vl"
# Embedding 模型
embedding = "qwen_embedding"
"""
