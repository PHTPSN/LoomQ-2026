const conversation = document.querySelector("#conversation");
const composer = document.querySelector("#composer");
const input = document.querySelector("#prompt-input");
const sendButton = document.querySelector("#send-button");
const starterPrompts = document.querySelector("#starter-prompts");
const statusElement = document.querySelector("#service-status");
const statusText = document.querySelector("#service-status-text");
const clearButton = document.querySelector("#clear-button");
const template = document.querySelector("#message-template");
const contentStage = document.querySelector("#content-stage");
const runnerLab = document.querySelector("#runner-lab");
const runnerForm = document.querySelector("#runner-form");
const qasmInput = document.querySelector("#qasm-input");
const simulatorTarget = document.querySelector("#simulator-target");
const simulatorShots = document.querySelector("#simulator-shots");
const runButton = document.querySelector("#run-button");
const simulationResults = document.querySelector("#simulation-results");

const chinese = {
  "aria.workspace": "工作区导航",
  "aria.language": "语言",
  "aria.tools": "学习工具",
  "aria.conversation": "对话",
  "brand.tagline": "量子新手指南",
  "nav.overview": "工具介绍",
  "nav.learn": "量子基础教学",
  "nav.gates": "支持的 12 种门",
  "nav.simulator": "厂商模拟器",
  "rail.local": "仅在本机运行 · 模型凭证始终保留在 Python 中",
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
  "learn.eyebrow": "02 · 量子基础教学",
  "learn.title1": "理解六个概念，",
  "learn.title2": "就能读懂第一条量子线路。",
  "learn.lede": "用程序员的方式理解：量子线路是一组按顺序执行的指令，它先变换状态，再对结果进行采样。",
  "learn.qubitTitle": "量子比特",
  "learn.qubitBody": "量子版本的比特。在测量前，它的状态可以同时包含带权重的 |0⟩ 和 |1⟩ 分量。",
  "learn.superTitle": "叠加",
  "learn.superBody": "多个基态的组合。振幅绝对值的平方就是测量得到相应状态的概率。",
  "learn.gateTitle": "量子门与线路",
  "learn.gateBody": "量子门是一次可逆状态变换；量子线路则是这些指令按顺序组成的列表。",
  "learn.measureTitle": "测量",
  "learn.measureBody": "把量子信息转换成经典比特，得到 00 或 11 这样的二进制结果。",
  "learn.shotsTitle": "Shots",
  "learn.shotsBody": "线路被重新制备并测量的次数。shots 越多，观测到的直方图通常越稳定。",
  "learn.entangleTitle": "纠缠",
  "learn.entangleBody": "多个量子比特共享且结果相关的状态。Bell 对的每一位都随机，但两位结果总是相同。",
  "learn.storyEyebrow": "只需要两个门",
  "learn.storyTitle": "Bell 对是怎样产生的",
  "learn.storyBody": "从两个 0 开始。H 门产生两条可能路径，CX 门把它们关联起来，测量后主要得到 00 或 11。",
  "learn.start": "开始",
  "learn.known": "确定的输入",
  "learn.gate": "量子门",
  "learn.paths": "两条路径",
  "learn.link": "关联",
  "learn.entangle": "产生纠缠",
  "learn.measure": "测量",
  "learn.correlated": "相关的 counts",
  "learn.bitOrderTitle": "一个重要约定",
  "learn.bitOrderBody": "在结果键“10”中，最右侧字符对应 c[0]。LoomQ 会把所有后端统一成这种小端位序。",
  "gates.eyebrow": "03 · 官方门集",
  "gates.title1": "十二种门，",
  "gates.title2": "就是完整词汇表。",
  "gates.lede": "竞赛隐藏用例同样只使用这份白名单。θ 表示以弧度为单位的旋转角度；“dg”表示该门的逆操作。",
  "gates.single": "单量子比特门",
  "gates.phase": "相位与旋转门",
  "gates.multi": "受控与多量子比特门",
  "gates.oneQubit": "1 量子比特",
  "gates.twoQubits": "2 量子比特",
  "gates.threeQubits": "3 量子比特",
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
  "sim.eyebrow": "04 · 厂商模拟器",
  "sim.title": "在本地运行 OpenQASM。",
  "sim.lede": "选择一个 SDK，或依次对比三个 SDK。Shots 表示模拟器重新制备并测量线路的次数。",
  "sim.lab": "本地模拟实验室",
  "sim.program": "OpenQASM 2.0 程序",
  "sim.simulator": "模拟器",
  "sim.all": "对比全部三个模拟器",
  "sim.shots": "Shots",
  "sim.run": "在本地运行",
  "sim.privacy": "无需账号、付款或排队，也不会提交任何真实硬件任务。",
  "assistant.eyebrow": "AI 量子线路助手",
  "assistant.title": "询问 LoomQ",
  "assistant.new": "新对话",
  "assistant.intro": "浏览工具和课程时，AI 对话会始终显示在这里。",
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
    checking: "Checking local agent", ready: "Local agent ready", missing: "Model configuration missing", unavailable: "Local agent unavailable",
    user: "You", assistant: "LoomQ · Verified response", verified: "✓ Parsed and verified locally", copy: "Copy QASM", copied: "Copied", selectCopy: "Select code to copy", run: "Run locally",
    couldNotRun: "Could not run", shots: "shots", showing: "Showing the 16 most frequent of {count} measured states.", simulatorFailure: "The simulator could not run this circuit.",
    insightOne: "Most frequent result: {states}, representing {share}% of all shots.", insightTwo: "Most frequent results: {states}. Together they represent {share}% of all shots.",
    running: "Running…", comparing: "Comparing {current} of 3…", checkingAnswer: "Checking…", loading: "Interpreting, building, and checking your request", chatFailure: "The local agent could not answer.", chatHint: "Check the local model configuration, then try again. Your prompt is still in the box."
  },
  zh: {
    checking: "正在检查本地智能体", ready: "本地智能体已就绪", missing: "缺少模型配置", unavailable: "本地智能体不可用",
    user: "你", assistant: "LoomQ · 已验证回答", verified: "✓ 已在本地解析并验证", copy: "复制 QASM", copied: "已复制", selectCopy: "请选择代码后复制", run: "在本地运行",
    couldNotRun: "无法运行", shots: "次测量", showing: "正在显示 {count} 个测量状态中出现次数最多的 16 个。", simulatorFailure: "模拟器无法运行此线路，请检查量子门、参数和测量语句。",
    insightOne: "最常见的结果是 {states}，占全部测量次数的 {share}%。", insightTwo: "最常见的结果是 {states}，两者合计占全部测量次数的 {share}%。",
    running: "正在运行…", comparing: "正在对比第 {current}/3 个…", checkingAnswer: "正在检查…", loading: "正在理解、构建并检查你的请求", chatFailure: "本地智能体暂时无法回答。", chatHint: "请检查本地模型配置后重试。你的输入仍保留在输入框中。"
  }
};

