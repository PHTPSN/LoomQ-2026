const conversation = document.querySelector("#conversation");
const composer = document.querySelector("#composer");
const input = document.querySelector("#prompt-input");
const sendButton = document.querySelector("#send-button");
const starterPrompts = document.querySelector("#starter-prompts");
const statusElement = document.querySelector("#service-status");
const statusText = document.querySelector("#service-status-text");
const backendStatusRows = Array.from(document.querySelectorAll("[data-backend-status]"));
const clearButton = document.querySelector("#clear-button");
const template = document.querySelector("#message-template");
const contentStage = document.querySelector("#content-stage");
const runnerForm = document.querySelector("#runner-form");
const qasmInput = document.querySelector("#qasm-input");
const simulatorTarget = document.querySelector("#simulator-target");
const simulatorShots = document.querySelector("#simulator-shots");
const runButton = document.querySelector("#run-button");
const simulationResults = document.querySelector("#simulation-results");
const translationTarget = document.querySelector("#translation-target");
const translationButton = document.querySelector("#translation-button");
const irOutput = document.querySelector("#l1-ir-output");
const translationOutput = document.querySelector("#l1-translation-output");
const hybridForm = document.querySelector("#hybrid-form");
const hybridInput = document.querySelector("#hybrid-input");
const hybridButton = document.querySelector("#hybrid-button");
const hybridQuantumOutput = document.querySelector("#hybrid-quantum-output");
const hybridAssemblyOutput = document.querySelector("#hybrid-assembly-output");
const hybridMachineOutput = document.querySelector("#hybrid-machine-output");
const hybridDecodedOutput = document.querySelector("#hybrid-decoded-output");
const workspace = document.querySelector(".workspace");
const railToggle = document.querySelector("#rail-toggle");
const promptResizeHandle = document.querySelector("#composer-resize-handle");
const assistantDock = document.querySelector("#assistant-dock");
const assistantHideButton = document.querySelector("#assistant-hide-button");
const assistantLauncher = document.querySelector("#assistant-launcher");
const hardwareTabButtons = Array.from(document.querySelectorAll("[data-hardware-tab]"));
const hardwareTabPanels = Array.from(document.querySelectorAll("[data-hardware-panel]"));
const evidenceModeButtons = Array.from(document.querySelectorAll("[data-evidence-mode]"));
const evidenceModePanels = Array.from(document.querySelectorAll("[data-evidence-panel]"));
const gpuTutorButtons = Array.from(document.querySelectorAll("[data-gpu-step]"));
const gpuTutorPanels = Array.from(document.querySelectorAll("[data-gpu-panel]"));
const historyList = document.querySelector("#history-list");
const historyEmpty = document.querySelector("#history-empty");

