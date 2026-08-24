# LoomQ Starter Kit v1.1.0

本工具包定义参赛提交协议，并提供公开自测。它不包含正式评分器、隐藏答案、Mock 得分路径或任何 Level 的参考解答。

## 提交结构

```text
starter_kit/
├── __init__.py
├── VERSION
├── CHANGELOG.md
├── submission.yaml
├── adapter.py
├── llm_client.py
├── l2_policy.json
├── evaluator.py
├── prepare_submission.py
├── riscv_emulator.py
├── backend_capabilities.md
├── backend_capabilities.json
├── knowledge/                 # 编译器知识、SDK 适配说明、机器规范与权威链接索引
├── QUANTUM_101.md
├── gate_identities.md
├── target_ir_contract.md
├── requirements.txt
├── backend_requirements/     # 三个互相隔离的 SDK 完整依赖锁
├── loomq_l1/                 # 解析、规范电路、发射器、语义与 SDK 运行器
├── loomq_l2/                 # 模型解释、QASM 自验与静态后端筛选
├── hardware/                 # 可选真机证据脚本；不进入自动评测运行路径
├── Dockerfile
├── evidence/
│   ├── README.md
│   └── files/                # 可选附件
├── circuits/
│   ├── bell.qasm
│   └── ghz3.qasm
└── examples/
```

## 编译器知识库

实现 OpenQASM 解析、目标转译或 SDK 适配前，先阅读 [`knowledge/README.md`](knowledge/README.md)。知识库明确区分大赛契约、语言标准、供应商 API 与本地版本兼容行为；机器可读的 12 门白名单、目标映射和结果 Schema 位于 `knowledge/spec/`。

外部文档只用于开发期核验。正式评测不得依赖网络、Context7 或其他文档服务；运行时决策必须来自随提交归档的本地版本化文件。

在正式 fork 中，本 `starter_kit/` 目录就是构建与评测根目录，必须保留并填写 `submission.yaml`，同时提供 `adapter.py`。非 Python 项目可以在 `adapter.py` 中通过 `subprocess` 调用自己的 CLI 或二进制。

目录名使用下划线，因此从 fork 根目录编写测试时可以按标准 Python 包导入：

```python
from starter_kit import adapter
```

## 环境

L1 通用 IR 实现使用精确锁定的 `qiskit==2.5.2` 解析 OpenQASM 2。推荐 Python 3.10，与官方基础镜像一致。在 `starter_kit/` 构建根目录先安装核心依赖：

```bash
python3 -m pip install -r requirements.txt
python3 evaluator.py --level l1 --target spinq,originq,braket --json-out report.json
```

核心依赖在 `requirements.txt` 中完整锁定；三个 SDK 的完整依赖图分别位于
`backend_requirements/*.lock.txt`。它们不能安装进同一环境，因为 SpinQit 和
Braket 要求互不兼容的 ANTLR 运行时版本。

也可以先验证基础容器：

```bash
docker build -t loomq-submission .
docker run --rm loomq-submission
```

## Adapter 契约

L1 必须实现：

```python
def transpile(qasm_str: str, target: str) -> str: ...
def run(qasm_str: str, target: str, shots: int) -> dict: ...
```

`transpile()` 的三个目标格式不是任意字符串，规范子集见 `target_ir_contract.md`。正式评测会由组织方解析并模拟返回的目标 IR。

L2、L3 为可选接口：

```python
def agent_chat(prompt: str) -> str: ...
def compile_hybrid(hybrid_qasm_str: str) -> tuple[list, str]: ...
```

未参赛的 Level 保持 `NotImplementedError`，并在 `submission.yaml` 中标为 `false`。Starter Kit 原样运行会失败，这是预期行为，也确保原样提交不会获得功能分。

## 公开自测

```bash
# 默认只测试 submission.yaml 中声明为 true 的 Level
python3 evaluator.py --json-out report.json

# 单独测试
python3 evaluator.py --level l1 --target spinq,originq,braket
python3 evaluator.py --level l2
python3 evaluator.py --level l3
```

退出码：全部公开测试通过为 `0`，存在失败为 `1`。`report.json` 只表示公开契约自测结果，不是正式分数。

正式评测由组织方在隔离环境运行：每个 case 使用独立进程、私有随机种子和私有期望值；提交进程不会获得理想分布文件。组织方还会分别验证目标原生 IR、真机证据、架构与交互体验。

## L1 真机证据

