# LoomQ Level 2 Agent

本目录实现 `adapter.agent_chat(prompt)` 的正式评分路径。实现采用显式 Python
管道，不依赖 LangChain、LangGraph 或平台 SDK：

```text
用户 prompt
  → 至少一次注入模型调用
  → 结构化任务与约束解释
  → QASM 生成/修复，或后端筛选
  → L1 解析、测量检查与无噪声语义校验
  → 最多一次模型纠正
  → 必要时对模型声明的纯态执行通用确定性合成
  → 仅修复大小写、分号、寄存器和门操作数逗号等机械语法，并再次完整校验
  → 最终文本
```

## 模块边界

- `agent.py`：模型提示、响应解析、时限和最多两次调用的状态流；
- `qasm.py`：从模型文本提取 QASM，复用 L1 严格解析器规范化，并对模型声明的
  测量分布和纯态振幅执行本地校验；若两次模型候选均错误，可将不超过 10 比特的
  稀疏目标态统一合成为 `rz`、`ry`、`cx` 门，而不是按状态名称打表；只有目标态
  不可合成时才尝试狭窄的机械语法清理，而且清理后的线路仍必须通过同一语义校验；
- `backend.py`：只读取归档内的 `backend_capabilities.json`，校验模型提取的约束，
  再用确定性代码筛选和排序规范后端 ID。

QASM 任务必须由模型同时声明 `target_state`、`expected_distribution` 中至少一项；
仅仅语法正确不再足以通过。响应解析会跳过无关或不符合 Schema 的 JSON 对象，选取第一
个结构有效的对象。最终线路还必须包含测量，并分别通过目标态保真度或测量分布距离校验。

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

界面采用三栏工作区：左侧边栏在工具介绍、量子基础、12 门图谱和厂商模拟器之间切换；
中间只滚动当前内容；右侧 AI 对话面板始终保留，不会因教学内容过长而消失。语言开关会
完整切换全部界面、教学说明、示例 prompt、动态状态和错误恢复文字的英文版或中文版，
不会再把少量中文标签混在英文正文中。语言选择仅保存在当前浏览器的本地存储中。

**Quantum 101** 学习层先用软件工程类比解释 qubit、叠加、门与线路、测量、shots 和
纠缠，再用 Bell 线路串起 `|00⟩ → h → cx → counts`。门图谱严格来自
`knowledge/spec/gates.json`，完整覆盖比赛白名单中的 12 个门：
`h, x, s, sdg, t, tdg, rz, ry, cx, cu1, swap, ccx`。每张门卡都说明量子比特数、
直观用途、OpenQASM 写法，并可把一个完整示例直接载入 Local simulator lab。

### 在页面中运行线路

展开页面中的 **Local simulator lab**，可以直接粘贴 OpenQASM 2.0、选择 shots，并在
下列本地厂商 SDK 模拟器中单独运行或依次对比：

| 页面选项 | 实际执行器 | 是否提交真机任务 |
|---|---|---|
| SpinQit Basic | `spinqit` Basic Simulator | 否 |
| Origin Quantum CPU | `pyqpanda.CPUQVM` | 否 |
| Amazon Braket Local | `braket.devices.LocalSimulator` | 否 |

运行结果使用统一的 little-endian counts Schema，并在页面中显示测量分布条形图。页面
还会用确定性代码指出最常见的一个或两个状态及其合计占比，中英文完整切换，不额外调用
模型。Agent 生成且已验证的 QASM 也带有 **Run locally** 按钮，可直接送入同一个实验室。

三个 SDK 的依赖互相冲突，因此必须按 `backend_requirements/*.lock.txt` 分别安装在 fork
根目录的 `.venv-spinq`、`.venv-originq`、`.venv-braket`，Dockerfile 已自动完成这一步。
也可以分别用 `LOOMQ_SPINQ_PYTHON`、`LOOMQ_ORIGINQ_PYTHON`、
`LOOMQ_BRAKET_PYTHON` 指向对应解释器。模拟器 API 与模型 API 使用同一套本机同源、
会话令牌和请求大小保护；它不会使用 `hardware/` 中的真实设备提交路径。

## 36 案例鲁棒性评估

仓库提供一套可选的开发期评估包，均衡覆盖 12 个生成、12 个修复和 12 个后端选择案例。
它不是组委会未公开的 12 个隐藏案例，也不能证明官方得分；其用途是提前发现措辞、
位序、复杂振幅、损坏语法和组合约束方面的风险。正式模型配置下运行：

```powershell
.\.venv\Scripts\python.exe -m starter_kit.loomq_l2.robustness_eval `
  --env-file .env `
  --json-out starter_kit\evidence\files\l2-robustness\robustness-report.json `
  --jobs 3
```

评估器默认拒绝把其他模型冒充正式配置；只有 `LOOMQ_LLM_MODEL` 精确等于
`deepseek-v4-flash` 才运行。`--allow-other-model` 只用于明确标记的开发测试。报告不会
保存 API Key 或 Base URL。当前证据报告保存 36 个真实模型回答和本地评分，并明确写明
这是本地对抗评估而非官方隐藏案例成绩。

## 合规性

每个非空评分 prompt 都先调用 `LOOMQ_LLM_*` 指定的 OpenAI Chat Completions
端点，再进入本地分支；不存在绕过模型的关键词答案表。模型负责理解自然语言，代码负责
验证与执行，二者都不是隐藏答案的替代品。URL、Key 和模型名不在代码中硬编码。