const chinese = {
  "aria.workspace": "工作区导航",
  "aria.language": "语言",
  "aria.tools": "学习工具",
  "aria.conversation": "对话",
  "aria.backends": "本地执行后端状态",
  "brand.tagline": "量子新手指南",
  "nav.overview": "工具介绍",
  "nav.guide": "新手导引",
  "nav.learn": "量子基础教学",
  "nav.gates": "支持的 12 种门",
  "nav.simulator": "厂商模拟器",
  "nav.hybrid": "混合编译器",
  "nav.evidence": "执行证据",
  "nav.history": "对话记录",
  "rail.backends": "本地后端",
  "overview.eyebrow": "01 · 工具介绍",
  "overview.title1": "从一句自然语言想法",
  "overview.title2": "到一条可以运行的量子线路。",
  "overview.lede": "LoomQ 帮助新手理解任务、编写或修复 OpenQASM、在本地验证线路，并对比三个厂商模拟器。",
  "overview.askTitle": "直接说出目标",
  "overview.askBody": "描述你希望得到的结果，不需要先掌握量子门语法或后端名称。",
  "overview.verifyTitle": "使用前先验证",
  "overview.verifyBody": "生成的 QASM 会先经过本地解析和模拟，验证通过后才会作为有效结果展示。",
  "overview.runTitle": "无需云端费用",
  "overview.runBody": "通过 SpinQit、本源量子和 Amazon Braket 的本地 SDK 模拟器测试 counts。",
  "overview.intentLabel": "你的目标",
  "overview.intentValue": "“创建一个 Bell 对”",
  "overview.loomqValue": "构建 + 验证",
  "overview.resultLabel": "结果",
  "overview.resultValue": "QASM + 测量 counts",
  "overview.boundaryTitle": "模拟器不等于真实量子硬件。",
  "overview.boundaryBody": "模拟器页面只在这台电脑上运行厂商 SDK，绝不会提交付费真机任务。",
  "guide.eyebrow": "02 · 新手导引",
  "guide.title": "新手导引",
  "learn.eyebrow": "03 · 量子基础教学",
  "learn.title1": "理解八个概念，",
  "learn.title2": "从向量读懂量子线路。",
  "learn.lede": "从熟悉的线性代数出发：量子线路把一个复向量依次乘以若干矩阵；测量再把向量坐标的模平方作为概率，随机返回一个比特串。",
  "learn.vectorTitle": "一个量子比特就是一个向量",
  "learn.vectorBody": "一个量子比特用长度为 2 的复向量表示，这个向量称为它的状态。|ψ⟩ 只是该向量的名字。固定向量 |0⟩=[1,0]ᵀ 和 |1⟩=[0,1]ᵀ 组成计算基，也就是测量可能报告的两个结果。",
  "learn.amplitudeTitle": "振幅决定概率",
  "learn.amplitudeBody": "复数 α 和 β 称为振幅，但它们本身不是概率。测得 0 和 1 的概率分别为 |α|² 和 |β|²。有效状态的总概率必须等于 1。如果多个振幅都不为零，这个状态就称为这些基向量的叠加。",
  "learn.registerTitle": "更多量子比特意味着更多坐标",
  "learn.registerBody": "两个量子比特使用长度为 4 的向量，四个坐标命名为 |00⟩、|01⟩、|10⟩ 和 |11⟩。组合彼此独立的量子比特要使用 Kronecker 积，记作 ⊗：把第一个向量的每个坐标分别乘以第二个向量的每个坐标。每增加一个量子比特，向量长度就翻倍。",
  "learn.gateTitle": "量子门就是矩阵",
  "learn.gateBody": "量子门通过矩阵乘法更新状态。这个矩阵是酉矩阵：U†U=I，其中 U† 表示 U 的共轭转置。它不会改变向量长度，并且应用 U† 可以撤销 U。量子线路就是这些矩阵操作按顺序组成的程序。",
  "learn.phaseTitle": "相位控制干涉",
  "learn.phaseBody": "复数振幅既有大小也有角度；这个角度称为相位。相位本身不会改变当前坐标的概率，但后续量子门可以把坐标相加：方向相同的振幅会增强，方向相反的振幅会抵消。这个过程称为干涉。",
  "learn.measureTitle": "测量会选择一个结果",
  "learn.measureBody": "测量会从计算基标签中随机选择一个，例如 00 或 11。某个标签被选中的概率等于对应坐标模的平方。测量会把选中的标签作为普通比特串返回；读取后，状态变为被选中的基向量。",
  "learn.shotsTitle": "一次 shot 就是一次完整运行",
  "learn.shotsBody": "一次 shot 会创建处于 |0…0⟩ 的全新量子比特，按顺序执行全部量子门，然后测量一次。N 次 shots 会从头重复整个过程 N 次。counts 是每个返回比特串及其出现次数组成的映射。",
  "learn.entangleTitle": "纠缠就是无法分解",
  "learn.entangleBody": "如果一个多量子比特状态不能写成若干单量子比特状态的 Kronecker 积，它就是纠缠态。在下面的 Bell 态中，两个量子比特都没有各自独立的向量，因此测量一个比特会限制另一个比特的结果。",
  "learn.storyEyebrow": "实际运用上述定义",
  "learn.storyTitle": "计算一个 Bell 对",
  "learn.storyBody": "Bell 对是一种双量子比特纠缠态，测量得到的两个比特完全相关：本例只会返回 00 或 11，并且两者概率都是 1/2。计算时，用 |q₁q₀⟩ 顺序书写标签。H 门让 q₀ 得到两个大小为 1/√2 的振幅，CX 只在 q₀=1 的坐标中翻转 q₁。",
  "learn.start": "初始化",
  "learn.known": "两个量子比特都从 0 开始",
  "learn.gate": "对 q₀ 应用 H 门",
  "learn.paths": "两个非零坐标",
  "learn.link": "应用 CX 门",
  "learn.entangle": "无法分解成两个向量",
  "learn.measure": "测量",
  "learn.correlated": "只会出现两个比特相同的结果",
  "learn.bitOrderTitle": "一个重要约定",
  "learn.bitOrderBody": "在结果键“10”中，最右侧字符对应 c[0]。LoomQ 会把所有后端统一成这种小端位序。",
  "gates.eyebrow": "04 · 官方门集",
  "gates.title1": "十二种门，",
  "gates.title2": "就是完整词汇表。",
  "gates.lede": "竞赛隐藏用例同样只使用这份白名单。θ 表示以弧度为单位的旋转角度；“dg”表示该门的逆操作。",
  "gates.single": "单量子比特门",
  "gates.phase": "相位与旋转门",
  "gates.multi": "受控与多量子比特门",
  "gates.oneQubit": "1 量子比特",
  "gates.twoQubits": "2 量子比特",
  "gates.threeQubits": "3 量子比特",
  "gates.matrix": "矩阵",
  "gates.try": "试运行这个门",
  "gate.h.title": "Hadamard 门",
  "gate.h.body": "产生或重新合并等权重量子路径，是进入叠加态最常用的入口。",
  "gate.x.title": "比特翻转门",
  "gate.x.body": "交换 |0⟩ 和 |1⟩，相当于经典逻辑中的 NOT。",
  "gate.s.title": "四分之一相位门",
  "gate.s.body": "给 |1⟩ 分量增加 90° 相位；需要通过干涉才能观察到这个隐藏变化。",
  "gate.sdg.title": "S 的逆门",
  "gate.sdg.body": "施加相反的 −90° 相位；dagger 表示逆操作。",
  "gate.t.title": "八分之一相位门",
  "gate.t.body": "增加更细的 45° 相位，是构造通用量子算法的重要基础门。",
  "gate.tdg.title": "T 的逆门",
  "gate.tdg.body": "施加 −45° 相位，直接放在 T 门之后可以撤销 T 的作用。",
  "gate.rz.title": "Z 轴旋转",
  "gate.rz.body": "按角度 θ 改变相位；即使直接测量概率不变，它仍会改变后续干涉。",
  "gate.ry.title": "Y 轴旋转",
  "gate.ry.body": "按 θ 旋转振幅，直接改变测量得到 0 或 1 的概率。",
  "gate.cx.title": "受控 X 门",
  "gate.cx.body": "仅当控制位为 1 时翻转目标位；与 H 门组合即可产生纠缠。",
  "gate.cu1.title": "受控相位门",
  "gate.cu1.body": "仅当两个量子比特都为 1 时增加相位 θ，常见于量子傅里叶线路。",
  "gate.swap.title": "交换门",
  "gate.swap.body": "在不测量的情况下交换两个量子比特的完整状态。",
  "gate.ccx.title": "Toffoli 门",
  "gate.ccx.body": "仅当两个控制位都为 1 时翻转目标位，可用于构造可逆经典逻辑。",
  "sim.eyebrow": "05 · 厂商模拟器",
  "sim.title": "在本地运行 OpenQASM。",
  "sim.lede": "选择一个 SDK，或依次对比三个 SDK。每次 shot 中，LoomQ 都会创建处于 |0…0⟩ 的全新量子比特，执行一遍全部量子门，并记录一个测量得到的比特串。",
  "sim.lab": "本地模拟实验室",
  "sim.program": "OpenQASM 2.0 程序",
  "sim.simulator": "模拟器",
  "sim.all": "对比全部三个模拟器",
  "sim.shots": "Shots",
  "sim.run": "在本地运行",
  "sim.privacy": "无需账号、付款或排队，也不会提交任何真实硬件任务。",
  "sim.vendor.spinq": "量旋科技 SpinQ",
  "sim.vendor.origin": "本源量子",
  "l1.target": "翻译目标",
  "l1.optional": "查看 IR 与 SDK 翻译",
  "l1.translate": "显示 IR 与 SDK 翻译",
  "l1.note": "IR 会去除源程序中的寄存器名称，同时保留量子比特索引、经典比特写入位置、参数和指令顺序。",
  "l1.ir": "规范化 IR",
  "l1.output": "SDK 翻译",
  "l1.awaiting": "选择此功能后即可查看线路 IR。",
  "l1.awaitingOutput": "选择目标后即可查看对应的准确语法。",
  "hybrid.eyebrow": "06 · 混合编译器",
  "hybrid.title1": "量子操作保持顺序，",
  "hybrid.title2": "经典决策编译为 RISC-V。",
  "hybrid.lede": "Hybrid-QASM 在 OpenQASM 2.0 线路中加入一个 classical { … } 代码块。LoomQ 会分离两类职责：量子门与测量保持为有序操作流，整数赋值和 if/else 决策则转换成确定性的 RISC-V 指令。",
  "hybrid.step1Title": "读取 Hybrid-QASM",
  "hybrid.step1Body": "普通量子指令围绕一个 classical 代码块排列。测量表达式使用 c[n]，可写整数值使用 r1、r2 等名称。",
  "hybrid.step2Title": "保持量子顺序",
  "hybrid.step2Body": "量子门和测量会被规范化为与线路翻译器相同的标准指令顺序。",
  "hybrid.step3Title": "降低经典逻辑",
  "hybrid.step3Body": "测量比特依次进入 RISC-V 寄存器 x10、x11 等位置。赋值和分支会被编译成一段精简且可执行的汇编程序。",
  "hybrid.program": "Hybrid-QASM 程序",
  "hybrid.note": "编译过程是确定性的，并且完全在本地完成：不会调用 AI 模型或云端服务。",
  "hybrid.compile": "编译 Hybrid-QASM",
  "hybrid.quantumOutput": "量子操作流",
  "hybrid.classicalOutput": "精简 RISC-V 汇编",
  "hybrid.awaitingQuantum": "编译示例后即可列出量子操作。",
  "hybrid.awaitingAssembly": "编译后的经典指令将显示在这里。",
  "hybrid.binaryTitle": "量子操作会成为真正的 32 位指令字。",
  "hybrid.binaryBody": "custom-0 操作码 0x0B 进入最小可执行闭环：编码、解码，再恢复模拟器执行的操作语义。",
  "hybrid.machineOutput": "LQ-Q32 机器码",
  "hybrid.decodedOutput": "解码执行轨迹",
  "hybrid.awaitingMachine": "编码后的 32 位指令字将显示在这里。",
  "hybrid.awaitingDecoded": "解码后的操作将显示在这里。",
  "evidence.eyebrow": "07 · 执行证据",
  "evidence.title1": "两条执行路径，",
  "evidence.title2": "一份可审计记录。",
  "evidence.lede": "在物理量子真机任务与带有归档 GPU 验证的自定义量子 RISC-V 路径之间切换。每项结论都会链接到支持它的证据文件。",
  "evidence.modeHardware": "量子真机",
  "evidence.modeHardwareMeta": "本源 · SpinQ · AWS 指南",
  "evidence.modeRiscv": "量子 RISC-V + GPU",
  "evidence.modeRiscvMeta": "LQ-Q32 · CUDA 证据",
  "gpu.title": "一条真正可运行的 32 位量子指令路径。",
  "gpu.lede": "LoomQ 将 L3 量子操作流转换为 LQ-Q32 指令字，再解码并执行恢复出的语义。另一次 Kaggle 运行在 NVIDIA GPU 上验证了解码后的 GHZ 工作负载。",
  "gpu.requirementsEyebrow": "最小闭环",
  "gpu.requirementsTitle": "Bonus 基础要求已端到端连接。",
  "gpu.req1Title": "编码规范",
  "gpu.req1Body": "两种经过验证的 32 位格式使用 RISC-V custom-0 操作码 0x0B，并明确表示量子比特、量子门、角度和测量字段。",
  "gpu.req2Title": "机器码解码器",
  "gpu.req2Body": "模拟器接收十六进制指令字、检查保留字段，并重建可执行的量子操作。",
  "gpu.req3Title": "完整白名单覆盖",
  "gpu.req3Body": "全部 12 种允许的门和测量均通过编码/解码测试，包括参数量化和非法指令拒绝。",
  "gpu.req4Title": "GPU 验证",
  "gpu.req4Body": "一次私有 Kaggle 运行在 Tesla P100 上使用 CuPy NVRTC 内核运行解码后的 GHZ 子集，并与 CPU 结果比较。",
  "gpu.tutorEyebrow": "GPU 教程",
  "gpu.tutorTitle": "跟随一个 GHZ 程序经历五次转换。",
  "gpu.tutorLede": "选择一个步骤，查看发生了什么变化、什么保持不变，以及哪份文件提供证明。",
  "gpu.step1": "Hybrid-QASM",
  "gpu.step1Meta": "源程序语义",
  "gpu.step2": "LQ-Q32 指令字",
  "gpu.step2Meta": "二进制编码",
  "gpu.step3": "解码字段",
  "gpu.step3Meta": "恢复含义",
  "gpu.step4": "CUDA / NVRTC",
  "gpu.step4Meta": "GPU 执行",
  "gpu.step5": "CPU ↔ GPU",
  "gpu.step5Meta": "验证一致性",
  "gpu.sourceKicker": "输入",
  "gpu.sourceTitle": "从操作语义开始，而不是硬件细节。",
  "gpu.sourceBody": "GHZ 线路使用 H 和两个 CX 门创建三量子比特叠加态，然后测量所有量子比特。L3 按原顺序保留这些操作。",
  "gpu.wordsKicker": "编码",
  "gpu.wordsTitle": "每个操作变成一个无符号 32 位指令字。",
  "gpu.wordsBody": "最低七位承载 custom-0 操作码 0x0B。基础门使用 funct7，操作数使用 rd、rs1 和 rs2。",
  "gpu.decodeKicker": "解码",
  "gpu.decodeTitle": "恢复语义前先验证所有字段。",
  "gpu.decodeBody": "opcode 选择扩展，funct3 选择格式，funct7 或立即数识别操作。非法操作码、未知功能、重复量子比特和非零保留字段都会被拒绝。",
  "gpu.cudaKicker": "执行",
  "gpu.cudaTitle": "解码后的门驱动原生 GPU 内核。",
  "gpu.cudaBody": "CuPy 通过 NVRTC 在运行时编译 CUDA C 内核。归档运行把解码后的 H 和 CX 应用于复数状态向量，并在 Tesla P100 上计算测量概率。",
  "gpu.verifyKicker": "核验",
  "gpu.verifyTitle": "独立的 CPU 和 GPU 路径结果一致。",
  "gpu.verifyBody": "两条路径在 4,096 shots 下都返回理想 GHZ 分布。最大概率差异接近浮点舍入误差。",
  "gpu.archived": "已归档 · 通过",
  "gpu.proofTitle": "私有 Kaggle GPU 验证",
  "gpu.device": "设备",
  "gpu.memory": "GPU 显存",
  "gpu.coverage": "编码覆盖范围",
  "gpu.coverageValue": "12 种门 + 测量",
  "gpu.executed": "GPU 执行子集",
  "gpu.resultJson": "证据 JSON",
  "gpu.runLog": "完整运行日志",
  "gpu.validationScript": "验证脚本",
  "gpu.boundaryTitle": "这项结果证明什么，以及不证明什么",
  "gpu.boundaryBody": "完整指令集在 CPU 上完成编码和解码。归档 GPU 运行只执行 GHZ 所需的 H、CX 和测量；它不声称每个门都有专用 CUDA 内核，也不会把 GPU 描述成量子真机。",
  "evidence.definitionTitle": "这里的“真机证据”是什么意思",
  "evidence.definitionBody": "厂商记录显示：一个任务已在指定的物理量子机器上完成。“统一格式”表示 LoomQ 把厂商结果转换为共同的 counts 格式；原始响应仍与转换结果一同保留。",
  "evidence.originBell": "Bell 对 · 本源悟空 180",
  "evidence.spinqBell": "Bell 对 · Gemini 核磁共振设备",
  "evidence.verified": "已核验",
  "evidence.noisy": "已记录 · 噪声较大",
  "evidence.openScreenshot": "打开任务截图 ↗",
  "evidence.jobId": "任务编号",
  "evidence.shots": "运行次数",
  "evidence.finished": "平台完成时间",
  "evidence.originReading": "的厂商概率落在 Bell 对应有的 00 和 11 结果上。",
  "evidence.spinqReading": "落在 00 和 11 上。LoomQ 保留了意外出现的 01 和 10，而没有把它们隐藏。",
  "evidence.taskRecord": "任务记录",
  "evidence.executedProgram": "实际执行程序",
  "evidence.rawResult": "原始结果",
  "evidence.normalizedResult": "统一格式结果",
  "evidence.ghzTitle": "第二次悟空 180 真机运行",
  "evidence.ghzBody": "任务 98E7…C497 共运行 512 次。预期的 000 与 111 合计占厂商概率的 99.85%。",
  "evidence.viewGhz": "查看 GHZ-3 任务截图 ↗",
  "evidence.diagnosticTitle": "我们调查了这个高噪声结果",
  "evidence.diagnosticBody": "三个后续任务表明，仅仅调换 CNOT 的两个操作数无法解释 Bell 结果差异。现有云端接口无法进一步区分编译、映射、校准、初态制备和测量等因素。",
  "evidence.viewDiagnostics": "打开诊断报告 ↗",
  "evidence.notRunTitle": "已准备，但没有提交",
  "evidence.notRunBody": "记录状态时，唯一在线的机器只有两个量子比特。LoomQ 没有把离线的三量子比特机器伪装成成功运行。",
  "evidence.tutorialEyebrow": "真机实验教程",
  "evidence.tutorialTitle": "学习三个平台各自的安全流程。",
  "evidence.tutorialLede": "这个网站绝不会提交真机任务。以下教程会解释每一步的含义、可以使用的项目资源，以及只读操作从哪里开始变成会消耗配额的云端提交。",
  "evidence.safetyTitle": "三个平台共同遵守的规则",
  "evidence.safetyBody": "先在线路模拟器中运行线路；然后刷新真机的当前状态，检查它支持的量子比特数量和量子门，核对价格或配额，并获得账号所有者批准。凭证只能存放在被忽略的本地配置中，不能进入本页面、截图、证据文件或 Git。",
  "evidence.tabOrigin": "本源量子",
  "evidence.tabSpinq": "量旋科技 SpinQ",
  "evidence.originLessonTitle": "从本地验证的线路到一个妥善保存的真机任务",
  "evidence.originLessonLede": "后端是接收线路的指定机器。预检会在提交前读取可用后端列表，不会消耗真机配额。",
  "evidence.originStep1": "先在本地验证线路",
  "evidence.originStep1Body": "首先使用“厂商模拟器”页面运行线路，再打开其中的可选翻译面板，检查本源量子格式，然后再接触云端。",
  "evidence.originStep2": "配置账号访问",
  "evidence.originStep2Body": "在本源量子账号中心创建当前有效的 API token。token 是供软件使用的秘密字符串，与网站密码不同。它只能放在项目根目录中被忽略的 .env 文件里。",
  "evidence.originStep3": "构建一次环境，然后执行只读预检",
  "evidence.originStep3Body": "隔离镜像会把云端 SDK 与竞赛环境分开。预检可以确认 token 有效，并显示当前可用的机器。",
  "evidence.originStep4": "批准后只提交一次，并保存任务编号",
  "evidence.originStep4Body": "确认所选机器和配额后才能提交。项目助手要求显式确认参数，会立即保存返回的任务编号，并拒绝覆盖已有任务记录。",
  "evidence.reproduceOriginTitle": "如果需要复现上面的归档证据示例",
  "evidence.reproduceOriginBody": "请使用 starter_kit/circuits/bell.qasm、默认 bell 配置、后端 WK_C180 和 512 次 shots，并在提交前执行 prepare。若要复现三量子比特示例，请在 prepare、submit 和 poll 中加入 --profile ghz3。",
  "evidence.spinqLessonTitle": "选择机器之前，先准备兼容云端的线路",
  "evidence.spinqLessonLede": "SpinQ 云端真机会自动测量已经使用的量子比特，因此实际提交文件必须删除显式 measure 语句，即使本地教学线路仍然包含这些语句。",
  "evidence.spinqStep1": "从本地验证过的 OpenQASM 线路开始",
  "evidence.spinqStep1Body": "先在“厂商模拟器”页面中使用 SpinQit 模拟器运行线路。模拟可以检查线路含义，但不能证明真机当前在线。",
  "evidence.spinqStep2": "刷新机器列表，并按能力选择",
  "evidence.spinqStep2Body": "连接已认证的 SpinQ 云端工具，调用 get_platforms，并选择一台在线且量子比特数量和量子门满足要求的机器。把这次最新响应保存为预检 JSON。",
  "evidence.spinqStep3": "生成实际提交文件",
  "evidence.spinqStep3Body": "项目助手会检查所选平台，并删除云端不兼容的测量声明。发送到任何地方之前，先人工检查输出。",
  "evidence.spinqStep4": "批准一次提交，然后获取同一个任务",
  "evidence.spinqStep4Body": "获得批准后，使用所选平台代码和准备好的完整 QASM 调用 qasm_submit。保存返回的任务编号，等待后使用 get_task_result_by_id；不要因为任务仍在等待就再创建一个任务。",
  "evidence.awsLessonTitle": "区分免费的本地学习与经过授权的 AWS QPU 任务",
  "evidence.awsLessonLede": "QPU 是物理量子处理器。Amazon Braket 本地模拟不需要 AWS 账号，而 QPU 任务需要 AWS 权限、区域、服务配置、存储位置和明确的费用批准。",
  "evidence.awsStep1": "无需凭证，先完成翻译和本地测试",
  "evidence.awsStep1Body": "可以在“厂商模拟器”页面选择 Amazon Braket，也可以运行下面的项目示例。它会演示 OpenQASM 3.0 程序结构，并在不连接 AWS 的情况下返回 counts。",
  "evidence.awsStep2": "创建权限受限的命名 AWS 配置",
  "evidence.awsStep2Body": "在学习和发现设备阶段，先使用只能调用 SearchDevices 和 GetDevice 的身份。这些只读权限不能创建量子任务。",
  "evidence.awsStep3": "选择 QPU 前阅读最新报告",
  "evidence.awsStep3Body": "检查设备 ARN、区域、ONLINE 状态、量子比特数量、能力、队列信息和当前公开价格。ARN 是 AWS 为云端资源分配的唯一标识。",
  "evidence.awsStep4": "在付费提交前停在项目边界",
  "evidence.awsStep4Body": "本项目有意不提供 AWS QPU 提交助手，也没有归档 AWS 真机任务。账号所有者批准启用服务、存储、区域、设备和费用后，请按照 Braket 官方控制台或 SDK 任务流程操作。只读发现凭证不代表具有提交权限。",
  "evidence.awsLimitTitle": "项目目前提供什么",
  "evidence.awsLimitBody": "OpenQASM 3.0 翻译、无需凭证的 Braket 本地示例，以及只读的实时设备发现；它不会自动执行可能收费的 AWS 任务。",
  "evidence.originGuide": "本源量子 · 带保护措施的命令行流程",
  "evidence.originGuideMeta": "本地准备 → 只读预检 → 一次显式确认提交 → 轮询",
  "evidence.credentialTitle": "只在本地配置当前 API token",
  "evidence.credentialBody": "请使用本源量子的 API token，而不是网站密码或浏览器 cookie。项目根目录的 .env 文件已被 Git 忽略。",
  "evidence.buildTitle": "构建隔离的真机镜像",
  "evidence.buildBody": "这样可以把 pyqpanda3 0.4.0 与竞赛离线评测所用的旧版 SDK 分开。",
  "evidence.prepareTitle": "准备并检查实际执行程序",
  "evidence.prepareOriginBody": "这一步完全不连接网络，会生成之后提交的 OriginIR 文件。",
  "evidence.preflightTitle": "检查账号权限和当前可用状态",
  "evidence.preflightBody": "预检是只读操作：它只查询后端列表，不会创建任务。",
  "evidence.submitTitle": "获得批准后只提交一次",
  "evidence.submitOriginBody": "这是本源流程中唯一会消耗真机配额的步骤。脚本缺少显式确认参数时会拒绝运行，也不会覆盖已经存在的任务记录。",
  "evidence.collectTitle": "按已保存的任务编号轮询并保留证据",
  "evidence.collectOriginBody": "轮询只会复用已保存的任务编号，不得创建第二个任务。收集完成后，再补充厂商任务页截图。",
  "evidence.spinqGuide": "SpinQ · 本地准备与已认证云端提交",
  "evidence.spinqGuideMeta": "刷新状态 → 准备不含测量语句的 QASM → 一次获批 MCP 提交 → 获取结果",
  "evidence.refreshTitle": "刷新实时能力",
  "evidence.refreshBody": "使用 SpinQ 的 get_platforms 工具，把选中的在线机器记录保存为预检 JSON。可用状态会变化，不要直接复用归档快照。",
  "evidence.prepareSpinqBody": "SpinQ 会自动测量已使用的量子比特，因此项目会从云端执行文件中删除显式 measure 语句。",
  "evidence.submitSpinqTitle": "通过 SpinQ 已认证工具提交一次",
  "evidence.submitSpinqBody": "获得账号所有者批准后，用 platform_code gemini_vp 和准备好的完整 QASM 调用 qasm_submit。立即保存返回的任务编号；等待期间不要重复提交。",
  "evidence.collectSpinqBody": "按任务编号获取结果，保留未经修改的响应，生成统一格式结果，并保存包含实际设备、时间、shots 和完成状态的任务页截图。",
  "evidence.awsTitle": "本项目中的 AWS 仍然只有只读能力",
  "evidence.awsBody": "如果已经配置凭证，项目可以刷新 Amazon Braket 设备可用状态；但项目中没有归档的 AWS 真机任务，也没有带保护措施的提交流程。本页面不会声称已有这些内容。",
  "history.eyebrow": "08 · 对话记录",
  "history.title1": "每一次 LoomQ 对话，",
  "history.title2": "都会保留到页面刷新。",
  "history.lede": "当前页面打开后创建的所有对话都会显示在这里。新建对话不会清除这些记录。",
  "history.emptyTitle": "还没有对话记录",
  "history.emptyBody": "向 LoomQ 提问后，对话内容会显示在这里。",
  "assistant.eyebrow": "AI 量子线路助手",
  "assistant.title": "询问 LoomQ",
  "assistant.new": "新对话",
  "assistant.generate": "生成",
  "assistant.ghz": "创建 GHZ 线路",
  "assistant.repair": "修复",
  "assistant.fix": "修复错误 QASM",
  "assistant.choose": "选择",
  "assistant.backend": "推荐后端",
  "assistant.describe": "描述你的目标",
  "assistant.placeholder": "创建一个 Bell 态，测量两个量子比特，并解释结果。",
  "assistant.ask": "询问 LoomQ"
};

