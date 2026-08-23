# Authoritative Technical Web Links

These links are for development and review. Formal evaluation must use the local contracts and specifications, not live web content.

## OpenQASM standards

| Source | Use it for |
|---|---|
| [Official OpenQASM repository](https://github.com/openqasm/openqasm) | Project governance, released specifications, examples, and reference grammars. |
| [OpenQASM 2.x branch](https://github.com/openqasm/openqasm/tree/OpenQASM2.x) | Authoritative OpenQASM 2.0 grammar and language semantics shared by the LoomQ source subset. |
| [OpenQASM live specification](https://openqasm.com/) | OpenQASM 3 language reference. Use only the subset required by the LoomQ Braket target. |
| [OpenQASM releases](https://github.com/openqasm/openqasm/releases) | Stable release identification; do not base production behavior on an unreleased development branch. |
| [Qiskit OpenQASM 2 parser API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qasm2) | Maintained `load`/`loads` parser, strict mode, include paths, and legacy `qelib1.inc` compatibility controls used by the pinned frontend. |
| [OpenQASM 2 and Qiskit guide](https://quantum.cloud.ibm.com/docs/en/guides/interoperate-qiskit-qasm2) | Official examples and guidance for importing OpenQASM 2 with Qiskit. |

## SpinQit

| Source | Use it for |
|---|---|
| [SpinQit official documentation](https://doc.spinq.cn/doc/spinqit/index.html) | Compiler, circuit, simulator, and backend API reference. |
| [SpinQit official repository](https://github.com/SpinQTech/SpinQit) | Source examples, getting-started material, and release history. |
| [SpinQit 0.2.4 package](https://pypi.org/project/spinqit/0.2.4/) | Package artifact and pinned release metadata. |

## OriginQ and pyQPanda

| Source | Use it for |
|---|---|
| [pyQPanda documentation](https://pyqpanda-toturial.readthedocs.io/zh/latest/) | CPUQVM, QASM conversion, execution, measurement, and API reference. |
| [QASM and OriginIR conversion documentation](https://pyqpanda-toturial.readthedocs.io/zh/latest/10.%E9%87%8F%E5%AD%90%E7%BA%BF%E8%B7%AF%E7%BC%96%E8%AF%91/index.html) | `convert_qasm_*`, `convert_qprog_to_qasm`, and conversion workflows. |
| [QPanda3 OriginIR specification](https://github.com/OriginQ/QPanda3-doc/blob/main/tutorials/tutorial_04_compilation/tutorial_OriginIR_cn.markdown.in) | Primary OriginIR syntax and instruction families. LoomQ uses a narrower contract. |
| [pyQPanda 3.8.5 package](https://pypi.org/project/pyqpanda/3.8.5/) | Package artifact and pinned release metadata. |
| [Origin Quantum real-computing manual](https://qcloud.originqc.com.cn/document/usermanual/rst/Computing_service1.html) | Current public hardware inventory and console-visible status fields. |
| [QPanda3 cloud service](https://qcloud.originqc.com.cn/document/qpanda-3/cn/d2/d42/tutorial_qcloud_service.html) | Official authenticated `QCloudService.backends()` discovery and cloud execution workflow. |
| [Context7 pyQPanda index](https://context7.com/originq/pyqpanda-toturial/llms.txt) | Optional focused retrieval. Verify every result against pyQPanda 3.8.5 and local tests. |

Context7 library ID: `/originq/pyqpanda-toturial`.

## Amazon Braket

| Source | Use it for |
|---|---|
| [Amazon Braket documentation](https://docs.aws.amazon.com/braket/) | Primary AWS documentation entry point. |
| [Running OpenQASM 3 on Braket](https://docs.aws.amazon.com/braket/latest/developerguide/braket-openqasm.html) | OpenQASM task construction and submission model. |
| [Supported OpenQASM features](https://docs.aws.amazon.com/braket/latest/developerguide/braket-openqasm-supported-features.html) | Braket data types, statements, measurement forms, and supported gate behavior. |
| [Testing with LocalSimulator](https://docs.aws.amazon.com/braket/latest/developerguide/braket-send-to-local-simulator.html) | Credential-free local execution workflow. |
| [Amazon Braket Python SDK repository](https://github.com/amazon-braket/amazon-braket-sdk-python) | SDK source, examples, API documentation, and local simulator integration. |
| [Amazon Braket SDK 1.110.1 package](https://pypi.org/project/amazon-braket-sdk/1.110.1/) | Package artifact and pinned release metadata. |
| [Supported regions and devices](https://docs.aws.amazon.com/braket/latest/developerguide/braket-devices.html) | Current public device names, ARNs, providers, and regions. |
| [SearchDevices API](https://docs.aws.amazon.com/braket/latest/APIReference/API_SearchDevices.html) | Authenticated device enumeration and status summaries. |
| [GetDevice API](https://docs.aws.amazon.com/braket/latest/APIReference/API_GetDevice.html) | Authenticated capabilities, operational status, and queue information. |
| [Amazon Braket pricing](https://aws.amazon.com/braket/pricing/) | Current public QPU, simulator, and reservation prices. |
| [Amazon Braket IAM actions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_braket.html) | Least-privilege distinction between discovery and task-submission permissions. |

## Refresh policy

- Prefer specifications, vendor documentation, vendor repositories, and official package registries.
- Do not promote search summaries, forum answers, or generated snippets into the local standard without primary-source and executable verification.
- Record changed sources in `sources.lock.json`.
- Keep the pinned environment unchanged until the refreshed knowledge passes all tests.
