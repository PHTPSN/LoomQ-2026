# LoomQ 人工评分证据

这份文件是人工评分材料的统一入口。请直接编辑它，只填写要申报的项目。截图、原始结果或图表统一放在 `starter_kit/evidence/files/`，也可以引用 `starter_kit/` 中已有的代码和文档。

证据包是可选的。没有申报某项人工分时，留空即可，不影响自动评分。

## 评委快速入口

- **L1 真机申报：**本文件的[“L1 真机”](#l1-真机)部分；正式申报平台为本源量子
  和 SpinQ Cloud。
- **SpinQ 异常的可读诊断报告：**
  [`SPINQ_DIAGNOSTICS.md`](SPINQ_DIAGNOSTICS.md)。报告逐项链接实际提交 QASM、
  job ID、时间、shots、SDK 原始结果、规范化结果和登录可见的云端任务页。
- **机器可读诊断汇总：**
  [`files/spinq-diagnostics/spinq-diagnostics-report.json`](files/spinq-diagnostics/spinq-diagnostics-report.json)。
- **SpinQ 已完成任务列表截图：**
  [`files/spinq-diagnostics/spinq-diagnostics-task-list.jpg`](files/spinq-diagnostics/spinq-diagnostics-task-list.jpg)。
- **SpinQ 诊断证据目录：**[`files/spinq-diagnostics/`](files/spinq-diagnostics/)。
- **SpinQ GHZ-3 真机状态检查：**
  [`files/spinq-ghz3/spinq-ghz3-platform-status.json`](files/spinq-ghz3/spinq-ghz3-platform-status.json)。
- **附件目录索引：**[`files/README.md`](files/README.md)；正式任务分别位于
  [`originq-bell/`](files/originq-bell/)、[`originq-ghz3/`](files/originq-ghz3/)
  和 [`spinq-bell/`](files/spinq-bell/)，跨平台结果位于
  [`comparisons/`](files/comparisons/)。

最终提交 Issue 的 `Hardware evidence` 字段请填写
`starter_kit/evidence/README.md`，评委从这里即可到达全部正式证据和补充诊断材料。

## 提交前填写

把要申报项目的方框改成 `[x]`，并填写对应内容：

- [x] L1 真机
- [x] L2 交互体验
- [x] 工程与产品化
- [ ] 自定义量子 RISC-V Bonus
- [x] 新手引导与视觉叙事 Bonus

## L1 真机

每个有效真机平台计 5 分，最多两个平台。模拟器不计真机分。每个平台复制并填写一次下面的信息：

### 平台 1：本源量子

```text
平台名称：本源量子 本源悟空 180（WK_C180）
平台 job ID：FF2950C304E23CFA40F7887CDB1C14CA
运行时间：2026-08-23T18:16:22.804+08:00 至 2026-08-23T18:17:46.433+08:00（平台任务页）
shots：512
实际执行的 QASM：starter_kit/circuits/bell.qasm
云端提交的 OriginIR：starter_kit/evidence/files/originq-bell/originq-bell-executed.originir
平台返回的原始结果：starter_kit/evidence/files/originq-bell/originq-bell-sdk-result.json
规范化结果：starter_kit/evidence/files/originq-bell/originq-bell-normalized-result.json
任务记录：starter_kit/evidence/files/originq-bell/originq-bell-task.json
任务页截图：starter_kit/evidence/files/originq-bell/originq-bell-task.png
```

核验摘要：任务页显示“计算成功”、本源悟空 180、2 个量子比特、512 次重复试验、
任务耗时 0.471 秒、芯片运行时间 0.171 秒，物理量子比特映射为 `q[157]` 和
`q[166]`。截图 job ID 与 SDK 原始结果一致。平台返回概率为
`00=0.4763031`、`01=0.0001217`、`10=0.0004937`、`11=0.5230812`；
最大概率的两个态为 `00` 和 `11`，符合 Bell 态预期。规范化结果遵循大赛统一
结果 Schema，并明确标注整数 counts 由平台概率按最大余数法确定性换算。

#### 本源量子补充任务：公开 GHZ-3

```text
平台名称：本源量子 本源悟空 180（WK_C180）
平台 job ID：98E7A7BD5F53323E2B373DCF4286C497
提交时间：2026-08-23T15:22:56.753134Z
收集时间：2026-08-23T15:24:11.151230Z
shots：512
实际执行的 QASM：starter_kit/circuits/ghz3.qasm
云端提交的 OriginIR：starter_kit/evidence/files/originq-ghz3/originq-ghz3-executed.originir
平台返回的原始结果：starter_kit/evidence/files/originq-ghz3/originq-ghz3-sdk-result.json
规范化结果：starter_kit/evidence/files/originq-ghz3/originq-ghz3-normalized-result.json
任务记录：starter_kit/evidence/files/originq-ghz3/originq-ghz3-task.json
任务页截图：starter_kit/evidence/files/originq-ghz3/originq-ghz3-task.png
```

核验摘要：任务状态为 `FINISHED`，实际映射线路与公开 GHZ-3 一致，物理量子比特
映射为 `q[157]`、`q[166]` 和 `q[176]`。平台返回 `000=0.4867053`、
`111=0.5117907`，两个理想支持态合计概率为 `0.998496`；其余六个状态合计
`0.001504`。Top-K 为 `000` 和 `111`，通过真机主峰核验。平台原始元数据显示
任务总耗时 61.729 秒、QPU 运行时间 0.169 秒。

### 平台 2：SpinQ Cloud

```text
平台名称：SpinQ Cloud 2 Qubits NMR（gemini_vp）
平台 job ID：G-260823-0014（内部任务 ID 61451）
运行时间：2026-08-23 22:33:33 至 2026-08-23 22:35:07（平台任务页，UTC+8）
shots：1000
原始公开 QASM：starter_kit/circuits/bell.qasm
云端实际执行 QASM：starter_kit/evidence/files/spinq-bell/spinq-bell-executed.qasm
提交前平台能力快照：starter_kit/evidence/files/spinq-bell/spinq-bell-gemini-preflight.json
平台返回的原始结果：starter_kit/evidence/files/spinq-bell/spinq-bell-sdk-result.json
规范化结果：starter_kit/evidence/files/spinq-bell/spinq-bell-normalized-result.json
任务记录：starter_kit/evidence/files/spinq-bell/spinq-bell-task.json
任务页截图：starter_kit/evidence/files/spinq-bell/spinq-bell-task.png
```

核验摘要：任务页显示 `Success`、2 Qubits NMR、来源 `spinqit`，任务编号、
创建时间、开始时间和结束时间与保存记录一致。MCP 固定执行 1000 shots，返回概率为
`00=0.39588674`、`01=0.27626729`、`10=0.05157868`、`11=0.27626729`。
规范化文件使用最大余数法换算为整数 counts 并保持总和为 1000。该次真机结果中
理想 Bell 支持态 `00` 与 `11` 的合计概率为 `0.67215403`，分布保真度为
`0.6667892113380465`；由于 `01` 与 `11` 并列，未通过“概率最高的两个态必须为
`00` 和 `11`”这一较严格的内部核验条件。原始结果未作筛选或修改。

跨平台对照分析：
[`files/comparisons/bell-cross-platform-comparison.json`](files/comparisons/bell-cross-platform-comparison.json)。
同一公开 Bell 线路在本源悟空 180 上的理想支持态概率为 `0.9993843`，在 SpinQ
`gemini_vp` 上为 `0.67215403`。该对照强烈排除共享源线路和规范 IR 语义作为主因，
并把差异定位到 SpinQ 特有的执行链路；但仅凭此证据无法进一步区分 SpinQ 云编译、
量子比特映射、设备校准、门误差、状态制备误差或测量误差。

#### SpinQ Gemini 诊断任务

为定位 Bell 偏差，额外提交了三个确定性诊断线路；完整汇总见
[`SPINQ_DIAGNOSTICS.md`](SPINQ_DIAGNOSTICS.md)，机器可读汇总见
[`files/spinq-diagnostics/spinq-diagnostics-report.json`](files/spinq-diagnostics/spinq-diagnostics-report.json)。每个任务的
提交 QASM、任务记录、SDK 原始结果和规范化结果均使用 `spinq-diag-*` 文件名前缀
保存在 [`files/spinq-diagnostics/`](files/spinq-diagnostics/)；任务列表截图和三个
独立任务页截图显示全部诊断任务均为 `Success`。

- `G-260823-0015`：`X⊗X`，理想结果为 `11=1`，实际四个状态各为 `0.25`，失败。
- `G-260823-0017`：正向 `X+CNOT`，`11=0.72389876`，主导态通过。
- `G-260823-0018`：反向 `X+CNOT`，`11=0.67038918`，主导态通过。

两个 CNOT 方向均能驱动预期主导态，因此 Bell 偏差不是简单的 CNOT 操作数反转。
异常在不含 CNOT 和叠加态的 `X⊗X` 基线中已经出现，问题被定位到 LoomQ 发射之后
的 SpinQ 特有执行链路。现有接口无法进一步区分云端编译或调度、NMR 状态制备、
设备校准、测量或结果重建。

#### SpinQ GHZ-3 状态检查（未提交任务）

公开 GHZ-3 线路需要 3 个量子比特。2026-08-24 00:40:25 至 00:40:35
（UTC+8）通过 SpinQ MCP `get_platforms` 检查真机状态：唯一在线的
`gemini_vp` 只有 2 个量子比特；可执行该线路的 `triangulum_vp`、
`hercules_vp` 均返回 `countOnlineMachine=0`。`superconductor_vp` 的量子比特数量
足够但同样离线，而且此次返回的门列表没有声明 CNOT。

因此没有创建可能无限期排队的任务，也不把这次检查申报为一次成功真机运行。
已保存的可复核材料如下：

- 平台状态完整返回及检查时间：
  [`files/spinq-ghz3/spinq-ghz3-platform-status.json`](files/spinq-ghz3/spinq-ghz3-platform-status.json)
- 针对 `triangulum_vp` 的兼容性预检：
  [`files/spinq-ghz3/spinq-ghz3-triangulum-preflight.json`](files/spinq-ghz3/spinq-ghz3-triangulum-preflight.json)
- 已通过本地验证、等待平台上线的实际提交 QASM：
  [`files/spinq-ghz3/spinq-ghz3-executed.qasm`](files/spinq-ghz3/spinq-ghz3-executed.qasm)

建议按平台和实验把附件放入 `evidence/files/` 的子目录，例如：

```text
evidence/files/spinq-bell/spinq-bell-executed.qasm
evidence/files/spinq-bell/spinq-bell-sdk-result.json
evidence/files/spinq-bell/spinq-bell-task.png
```

工作人员会核对 job ID、运行时间、电路、shots 和原始结果。截图只能辅助说明，不能代替 job ID 和原始结果。

## L2 交互体验

请填写：

```text
启动界面或 CLI 的命令：python -m starter_kit.loomq_l2.ui_server
测试入口或页面地址：http://127.0.0.1:8765
用于交互体验评测的 3 个用户任务：
1. Create a three-qubit GHZ state and measure every qubit.
2. I intended to prepare and measure a Bell state, but this is broken: H q[0]; CX q[0] q[1]. Repair the complete OpenQASM 2.0 program.
3. I need to run a 26-qubit circuit with no queue and no account. Which backend should I use?
截图或演示视频：无；评委可按上述命令直接运行完整交互流程。
```

界面首先给出三个可点击任务，明确区分生成、修复和后端推荐。QASM 结果使用等宽代码区并
标明已经本地解析和验证；错误会解释恢复方法并把原 prompt 留在输入框中。最近六条对话
作为后续请求的上下文。模型 Key 不进入浏览器，服务仅监听 IPv4 回环地址并校验同源请求。
页面还提供可直接粘贴代码的 Local simulator lab，并能在 SpinQit、pyQPanda 和 Amazon
Braket 三个本地 SDK 模拟器间单独运行或依次对比。测量 counts 会显示为百分比条形图；
此路径不会提交真实硬件任务，也不需要任何云平台账号。

工作人员会在组委会统一模型环境中运行最终代码，测试新手是否看得懂、出错后能否得到有效帮助、结果是否清楚，以及多轮回答是否一致。选手自己的对话截图只用于说明产品流程，不直接证明得分。

## 工程与产品化

已有内容可以直接引用主 README 或其他项目文档，不必复制到本目录。

```text
干净环境中的构建和启动命令：starter_kit/README.md 的“环境”和“L2 统一模型与环境变量”；界面命令为 python -m starter_kit.loomq_l2.ui_server
架构说明：starter_kit/loomq_l2/README.md；浏览器 SPA → 本机 Python HTTP 边界 → agent_chat → 模型解释与确定性本地验证
目标用户和使用场景：不了解 OpenQASM 或云量子平台约束的初学者；生成或修复小型线路，并根据比赛能力快照选择可用后端
完整使用流程：starter_kit/loomq_l2/README.md 的“本地网页界面”，以及页面内三个引导任务
```

工作人员会按最终 commit 实际构建和启动，并检查文档与代码是否一致、产品是否真的降低了量子计算的使用门槛。

## 自定义量子 RISC-V Bonus

以下三项必须齐全且测试通过，才获得 8 分：

```text
指令编码规格：[填写文档路径]
模拟器扩展实现：[填写代码路径]
端到端测试命令：[填写命令或文档路径]
```

## 新手引导与视觉叙事 Bonus

请填写已有材料的路径，不要求为评分另写一套文档：

```text
零基础首次运行指南：starter_kit/loomq_l2/README.md 的“本地网页界面”和“在页面中运行线路”
量子概念解释：starter_kit/QUANTUM_101.md；页面内 Understand → Build → Verify → Compare 四步引导
结果可视化：Local simulator lab 把三个厂商本地模拟器的测量 counts 显示为态、次数和百分比条形图
错误恢复或无障碍引导：失败 prompt 保留在输入框；模拟器逐平台显示错误且继续其余对比；语义化 label、aria-live、键盘提交和 prefers-reduced-motion
```

以上四项各 1 分。普通项目 README 完整不代表自动获得 Bonus。

## 提交规则

- 所有材料都要在截止前进入最终提交的 commit，工作人员不接受截止后补交。
- 外部视频可以用稳定只读链接，源码、原始结果和复现命令应保存在仓库中。
- 整个 fork commit 的归档包不得超过 100 MiB。
- 不要提交 API Key、Token、Cookie、个人身份信息或平台账户隐私。
- 如申报 L1 真机分，在最终提交 Issue 的 `Hardware evidence` 中填写 `starter_kit/evidence/README.md`。