const dynamicText = {
  en: {
    checking: "Checking model endpoint", ready: "Local agent ready", missing: "Model configuration missing", unavailable: "Model endpoint unreachable", authentication: "Model credentials rejected", modelMissing: "Configured model unavailable", apiError: "Model API error",
    user: "You", assistant: "LoomQ · Verified response", verified: "✓ Parsed and verified locally", copy: "Copy QASM", copied: "Copied", selectCopy: "Select code to copy", run: "Run locally",
    couldNotRun: "Could not run", shots: "shots", showing: "Showing the 16 most frequent of {count} measured states.", simulatorFailure: "The simulator could not run this circuit.",
    insightOne: "Most frequent result: {states}, representing {share}% of all shots.", insightTwo: "Most frequent results: {states}. Together they represent {share}% of all shots.",
    collapseRail: "Collapse sidebar", expandRail: "Expand sidebar",
    backendChecking: "Checking", backendReady: "Ready", backendMissing: "Not ready", backendUnavailable: "Unavailable",
    resizePrompt: "Resize prompt input from its top edge", hideAssistant: "Hide LoomQ assistant", showAssistant: "Open LoomQ assistant", openAssistant: "Ask LoomQ",
    running: "Running…", comparing: "Comparing {current} of 3…", translating: "Translating…", compiling: "Compiling…", translationFailure: "The circuit translator could not process this program.", hybridFailure: "The hybrid compiler could not process this program.", checkingAnswer: "Checking…", loading: "Interpreting, building, and checking your request", chatFailure: "The local agent could not answer.", chatHint: "Check the local model configuration, then try again. Your prompt is still in the box."
  },
  zh: {
    checking: "正在检查模型端点", ready: "本地智能体已就绪", missing: "缺少模型配置", unavailable: "模型端点无法连接", authentication: "模型凭证被拒绝", modelMissing: "配置的模型不可用", apiError: "模型 API 错误",
    user: "你", assistant: "LoomQ · 已验证回答", verified: "✓ 已在本地解析并验证", copy: "复制 QASM", copied: "已复制", selectCopy: "请选择代码后复制", run: "在本地运行",
    couldNotRun: "无法运行", shots: "次测量", showing: "正在显示 {count} 个测量状态中出现次数最多的 16 个。", simulatorFailure: "模拟器无法运行此线路，请检查量子门、参数和测量语句。",
    insightOne: "最常见的结果是 {states}，占全部测量次数的 {share}%。", insightTwo: "最常见的结果是 {states}，两者合计占全部测量次数的 {share}%。",
    collapseRail: "折叠侧边栏", expandRail: "展开侧边栏",
    backendChecking: "检查中", backendReady: "可用", backendMissing: "未就绪", backendUnavailable: "不可用",
    resizePrompt: "从顶部边缘调整提示词输入框高度", hideAssistant: "隐藏 LoomQ 助手", showAssistant: "打开 LoomQ 助手", openAssistant: "询问 LoomQ",
    running: "正在运行…", comparing: "正在对比第 {current}/3 个…", translating: "正在翻译…", compiling: "正在编译…", translationFailure: "线路翻译器无法处理这份程序。", hybridFailure: "混合编译器无法处理这份程序。", checkingAnswer: "正在检查…", loading: "正在理解、构建并检查你的请求", chatFailure: "本地智能体暂时无法回答。", chatHint: "请检查本地模型配置后重试。你的输入仍保留在输入框中。"
  }
};

