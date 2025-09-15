# ai-fs-agent

基于大模型的文件系统智能体，借助大模型实现对文件/文件夹的智能管理，可以在“工作目录”内安全地列出、搜索、读取、写入、复制、移动、删除文件/文件夹。支持非流式与流式交互。

---

## 快速开始

### 1、环境搭建

- Python >= 3.12
- 可用的 OpenAI 兼容模型服务（如 OpenAI 或 DashScope 兼容端）

### 2、拉取本地仓库并安装依赖

- 拉取本地仓库

```bash
git clone https://github.com/Apauto-to-all/ai-fs-agent.git
cd ai-fs-agent
```

- 安装依赖

```bash
pip install -U langchain langchain-openai langgraph pydantic python-dotenv send2trash
# 可选：使用uv
uv sync
```

### 3、首次初始化

- 首次运行后，项目会自动创建配置文件：`local_config/*`

```bash
python main.py
```

### 4、配置 LLM

- 编辑 local_config/llm_models.toml，选择并路由模型
- 在 local_config/.env 写入对应 API Key

```toml
# llm_models.toml（示例片段）
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

# 路由模型，务必配置：default和fast模型
[routing]
# 默认模型（用于主Agent，务必配置）
default = "qwen_plus"
# 快速响应模型（用于子Agent，务必配置）
fast = "qwen_flash"
# 复杂推理模型
reason = "deepseek_r1"
# 图像理解模型
vision = "qwen_vl"
```

> 提示：上面的模型 ID 仅为示例，实际请以为准

```bash
# .env（示例）
DASHSCOPE_API_KEY=your_key_here
```

### 5、设置“工作目录”

- 编辑 local_config/user_config.json，设置 workspace_dir 为绝对路径（例如 D:\\workspace）
- 或在对话中执行“设置工作目录”的指令由配置代理引导输入

### 6、运行

```bash
# 非流式（逐步显示工具结果与回答）
python main.py

# 流式（实时输出规划与回答 tokens，推荐）
python main_streaming.py
```

---

## 在对话里怎么用

直接用自然语言描述你的意图（所有操作自动约束在“工作目录”内）：

- “列出根目录”
- “递归搜索包含 README 的文件路径”
- “读取 docs/guide.md 前 8 KB 内容”
- “写入 notes/todo.txt，内容为：...（允许覆盖）”
- “把 data/a.txt 复制到 backup/a.txt（覆盖）”
- “移动 logs/ 到 archive/logs_2025/”
- “删除 tmp/（递归）”

建议一次性描述清楚目标，代理会合并必要步骤，以降低模型调用次数与成本。

---

## 以 SDK 方式调用

```python
from ai_fs_agent.agents import build_supervisor_agent

agent = build_supervisor_agent()
resp = agent.invoke(
    {"messages": [{"role": "user", "content": "在工作目录创建 test/hello.txt 并写入 Hello"}]},
    config={"configurable": {"thread_id": "demo-1"}},
)
print(resp["messages"][-1].content)
```

如需更直接更低成本的文件操作，可使用文件代理：

```python
from ai_fs_agent.agents import build_fs_agent

agent = build_fs_agent()
resp = agent.invoke(
    {"messages": [{"role": "user", "content": "列出工作目录根目录"}]},
    config={"configurable": {"thread_id": "fs-1"}},
)
print(resp["messages"][-1].content)
```

---

## 安全与使用

- 严格边界：所有文件操作仅在“工作目录”内执行，越界将被拒绝
- 使用相对路径：在对话中直接写相对路径（如 docs/readme.md），无需绝对路径
- 覆盖与递归：复制/写入默认支持覆盖；删除操作统一移入系统回收站（send2trash），可递归，注意风险
- 可观测性：结构化的工具入参/出参与按天滚动日志（logs/）便于排障

---

## 常见问题

- 提示“工作目录未配置/不存在/不是文件夹”
  - 打开 local_config/user_config.json，设置 workspace_dir 为有效绝对路径
  - 或者直接告知主Agent，设置工作目录
- 模型不可用或认证失败
  - 检查 local_config/.env 的 API Key 与 llm_models.toml 的 base_url/model/routing 是否一致
- 工具未生效或响应为空
  - 确保路径在工作目录内、使用相对路径，并尽量一次性描述完整目标
- 删除行为说明
  - 删除会移入系统回收站（非物理永久删除）；如需彻底清理，请在系统回收站中手动清空

---

## 许可证

Apache-2.0，详见 [LICENSE](LICENSE)