评委统一入口为 [`evidence/README.md`](evidence/README.md)，其中列出两个正式申报
平台的 job ID、运行时间、shots、实际执行线路、原始结果、规范化结果与截图。
SpinQ Bell 结果的补充定位实验和完整证据链见
[`evidence/SPINQ_DIAGNOSTICS.md`](evidence/SPINQ_DIAGNOSTICS.md)。
SpinQ GHZ-3 已完成线路准备，但检查时兼容的三量子比特及以上真机均不在线；带 UTC+8
时间戳的完整平台返回见
[`evidence/files/spinq-ghz3/spinq-ghz3-platform-status.json`](evidence/files/spinq-ghz3/spinq-ghz3-platform-status.json)。
因此没有把状态检查冒充为成功真机运行。

真机任务与离线 `adapter.run()` 严格分离。使用本源悟空提交 Bell 电路并保存
task ID、SDK 原始结果和规范化结果的安全流程见
[`hardware/README.md`](hardware/README.md)。脚本只从
`LOOMQ_ORIGINQ_API_TOKEN` 读取本地凭证，只有显式传入
`--confirm-real-hardware` 才会创建消耗真实算力额度的任务。

## 最终提交

截止时间为 **2026-08-25 12:00 UTC+8**。先在 fork 根目录运行：

```bash
python3 starter_kit/prepare_submission.py --team-id <GITHUB_USERNAME>
```

当前不使用预登记队伍名单。每队指定一个 GitHub 提交账号，该账号的用户名就是 Team ID；fork 必须归该账号所有，并由同一账号创建最终提交 Issue。其他成员仍可作为协作者参与开发。预检通过后，在上游 `QAIDAO/LoomQ-2026` 的“LoomQ 最终提交” Issue Form 中填写输出的 fork 地址和 40 位 commit SHA。出现 `submission:accepted` 标签与归档哈希回执后才算提交成功。更新代码后必须新建 Issue，截止前最后一次有效提交生效。

如申报 L1 真机、L2 交互体验、工程与产品化或 Bonus，只需填写 [`evidence/README.md`](evidence/README.md)。截图、原始结果或图表可以统一放入 `evidence/files/`。证据必须随最终 commit 归档；未提交某项证据只影响对应人工分，不影响自动评分。

## L2 统一模型与环境变量

正式 L2 客观评测统一使用 DeepSeek `deepseek-v4-flash`，最终答案仍由确定性的官方测试判定，不使用 LLM 充当裁判。组委会在赛前**不提供 API 地址、API Key、代理或调用额度**。选手本地可使用自己的 DeepSeek API，也可使用其他 OpenAI-compatible 服务调试；组委会只保证正式 DeepSeek 环境下的结果。

`agent_chat(prompt: str) -> str` 接口不变。实现不得硬编码 URL、Key 或模型名，必须读取：

| 环境变量 | 含义 |
|---|---|
| `LOOMQ_LLM_BASE_URL` | OpenAI-compatible API 根地址 |
| `LOOMQ_LLM_API_KEY` | 当前运行凭证 |
| `LOOMQ_LLM_MODEL` | 当前模型；正式评测为 `deepseek-v4-flash` |
| `LOOMQ_LLM_TIMEOUT_SECONDS` | 单次请求超时 |

正式限制为每个 case 时限 120 秒；两组固定私有种子共 12 个 case。机器可读版本见 `l2_policy.json`。

`llm_client.py` 是可选的无依赖传输示例，不包含 Prompt、Agent 策略或参考答案。使用自己的 DeepSeek Key 调试时可设置：

本提交的 L2 实现位于 [`loomq_l2/`](loomq_l2/README.md)。它先完成规定的模型调用，再由本地确定性代码验证 QASM 或按 `backend_capabilities.json` 筛选后端；开发期的实时云状态不会进入正式评分路径。

```bash
export LOOMQ_LLM_BASE_URL=https://api.deepseek.com
export LOOMQ_LLM_API_KEY=<YOUR_OWN_KEY>
export LOOMQ_LLM_MODEL=deepseek-v4-flash
export LOOMQ_LLM_TIMEOUT_SECONDS=120
python3 evaluator.py --level l2
```

缺少配置时应立即失败，错误信息不得包含任何 Key。正式评测时，组委会将统一注入 DeepSeek 模型服务及调用预算；评测环境不保证能够访问其他外部网络服务。若参加 L2，请把 `submission.yaml` 中的 `levels.l2` 与 `network.required_for_l2` 同时改为 `true`；`allowed_hosts` 不用于申请正式评测中的任意公网访问。

## 版本政策

合同版本为 `1.0`。开赛后，`1.x` 只允许增加向后兼容的文档、诊断信息和公开测试，不改变已有接口语义；破坏性修改必须发布新的合同版本并为旧版保留评测通道。