let savedLanguage = "";
try { savedLanguage = localStorage.getItem("loomq-language") || ""; } catch (_error) { savedLanguage = ""; }
let language = savedLanguage || (navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");
let savedRailState = "";
try { savedRailState = localStorage.getItem("loomq-rail") || ""; } catch (_error) { savedRailState = ""; }
let railCollapsed = savedRailState ? savedRailState === "collapsed" : window.matchMedia("(max-width: 980px)").matches;
let savedAssistantState = "";
try { savedAssistantState = localStorage.getItem("loomq-assistant") || ""; } catch (_error) { savedAssistantState = ""; }
let assistantHidden = savedAssistantState === "hidden";
let sessionToken = "";
let history = [];
let busy = false;
let connected = false;
let statusState = "checking";

function tr(key, values = {}) {
  let value = dynamicText[language][key] || key;
  Object.entries(values).forEach(([name, replacement]) => { value = value.replace(`{${name}}`, replacement); });
  return value;
}

function syncRailToggle() {
  workspace.classList.toggle("rail-collapsed", railCollapsed);
  railToggle.setAttribute("aria-expanded", String(!railCollapsed));
  const label = tr(railCollapsed ? "expandRail" : "collapseRail");
  railToggle.setAttribute("aria-label", label);
  railToggle.title = label;
  railToggle.querySelector("span").textContent = railCollapsed ? "›" : "‹";
  document.querySelectorAll("[data-view]").forEach((button) => {
    const navigationLabel = button.querySelector("strong").textContent;
    if (railCollapsed) button.title = navigationLabel;
    else button.removeAttribute("title");
  });
  promptResizeHandle.setAttribute("aria-label", tr("resizePrompt"));
  promptResizeHandle.title = tr("resizePrompt");
}

function syncAssistantVisibility() {
  if (!assistantHidden && window.matchMedia("(max-width: 560px)").matches && !railCollapsed) {
    railCollapsed = true;
    syncRailToggle();
  }
  workspace.classList.toggle("assistant-hidden", assistantHidden);
  assistantDock.setAttribute("aria-hidden", String(assistantHidden));
  assistantLauncher.setAttribute("aria-expanded", String(!assistantHidden));
  assistantHideButton.setAttribute("aria-label", tr("hideAssistant"));
  assistantHideButton.title = tr("hideAssistant");
  assistantLauncher.setAttribute("aria-label", tr("showAssistant"));
  assistantLauncher.title = tr("showAssistant");
}

function setAssistantHidden(nextHidden) {
  assistantHidden = nextHidden;
  if (!assistantHidden && window.matchMedia("(max-width: 560px)").matches && !railCollapsed) {
    railCollapsed = true;
    syncRailToggle();
    try { localStorage.setItem("loomq-rail", "collapsed"); } catch (_error) { /* Preference storage is optional. */ }
  }
  syncAssistantVisibility();
  try { localStorage.setItem("loomq-assistant", assistantHidden ? "hidden" : "visible"); } catch (_error) { /* Preference storage is optional. */ }
  if (assistantHidden) assistantLauncher.focus(); else input.focus();
}

function setPromptHeight(value) {
  const height = Math.max(60, Math.min(220, Math.round(value)));
  input.style.height = `${height}px`;
  promptResizeHandle.setAttribute("aria-valuenow", String(height));
}

function applyLanguage(nextLanguage) {
  language = nextLanguage === "zh" ? "zh" : "en";
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = language === "zh" ? "LoomQ — 学习、翻译、模拟与编译量子程序" : "LoomQ — Learn, translate, simulate, and compile";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    if (!element.dataset.enText) element.dataset.enText = element.textContent;
    element.textContent = language === "zh" ? chinese[element.dataset.i18n] : element.dataset.enText;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    if (!element.dataset.enPlaceholder) element.dataset.enPlaceholder = element.placeholder;
    element.placeholder = language === "zh" ? chinese[element.dataset.i18nPlaceholder] : element.dataset.enPlaceholder;
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    if (!element.dataset.enAria) element.dataset.enAria = element.getAttribute("aria-label") || "";
    element.setAttribute("aria-label", language === "zh" ? chinese[element.dataset.i18nAria] : element.dataset.enAria);
  });
  document.querySelectorAll("[data-language]").forEach((button) => button.classList.toggle("active", button.dataset.language === language));
  document.querySelectorAll("[data-view]").forEach((button) => button.setAttribute("aria-label", button.querySelector("strong").textContent));
  document.querySelectorAll(".message").forEach((message) => {
    const meta = message.querySelector(".message-meta");
    meta.textContent = tr(message.dataset.role === "user" ? "user" : "assistant");
  });
  document.querySelectorAll("[data-history-role]").forEach((message) => {
    message.querySelector(".history-message-meta").textContent = tr(message.dataset.historyRole === "user" ? "user" : "assistant");
  });
  document.querySelectorAll("[data-dynamic-text]").forEach((element) => { element.textContent = tr(element.dataset.dynamicText); });
  statusText.textContent = tr(statusState);
  if (!busy) sendButton.querySelector("span").textContent = language === "zh" ? chinese["assistant.ask"] : sendButton.querySelector("span").dataset.enText || "Ask LoomQ";
  if (!runButton.disabled) runButton.querySelector("span").textContent = language === "zh" ? chinese["sim.run"] : "Run locally";
  if (!translationButton.disabled) translationButton.querySelector("span").textContent = language === "zh" ? chinese["l1.translate"] : "Show IR + SDK translation";
  if (!hybridButton.disabled) hybridButton.querySelector("span").textContent = language === "zh" ? chinese["hybrid.compile"] : "Compile Hybrid-QASM";
  if (simulationResults.children.length) simulationResults.replaceChildren();
  backendStatusRows.forEach((row) => setBackendStatus(row.dataset.backendStatus, row.dataset.state || "checking"));
  syncRailToggle();
  syncAssistantVisibility();
  try { localStorage.setItem("loomq-language", language); } catch (_error) { /* Preference storage is optional. */ }
}

