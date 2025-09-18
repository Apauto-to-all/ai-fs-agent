# ai-fs-agent 🚀

基于大模型的文件系统智能体，借助大模型实现对文件/文件夹的智能管理，可以在“工作目录”内安全地列出、搜索、读取、写入、复制、移动、删除文件/文件夹。支持非流式与流式交互。✨

---

## 快速开始 ⚡

### 1、环境搭建 🧩

- Python >= 3.12
- 可用的 OpenAI 兼容模型服务（如 OpenAI 或 DashScope 兼容端）
- 建议安装 Git（>= 2.x），用于版本管理与回退；若未安装，Git 功能会自动禁用，不影响文件代理使用

### 2、拉取本地仓库并安装依赖 📥

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

### 3、首次初始化 ⚙️

- 首次运行后，项目会自动创建配置文件：`local_config/*`
- 首次进行文件或 Git 操作时，会在“工作目录”内自动初始化独立 Git 仓库，并为该仓库设置本地 `user.name` 与 `user.email`
- 注意：若系统未安装 Git 或将 `use_git` 设为 `false`，项目将跳过 Git 初始化并禁用相关功能；如需恢复，请安装 Git 并在 user_config.json 中将 `use_git` 设为 `true`，或使用配置代理开启。

```bash
python main.py
```

### 4、配置 LLM 🧠

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

### 5、设置“工作目录” 🗂️

- 编辑 local_config/user_config.json，设置 workspace_dir 为绝对路径（例如 D:\\workspace）
- 或在对话中执行“设置工作目录”的指令由配置代理引导输入

### 6、运行 ▶️

```bash
# 非流式（逐步显示工具结果与回答）
python main.py

# 流式（实时输出规划与回答 tokens，推荐）
python main_streaming.py
```

---

## 在对话里怎么用 💬

直接用自然语言描述你的意图（所有操作自动约束在“工作目录”内）：

### 文件操作 📄

- “列出根目录”
- “递归搜索包含 README 的文件路径”
- “读取 docs/guide.md 前 8 KB 内容”
- “写入 notes/todo.txt，内容为：...（允许覆盖）”
- “把 data/a.txt 复制到 backup/a.txt（覆盖）”
- “移动 logs/ 到 archive/logs_2025/”
- “删除 tmp/（递归）”

### 配置管理 🔧

- “检查工作目录是否已设置并可用”
- “设置工作目录为 D:\\my_workspace”（代理会进行路径校验与二次确认）
- “查看当前是否启用 Git 管理”
- “关闭 Git 管理功能”

### 版本管理（Git） 🧾

- “查询最近 5 次操作”
- “回退到最近一次提交之前（HEAD~1）”

### 文件分类（整理） 🗃️

- “查看当前分类规则”
- “生成分类规则并整理未分类文件”
- “根据当前未分类文件进行分类整理”
- “在分类前先读取规则，然后按规则移动文件”
- “为现有规则补充与‘笔记’相关的标签并重新分类”
- “更新分类规则后重新执行整理”

说明：

- 分类流程由 classify_agent 执行：获取未分类文件 → 读取/生成规则 → 评估并增量更新规则 → 批量移动文件
- 规则文件：data/classify_rules.md（若不存在会自动生成骨架）
- 更新规则时保留所有旧块，可追加新规则或扩展标签，禁止直接删除旧规则
- 无法明确归类的文件会进入 文档/未分类/ 目录

建议一次性描述清楚目标，代理会合并必要步骤，以降低模型调用次数与成本。💡

---

## 以 SDK 方式调用 🛠️

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

使用 Git 代理（查询/回退）：

```python
from ai_fs_agent.agents import build_git_agent

agent = build_git_agent()
# 查询最近 5 个提交（内部使用 summarize_commit）
resp = agent.invoke({"messages": [{"role": "user", "content": "请查询最近 5 个提交，详细介绍"}]})
print(resp["messages"][-1].content)

# 触发回退（会进行 y/n 二次确认）
resp = agent.invoke({"messages": [{"role": "user", "content": "回退到 HEAD~1"}]})
print(resp["messages"][-1].content)
```

使用文件分类代理（自动生成 / 更新分类规则并整理文件）：

```python
from ai_fs_agent.agents import build_classify_agent

agent = build_classify_agent()
# 触发一次自动分类（含规则获取/生成与批量移动）
resp = agent.invoke(
    {"messages": [{"role": "user", "content": "对未分类文件执行一次分类整理"}]},
    config={"configurable": {"thread_id": "classify-1"}},
)
print(resp["messages"][-1].content)
```

---

## 安全与使用 🔐

- 严格边界：所有文件操作仅在“工作目录”内执行，越界将被拒绝
- 使用相对路径：在对话中直接写相对路径（如 docs/readme.md），无需绝对路径
- 覆盖与递归：复制/写入默认支持覆盖；删除操作统一移入系统回收站（send2trash），可递归，注意风险
- Git 自动化：
  - 文件变更工具成功执行后会自动提交，提交信息统一以“AI：…”前缀，便于审计
  - 支持查询最近提交与按引用回退，回退前会打印目标提交概要并要求 y/n 确认
  - Git 仓库为“工作目录”内的独立仓库，初始化/执行均限定在该目录
- 隐私与忽略：
  - `.git` 等敏感目录默认被工具层排除，不会被文件读写/遍历
- 可观测性：结构化的工具入参/出参与按天滚动日志（logs/）便于排障
- 分类安全：分类过程仅处理工作目录根层未分类文件；规则更新前进行自检并输出差异，移动操作使用相对路径并统一提交 Git 记录（若启用）

---

## 常见问题 ❓

- 提示“工作目录未配置/不存在/不是文件夹”
  - 打开 local_config/user_config.json，设置 workspace_dir 为有效绝对路径
  - 或者直接告知主Agent，设置工作目录
- 模型不可用或认证失败
  - 检查 local_config/.env 的 API Key 与 llm_models.toml 的 base_url/model/routing 是否一致
- 工具未生效或响应为空
  - 确保路径在工作目录内、使用相对路径，并尽量一次性描述完整目标
- Git 报错或无法使用
  - 确认已安装 Git 并在命令行可用；首次操作时仓库会在工作目录内自动初始化
- 删除行为说明
  - 删除会移入系统回收站（非物理永久删除）；如需彻底清理，请在系统回收站中手动清空
- 分类规则缺失
  - 首次分类会自动生成 data/classify_rules.md
- 规则未更新
  - 确认是否存在未分类文件；规则增量更新仅在发现新标签或未命中情况时发生
- 文件未被移动
  - 查看分类结果摘要，未明确归类的会放入 文档/未分类/；可补充规则标签后再次执行分类

---

## 许可证 📄

Apache-2.0，详见 [LICENSE](LICENSE)
