# LoomQ Level 2 Agent

本目录实现 `adapter.agent_chat(prompt)` 的正式评分路径。实现采用显式 Python
管道，不依赖 LangChain、LangGraph 或平台 SDK：

```text
用户 prompt
  → 至少一次注入模型调用
  → 结构化任务与约束解释
  → QASM 生成/修复，或后端筛选
  → L1 解析与无噪声语义校验
  → 最多一次模型纠正
  → 必要时对模型声明的纯态执行通用确定性合成
  → 最终文本
```

## 模块边界

- `agent.py`：模型提示、响应解析、时限和最多两次调用的状态流；
- `qasm.py`：从模型文本提取 QASM，复用 L1 严格解析器规范化，并对模型声明的
  测量分布和纯态振幅执行本地校验；若两次模型候选均错误，可将不超过 10 比特的
  稀疏目标态统一合成为 `rz`、`ry`、`cx` 门，而不是按状态名称打表；
- `backend.py`：只读取归档内的 `backend_capabilities.json`，校验模型提取的约束，
  再用确定性代码筛选和排序规范后端 ID。

后端选择不会访问 SpinQ、本源量子或 AWS，也不会读取开发期的实时观察缓存。
这样正式答案只取决于比赛规定的能力快照，不需要云账号、Cookie、API Token 或付费任务。

## 本地网页界面

从 fork 根目录启动零依赖、仅本机可访问的界面：

```bash
python -m starter_kit.loomq_l2.ui_server
```

然后打开 `http://127.0.0.1:8765`。启动器会读取当前目录的可选 `.env`，但操作系统或
评测器已经注入的同名变量优先。浏览器只与本机 Python 服务通信，不会取得或保存模型
API Key。服务拒绝非回环地址绑定、跨站请求和无会话令牌的请求。

界面支持三个主要流程：用自然语言生成量子线路、修复 OpenQASM 2.0，以及按比赛归档
能力快照选择后端。多轮对话只把最近六条消息作为上下文，并保留失败请求以便修改重试。
命令行参数见 `python -m starter_kit.loomq_l2.ui_server --help`。

### 在页面中运行线路

展开页面中的 **Local simulator lab**，可以直接粘贴 OpenQASM 2.0、选择 shots，并在
下列本地厂商 SDK 模拟器中单独运行或依次对比：

| 页面选项 | 实际执行器 | 是否提交真机任务 |
|---|---|---|
| SpinQit Basic | `spinqit` Basic Simulator | 否 |
| Origin Quantum CPU | `pyqpanda.CPUQVM` | 否 |
| Amazon Braket Local | `braket.devices.LocalSimulator` | 否 |

运行结果使用统一的 little-endian counts Schema，并在页面中显示测量分布条形图。Agent
生成且已验证的 QASM 也带有 **Run locally** 按钮，可直接送入同一个实验室。

三个 SDK 的依赖互相冲突，因此必须按 `backend_requirements/*.lock.txt` 分别安装在 fork
根目录的 `.venv-spinq`、`.venv-originq`、`.venv-braket`，Dockerfile 已自动完成这一步。
也可以分别用 `LOOMQ_SPINQ_PYTHON`、`LOOMQ_ORIGINQ_PYTHON`、
`LOOMQ_BRAKET_PYTHON` 指向对应解释器。模拟器 API 与模型 API 使用同一套本机同源、
会话令牌和请求大小保护；它不会使用 `hardware/` 中的真实设备提交路径。

## 合规性

每个非空评分 prompt 都先调用 `LOOMQ_LLM_*` 指定的 OpenAI Chat Completions
端点，再进入本地分支；不存在绕过模型的关键词答案表。模型负责理解自然语言，代码负责
验证与执行，二者都不是隐藏答案的替代品。URL、Key 和模型名不在代码中硬编码。