function activateEvidenceMode(name, moveFocus = false, updateHash = true) {
  const selected = evidenceModeButtons.some((button) => button.dataset.evidenceMode === name) ? name : "hardware";
  evidenceModeButtons.forEach((button) => {
    const active = button.dataset.evidenceMode === selected;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
    if (active && moveFocus) button.focus();
  });
  evidenceModePanels.forEach((panel) => {
    const active = panel.dataset.evidencePanel === selected;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
  if (updateHash && document.querySelector('[data-view-panel="evidence"]').classList.contains("active")) {
    window.history.replaceState(null, "", `#evidence/${selected}`);
  }
  return selected;
}

function activateGpuTutorStep(name, moveFocus = false) {
  const selected = gpuTutorButtons.some((button) => button.dataset.gpuStep === String(name)) ? String(name) : "1";
  gpuTutorButtons.forEach((button) => {
    const active = button.dataset.gpuStep === selected;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
    if (active && moveFocus) button.focus();
  });
  gpuTutorPanels.forEach((panel) => {
    const active = panel.dataset.gpuPanel === selected;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
}

function activateView(name, updateHash = true) {
  const allowed = new Set(["overview", "guide", "learn", "gates", "simulator", "hybrid", "evidence", "history"]);
  const [requestedView, requestedEvidenceMode] = String(name || "").split("/", 2);
  const view = allowed.has(requestedView) ? requestedView : "overview";
  document.querySelectorAll("[data-view]").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-view-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.viewPanel === view));
  const evidenceMode = view === "evidence" ? activateEvidenceMode(requestedEvidenceMode || "hardware", false, false) : "hardware";
  contentStage.scrollTop = 0;
  if (updateHash) window.history.replaceState(null, "", view === "evidence" ? `#evidence/${evidenceMode}` : `#${view}`);
}

function activateHardwareTutorial(name, moveFocus = false) {
  const selected = hardwareTabButtons.some((button) => button.dataset.hardwareTab === name) ? name : "origin";
  hardwareTabButtons.forEach((button) => {
    const active = button.dataset.hardwareTab === selected;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
    if (active && moveFocus) button.focus();
  });
  hardwareTabPanels.forEach((panel) => {
    const active = panel.dataset.hardwarePanel === selected;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
}

function gateProgram(qubits, instructions) {
  return `OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[${qubits}];\ncreg c[${qubits}];\n${instructions.join("\n")}\nmeasure q -> c;`;
}

const gateExamples = {
  h: gateProgram(1, ["h q[0];"]), x: gateProgram(1, ["x q[0];"]), s: gateProgram(1, ["h q[0];", "s q[0];", "h q[0];"]),
  sdg: gateProgram(1, ["h q[0];", "sdg q[0];", "h q[0];"]), t: gateProgram(1, ["h q[0];", "t q[0];", "h q[0];"]), tdg: gateProgram(1, ["h q[0];", "tdg q[0];", "h q[0];"]),
  rz: gateProgram(1, ["h q[0];", "rz(pi/2) q[0];", "h q[0];"]), ry: gateProgram(1, ["ry(pi/2) q[0];"]), cx: gateProgram(2, ["h q[0];", "cx q[0],q[1];"]),
  cu1: gateProgram(2, ["h q[0];", "h q[1];", "cu1(pi) q[0],q[1];", "h q[0];", "h q[1];"]), swap: gateProgram(2, ["x q[0];", "swap q[0],q[1];"]), ccx: gateProgram(3, ["x q[0];", "x q[1];", "ccx q[0],q[1],q[2];"])
};

function setStatus(state, key) {
  statusState = key;
  statusElement.className = `status ${state}`;
  statusText.textContent = tr(key);
}

async function connect() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    if (!response.ok) throw new Error();
    const health = await response.json();
    sessionToken = health.session_token;
    connected = Boolean(health.model_available);
    const stateKeys = { missing: "missing", unreachable: "unavailable", authentication: "authentication", model_missing: "modelMissing", api_error: "apiError" };
    setStatus(health.model_available ? "ready" : "offline", health.model_available ? "ready" : (stateKeys[health.model_state] || "unavailable"));
    sendButton.disabled = !connected;
    void compileHybridProgram();
  } catch (_error) { connected = false; sendButton.disabled = true; setStatus("offline", "unavailable"); }
}

function setBackendStatus(target, state) {
  const row = backendStatusRows.find((item) => item.dataset.backendStatus === target);
  if (!row) return;
  const normalized = ["ready", "missing", "unavailable"].includes(state) ? state : "checking";
  row.dataset.state = normalized;
  row.classList.remove("checking", "ready", "missing", "unavailable");
  row.classList.add(normalized);
  const stateText = tr(normalized === "ready" ? "backendReady" : normalized === "missing" ? "backendMissing" : normalized === "unavailable" ? "backendUnavailable" : "backendChecking");
  row.querySelector("[data-backend-state]").textContent = stateText;
  const name = row.querySelector(":scope > span:nth-of-type(2)").textContent;
  row.title = `${name} · ${stateText}`;
  row.setAttribute("aria-label", `${name} · ${stateText}`);
}

async function checkBackendHealth() {
  backendStatusRows.forEach((row) => setBackendStatus(row.dataset.backendStatus, "checking"));
  try {
    const response = await fetch("/api/backend-health", { cache: "no-store" });
    if (!response.ok) throw new Error();
    const payload = await response.json();
    backendStatusRows.forEach((row) => {
      const result = payload.backends && payload.backends[row.dataset.backendStatus];
      setBackendStatus(row.dataset.backendStatus, result && result.ok ? "ready" : result && result.state === "missing" ? "missing" : "unavailable");
    });
  } catch (_error) {
    backendStatusRows.forEach((row) => setBackendStatus(row.dataset.backendStatus, "unavailable"));
  }
}

function addMessage(role, content, options = {}) {
  const message = template.content.firstElementChild.cloneNode(true);
  message.dataset.role = role;
  message.classList.add(role);
  if (options.error) message.classList.add("error");
  if (options.loading) message.classList.add("loading");
  message.querySelector(".message-meta").textContent = tr(role === "user" ? "user" : "assistant");
  const body = message.querySelector(".message-body");
  if (options.kind === "qasm" && !options.loading) {
    body.remove();
    const code = document.createElement("pre"); code.textContent = content; message.append(code);
    const toolbar = document.createElement("div"); toolbar.className = "answer-toolbar";
    const badge = document.createElement("span"); badge.className = "answer-badge"; badge.dataset.dynamicText = "verified"; badge.textContent = tr("verified");
    const copy = document.createElement("button"); copy.type = "button"; copy.className = "copy-button"; copy.dataset.dynamicText = "copy"; copy.textContent = tr("copy");
    copy.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(content); copy.dataset.dynamicText = "copied"; copy.textContent = tr("copied"); window.setTimeout(() => { copy.dataset.dynamicText = "copy"; copy.textContent = tr("copy"); }, 1400); }
      catch (_error) { copy.dataset.dynamicText = "selectCopy"; copy.textContent = tr("selectCopy"); }
    });
    const simulate = document.createElement("button"); simulate.type = "button"; simulate.className = "simulate-button"; simulate.dataset.dynamicText = "run"; simulate.textContent = tr("run");
    simulate.addEventListener("click", () => { qasmInput.value = content; activateView("simulator"); window.setTimeout(() => qasmInput.focus(), 200); });
    const actions = document.createElement("div"); actions.className = "answer-actions"; actions.append(copy, simulate); toolbar.append(badge, actions); message.append(toolbar);
  } else { body.textContent = content; }
  conversation.append(message);
  if (!options.loading) archiveMessage(role, content, options);
  window.requestAnimationFrame(() => { conversation.scrollTop = conversation.scrollHeight; });
  return message;
}