let savedLanguage = "";
try { savedLanguage = localStorage.getItem("loomq-language") || ""; } catch (_error) { savedLanguage = ""; }
let language = savedLanguage || (navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");
let sessionToken = "";
let history = [];
let busy = false;
let statusState = "checking";

function tr(key, values = {}) {
  let value = dynamicText[language][key] || key;
  Object.entries(values).forEach(([name, replacement]) => { value = value.replace(`{${name}}`, replacement); });
  return value;
}

function applyLanguage(nextLanguage) {
  language = nextLanguage === "zh" ? "zh" : "en";
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = language === "zh" ? "LoomQ — 学习、构建和模拟量子线路" : "LoomQ — Learn, build, and simulate quantum circuits";
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
  document.querySelectorAll("[data-dynamic-text]").forEach((element) => { element.textContent = tr(element.dataset.dynamicText); });
  statusText.textContent = tr(statusState);
  if (!busy) sendButton.querySelector("span").textContent = language === "zh" ? chinese["assistant.ask"] : sendButton.querySelector("span").dataset.enText || "Ask LoomQ";
  if (!runButton.disabled) runButton.querySelector("span").textContent = language === "zh" ? chinese["sim.run"] : "Run locally";
  if (simulationResults.children.length) simulationResults.replaceChildren();
  try { localStorage.setItem("loomq-language", language); } catch (_error) { /* Preference storage is optional. */ }
}

function activateView(name) {
  const allowed = new Set(["overview", "learn", "gates", "simulator"]);
  const view = allowed.has(name) ? name : "overview";
  document.querySelectorAll("[data-view]").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-view-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.viewPanel === view));
  contentStage.scrollTop = 0;
  window.history.replaceState(null, "", `#${view}`);
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
    setStatus(health.model_configured ? "ready" : "offline", health.model_configured ? "ready" : "missing");
  } catch (_error) { setStatus("offline", "unavailable"); }
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
    simulate.addEventListener("click", () => { qasmInput.value = content; runnerLab.open = true; activateView("simulator"); window.setTimeout(() => qasmInput.focus(), 200); });
    const actions = document.createElement("div"); actions.className = "answer-actions"; actions.append(copy, simulate); toolbar.append(badge, actions); message.append(toolbar);
  } else { body.textContent = content; }
  conversation.append(message);
  message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return message;
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

function setBusy(nextBusy) {
  busy = nextBusy; sendButton.disabled = nextBusy; input.disabled = nextBusy;
  sendButton.querySelector("span").textContent = nextBusy ? tr("checkingAnswer") : (language === "zh" ? chinese["assistant.ask"] : "Ask LoomQ");
}

async function submitPrompt(prompt) {
  if (busy || !prompt.trim()) return;
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
input.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); composer.requestSubmit(); } });
document.querySelectorAll("[data-prompt-en]").forEach((button) => button.addEventListener("click", () => { input.value = language === "zh" ? button.dataset.promptZh : button.dataset.promptEn; input.focus(); }));
document.querySelectorAll("[data-gate-example]").forEach((button) => button.addEventListener("click", () => { qasmInput.value = gateExamples[button.dataset.gateExample]; simulationResults.replaceChildren(); runnerLab.open = true; activateView("simulator"); window.setTimeout(() => qasmInput.focus(), 200); }));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => activateView(button.dataset.view)));
document.querySelectorAll("[data-language]").forEach((button) => button.addEventListener("click", () => applyLanguage(button.dataset.language)));
clearButton.addEventListener("click", () => { history = []; conversation.replaceChildren(); starterPrompts.hidden = false; input.value = ""; input.focus(); });

applyLanguage(language);
activateView(location.hash.slice(1));
connect();
