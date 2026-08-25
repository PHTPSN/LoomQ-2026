# Evidence attachment index

本目录只保存人工评分证据附件。评委应先阅读上一级
[`README.md`](../README.md)，再按平台和实验进入以下目录：

| 目录 | 内容 | 状态 |
|---|---|---|
| [`originq-bell/`](originq-bell/) | 本源悟空 180 Bell：实际 OriginIR、任务记录、SDK 原始结果、规范化结果、截图 | 成功真机任务 |
| [`originq-ghz3/`](originq-ghz3/) | 本源悟空 180 GHZ-3：实际 OriginIR、任务记录、SDK 原始结果、规范化结果、截图 | 成功真机任务 |
| [`spinq-bell/`](spinq-bell/) | SpinQ Gemini Bell：能力快照、实际 QASM、任务记录、SDK 原始结果、规范化结果、截图 | 成功真机任务；结果保留原始噪声 |
| [`spinq-diagnostics/`](spinq-diagnostics/) | SpinQ Gemini 的 X⊗X、正向 X+CNOT、反向 X+CNOT 诊断及截图 | 三个成功诊断任务 |
| [`spinq-ghz3/`](spinq-ghz3/) | SpinQ GHZ-3 准备 QASM、兼容性预检、带时间戳的平台状态返回 | 未提交；兼容真机检查时不在线 |
| [`comparisons/`](comparisons/) | 同一 Bell 线路的本源量子与 SpinQ 机器可读对照 | 补充分析 |
| [`l2-robustness/`](l2-robustness/) | L2 的 36 个真实模型回答、本地语义/后端评分及配置声明 | 开发期对抗评估；不是官方隐藏案例 |
| [`quantum-riscv-gpu/`](quantum-riscv-gpu/) | LQ-Q32 机器码经模拟器解码后，在 Kaggle Tesla P100 上由开源 CuPy NVRTC Kernel 执行；包含脚本、JSON 结果和完整日志 | 成功 GPU 闭环；CPU/GPU 结果一致 |

截图用于直观辅助。正式核验仍以 job ID、平台时间、实际提交程序、SDK 原始结果和
规范化结果组成的证据链为准。目录内不得保存 API Key、Token、私钥、Cookie、
用户名或其他账户隐私。