function archiveMessage(role, content, options = {}) {
  const message = document.createElement("article");
  message.className = `history-message ${role}${options.error ? " error" : ""}`;
  message.dataset.historyRole = role;
  const meta = document.createElement("div");
  meta.className = "history-message-meta";
  meta.textContent = tr(role === "user" ? "user" : "assistant");
  const body = document.createElement(options.kind === "qasm" ? "pre" : "div");
  body.className = "history-message-body";
  body.textContent = content;
  message.append(meta, body);
  historyList.append(message);
  historyEmpty.hidden = true;
}

function setRunnerBusy(nextBusy, label = tr("run")) {
  runButton.disabled = nextBusy; qasmInput.disabled = nextBusy; simulatorTarget.disabled = nextBusy; simulatorShots.disabled = nextBusy;
  runButton.querySelector("span").textContent = label;
}

function createResultCard(targetName, payload, error = "") {
  const card = document.createElement("article"); card.className = `simulation-card${error ? " failed" : ""}`;
  const heading = document.createElement("div"); heading.className = "simulation-heading";
  const title = document.createElement("strong"); title.textContent = targetName;
  const state = document.createElement("span"); state.textContent = error ? tr("couldNotRun") : `${payload.result.shots} ${tr("shots")} · ${(payload.elapsed_ms / 1000).toFixed(2)}s`;
  heading.append(title, state); card.append(heading);
  if (error) { const message = document.createElement("p"); message.className = "simulation-error"; message.textContent = language === "zh" ? tr("simulatorFailure") : error; card.append(message); return card; }
  const counts = Object.entries(payload.result.counts); const total = counts.reduce((sum, entry) => sum + entry[1], 0); const visible = counts.sort((left, right) => right[1] - left[1]).slice(0, 16);
  if (payload.insight && payload.insight.top_states.length) {
    const explanation = document.createElement("p"); explanation.className = "result-insight";
    const separator = language === "zh" ? "、" : " and ";
    const states = payload.insight.top_states.map((name) => `|${name}⟩`).join(separator);
    const key = payload.insight.top_states.length === 1 ? "insightOne" : "insightTwo";
    explanation.textContent = tr(key, { states, share: (payload.insight.top_share * 100).toFixed(1) });
    card.append(explanation);
  }
  const chart = document.createElement("div"); chart.className = "counts-chart";
  visible.forEach(([stateName, count]) => { const row = document.createElement("div"); row.className = "count-row"; const key = document.createElement("code"); key.textContent = `|${stateName}⟩`; const track = document.createElement("span"); track.className = "count-track"; const bar = document.createElement("i"); const percent = total ? (count / total) * 100 : 0; bar.style.width = `${Math.max(percent, .7)}%`; track.append(bar); const value = document.createElement("span"); value.textContent = `${count} · ${percent.toFixed(1)}%`; row.append(key, track, value); chart.append(row); });
  card.append(chart);
  if (counts.length > visible.length) { const note = document.createElement("small"); note.textContent = tr("showing", { count: counts.length }); card.append(note); }
  return card;
}

async function runOnTarget(qasm, target, shots) {
  const response = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json", "X-LoomQ-Session": sessionToken }, body: JSON.stringify({ qasm, target, shots }) });
  const payload = await response.json(); if (!response.ok) throw new Error(payload.error || tr("simulatorFailure")); return payload;
}

runnerForm.addEventListener("submit", async (event) => {
  event.preventDefault(); const qasm = qasmInput.value.trim(); const shots = Number(simulatorShots.value); if (!qasm) return;
  const targets = simulatorTarget.value === "all" ? ["spinq", "originq", "braket"] : [simulatorTarget.value];
  const names = { spinq: "SpinQit Basic Simulator", originq: "Origin Quantum CPU Simulator", braket: "Amazon Braket Local Simulator" };
  simulationResults.replaceChildren(); setRunnerBusy(true, targets.length > 1 ? tr("comparing", { current: 1 }) : tr("running"));
  for (let index = 0; index < targets.length; index += 1) {
    const target = targets[index]; if (targets.length > 1) setRunnerBusy(true, tr("comparing", { current: index + 1 }));
    try { const payload = await runOnTarget(qasm, target, shots); simulationResults.append(createResultCard(payload.target_name, payload)); }
    catch (error) { simulationResults.append(createResultCard(names[target], null, error.message)); }
  }
  setRunnerBusy(false, language === "zh" ? chinese["sim.run"] : "Run locally");
});

function setCompilerOutput(element, content, isError = false) {
  element.classList.toggle("error", isError);
  element.textContent = content;
}

function setTranslationBusy(nextBusy) {
  translationButton.disabled = nextBusy;
  translationTarget.disabled = nextBusy;
  translationButton.querySelector("span").textContent = nextBusy ? tr("translating") : (language === "zh" ? chinese["l1.translate"] : "Show IR + SDK translation");
}

async function translateProgram() {
  const qasm = qasmInput.value.trim();
  if (!qasm || translationButton.disabled) return;
  setTranslationBusy(true);
  setCompilerOutput(irOutput, tr("translating"));
  setCompilerOutput(translationOutput, tr("translating"));
  try {
    const response = await fetch("/api/transpile", { method: "POST", headers: { "Content-Type": "application/json", "X-LoomQ-Session": sessionToken }, body: JSON.stringify({ qasm, target: translationTarget.value }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || tr("translationFailure"));
    setCompilerOutput(irOutput, JSON.stringify(payload.ir, null, 2));
    setCompilerOutput(translationOutput, payload.translated);
  } catch (error) {
    const message = `${tr("translationFailure")}\n\n${error.message}`;
    setCompilerOutput(irOutput, message, true);
    setCompilerOutput(translationOutput, message, true);
  } finally { setTranslationBusy(false); }
}

function setHybridBusy(nextBusy) {
  hybridButton.disabled = nextBusy;
  hybridInput.disabled = nextBusy;
  hybridButton.querySelector("span").textContent = nextBusy ? tr("compiling") : (language === "zh" ? chinese["hybrid.compile"] : "Compile Hybrid-QASM");
}

async function compileHybridProgram() {
  const source = hybridInput.value.trim();
  if (!source || hybridButton.disabled) return;
  setHybridBusy(true);
  setCompilerOutput(hybridQuantumOutput, tr("compiling"));
  setCompilerOutput(hybridAssemblyOutput, tr("compiling"));
  setCompilerOutput(hybridMachineOutput, tr("compiling"));
  setCompilerOutput(hybridDecodedOutput, tr("compiling"));
  try {
    const response = await fetch("/api/compile-hybrid", { method: "POST", headers: { "Content-Type": "application/json", "X-LoomQ-Session": sessionToken }, body: JSON.stringify({ source }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || tr("hybridFailure"));
    setCompilerOutput(hybridQuantumOutput, payload.quantum_operations.join("\n"));
    setCompilerOutput(hybridAssemblyOutput, payload.assembly);
    setCompilerOutput(hybridMachineOutput, payload.machine_code);
    setCompilerOutput(hybridDecodedOutput, payload.decoded_trace.join("\n"));
  } catch (error) {
    const message = `${tr("hybridFailure")}\n\n${error.message}`;
    setCompilerOutput(hybridQuantumOutput, message, true);
    setCompilerOutput(hybridAssemblyOutput, message, true);
    setCompilerOutput(hybridMachineOutput, message, true);
    setCompilerOutput(hybridDecodedOutput, message, true);
  } finally { setHybridBusy(false); }
}

function setBusy(nextBusy) {
  busy = nextBusy; sendButton.disabled = nextBusy || !connected; input.disabled = nextBusy;
  sendButton.querySelector("span").textContent = nextBusy ? tr("checkingAnswer") : (language === "zh" ? chinese["assistant.ask"] : "Ask LoomQ");
}

async function submitPrompt(prompt) {
  if (busy || !connected || !prompt.trim()) return;
  const cleanPrompt = prompt.trim(); starterPrompts.hidden = true; addMessage("user", cleanPrompt); const loading = addMessage("assistant", tr("loading"), { loading: true }); setBusy(true);
  try {
    const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json", "X-LoomQ-Session": sessionToken }, body: JSON.stringify({ prompt: cleanPrompt, history }) });
    const payload = await response.json(); loading.remove(); if (!response.ok) throw new Error(payload.error || tr("chatFailure"));
    addMessage("assistant", payload.answer, { kind: payload.kind }); history.push({ role: "user", content: cleanPrompt }, { role: "assistant", content: payload.answer }); history = history.slice(-6); input.value = "";
  } catch (error) {
    loading.remove(); const detail = language === "zh" ? tr("chatFailure") : error.message; addMessage("assistant", `${detail}\n\n${tr("chatHint")}`, { error: true }); input.value = cleanPrompt;
  } finally { setBusy(false); input.focus(); }
}

composer.addEventListener("submit", (event) => { event.preventDefault(); submitPrompt(input.value); });
translationButton.addEventListener("click", translateProgram);
hybridForm.addEventListener("submit", (event) => { event.preventDefault(); compileHybridProgram(); });
input.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); composer.requestSubmit(); } });
document.querySelectorAll("[data-prompt-en]").forEach((button) => button.addEventListener("click", () => { input.value = language === "zh" ? button.dataset.promptZh : button.dataset.promptEn; input.focus(); }));
document.querySelectorAll("[data-gate-example]").forEach((button) => button.addEventListener("click", () => { qasmInput.value = gateExamples[button.dataset.gateExample]; simulationResults.replaceChildren(); activateView("simulator"); window.setTimeout(() => qasmInput.focus(), 200); }));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => activateView(button.dataset.view)));
hardwareTabButtons.forEach((button, index) => {
  button.addEventListener("click", () => activateHardwareTutorial(button.dataset.hardwareTab));
  button.addEventListener("keydown", (event) => {
    let nextIndex = index;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % hardwareTabButtons.length;
    else if (event.key === "ArrowLeft") nextIndex = (index - 1 + hardwareTabButtons.length) % hardwareTabButtons.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = hardwareTabButtons.length - 1;
    else return;
    event.preventDefault();
    activateHardwareTutorial(hardwareTabButtons[nextIndex].dataset.hardwareTab, true);
  });
});
evidenceModeButtons.forEach((button, index) => {
  button.addEventListener("click", () => activateEvidenceMode(button.dataset.evidenceMode));
  button.addEventListener("keydown", (event) => {
    let nextIndex = index;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % evidenceModeButtons.length;
    else if (event.key === "ArrowLeft") nextIndex = (index - 1 + evidenceModeButtons.length) % evidenceModeButtons.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = evidenceModeButtons.length - 1;
    else return;
    event.preventDefault();
    activateEvidenceMode(evidenceModeButtons[nextIndex].dataset.evidenceMode, true);
  });
});
gpuTutorButtons.forEach((button, index) => {
  button.addEventListener("click", () => activateGpuTutorStep(button.dataset.gpuStep));
  button.addEventListener("keydown", (event) => {
    let nextIndex = index;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") nextIndex = (index + 1) % gpuTutorButtons.length;
    else if (event.key === "ArrowUp" || event.key === "ArrowLeft") nextIndex = (index - 1 + gpuTutorButtons.length) % gpuTutorButtons.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = gpuTutorButtons.length - 1;
    else return;
    event.preventDefault();
    activateGpuTutorStep(gpuTutorButtons[nextIndex].dataset.gpuStep, true);
  });
});
document.querySelectorAll("[data-language]").forEach((button) => button.addEventListener("click", () => applyLanguage(button.dataset.language)));
clearButton.addEventListener("click", () => { history = []; conversation.replaceChildren(); starterPrompts.hidden = false; input.value = ""; input.focus(); });
railToggle.addEventListener("click", () => {
  railCollapsed = !railCollapsed;
  syncRailToggle();
  try { localStorage.setItem("loomq-rail", railCollapsed ? "collapsed" : "expanded"); } catch (_error) { /* Preference storage is optional. */ }
});
assistantHideButton.addEventListener("click", () => setAssistantHidden(true));
assistantLauncher.addEventListener("click", () => setAssistantHidden(false));
let promptResizeStart = null;
promptResizeHandle.addEventListener("pointerdown", (event) => {
  promptResizeStart = { y: event.clientY, height: input.getBoundingClientRect().height };
  promptResizeHandle.setPointerCapture(event.pointerId);
  promptResizeHandle.classList.add("active");
  event.preventDefault();
});
promptResizeHandle.addEventListener("pointermove", (event) => {
  if (!promptResizeStart) return;
  setPromptHeight(promptResizeStart.height + promptResizeStart.y - event.clientY);
});
function finishPromptResize(event) {
  if (!promptResizeStart) return;
  promptResizeStart = null;
  promptResizeHandle.classList.remove("active");
  if (promptResizeHandle.hasPointerCapture(event.pointerId)) promptResizeHandle.releasePointerCapture(event.pointerId);
}
promptResizeHandle.addEventListener("pointerup", finishPromptResize);
promptResizeHandle.addEventListener("pointercancel", finishPromptResize);
promptResizeHandle.addEventListener("keydown", (event) => {
  const current = input.getBoundingClientRect().height;
  if (event.key === "ArrowUp") setPromptHeight(current + 16);
  else if (event.key === "ArrowDown") setPromptHeight(current - 16);
  else if (event.key === "Home") setPromptHeight(60);
  else if (event.key === "End") setPromptHeight(220);
  else return;
  event.preventDefault();
});

applyLanguage(language);
activateView(location.hash.slice(1));
activateGpuTutorStep("1");
window.addEventListener("hashchange", () => activateView(location.hash.slice(1), false));
connect();
checkBackendHealth();
