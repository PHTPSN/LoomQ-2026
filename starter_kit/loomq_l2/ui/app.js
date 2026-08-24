const conversation = document.querySelector("#conversation");
const composer = document.querySelector("#composer");
const input = document.querySelector("#prompt-input");
const sendButton = document.querySelector("#send-button");
const starterPrompts = document.querySelector("#starter-prompts");
const statusElement = document.querySelector("#service-status");
const statusText = document.querySelector("#service-status-text");
const clearButton = document.querySelector("#clear-button");
const template = document.querySelector("#message-template");
const runnerLab = document.querySelector("#runner-lab");
const runnerForm = document.querySelector("#runner-form");
const qasmInput = document.querySelector("#qasm-input");
const simulatorTarget = document.querySelector("#simulator-target");
const simulatorShots = document.querySelector("#simulator-shots");
const runButton = document.querySelector("#run-button");
const simulationResults = document.querySelector("#simulation-results");

let sessionToken = "";
let history = [];
let busy = false;

function gateProgram(qubits, instructions) {
  return `OPENQASM 2.0;
include "qelib1.inc";
qreg q[${qubits}];
creg c[${qubits}];
${instructions.join("\n")}
measure q -> c;`;
}

const gateExamples = {
  h: gateProgram(1, ["h q[0];"]),
  x: gateProgram(1, ["x q[0];"]),
  s: gateProgram(1, ["h q[0];", "s q[0];", "h q[0];"]),
  sdg: gateProgram(1, ["h q[0];", "sdg q[0];", "h q[0];"]),
  t: gateProgram(1, ["h q[0];", "t q[0];", "h q[0];"]),
  tdg: gateProgram(1, ["h q[0];", "tdg q[0];", "h q[0];"]),
  rz: gateProgram(1, ["h q[0];", "rz(pi/2) q[0];", "h q[0];"]),
  ry: gateProgram(1, ["ry(pi/2) q[0];"]),
  cx: gateProgram(2, ["h q[0];", "cx q[0],q[1];"]),
  cu1: gateProgram(2, ["h q[0];", "h q[1];", "cu1(pi) q[0],q[1];", "h q[0];", "h q[1];"]),
  swap: gateProgram(2, ["x q[0];", "swap q[0],q[1];"]),
  ccx: gateProgram(3, ["x q[0];", "x q[1];", "ccx q[0],q[1],q[2];"]),
};

function setStatus(state, text) {
  statusElement.className = `status ${state}`;
  statusText.textContent = text;
}

async function connect() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    if (!response.ok) throw new Error("Local agent unavailable");
    const health = await response.json();
    sessionToken = health.session_token;
    if (health.model_configured) {
      setStatus("ready", "Local agent ready");
    } else {
      setStatus("offline", "Model configuration missing");
    }
  } catch (_error) {
    setStatus("offline", "Local agent unavailable");
  }
}

function addMessage(role, content, options = {}) {
  const message = template.content.firstElementChild.cloneNode(true);
  message.classList.add(role);
  if (options.error) message.classList.add("error");
  if (options.loading) message.classList.add("loading");
  message.querySelector(".message-meta").textContent = role === "user" ? "You · 你" : "LoomQ · Verified response";
  const body = message.querySelector(".message-body");

  if (options.kind === "qasm" && !options.loading) {
    body.remove();
    const code = document.createElement("pre");
    code.textContent = content;
    message.append(code);
    const toolbar = document.createElement("div");
    toolbar.className = "answer-toolbar";
    const badge = document.createElement("span");
    badge.className = "answer-badge";
    badge.textContent = "✓ Parsed and verified locally";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy-button";
    copy.textContent = "Copy QASM";
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(content);
        copy.textContent = "Copied";
        window.setTimeout(() => { copy.textContent = "Copy QASM"; }, 1400);
      } catch (_error) {
        copy.textContent = "Select code to copy";
      }
    });
    const simulate = document.createElement("button");
    simulate.type = "button";
    simulate.className = "simulate-button";
    simulate.textContent = "Run locally";
    simulate.addEventListener("click", () => {
      qasmInput.value = content;
      runnerLab.open = true;
      runnerLab.scrollIntoView({ behavior: "smooth", block: "start" });
      window.setTimeout(() => qasmInput.focus(), 350);
    });
    const actions = document.createElement("div");
    actions.className = "answer-actions";
    actions.append(copy, simulate);
    toolbar.append(badge, actions);
    message.append(toolbar);
  } else {
    body.textContent = content;
  }

  conversation.append(message);
  message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return message;
}

function setRunnerBusy(nextBusy, label = "Run locally") {
  runButton.disabled = nextBusy;
  qasmInput.disabled = nextBusy;
  simulatorTarget.disabled = nextBusy;
  simulatorShots.disabled = nextBusy;
  runButton.querySelector("span").textContent = label;
}

function createResultCard(targetName, payload, error = "") {
  const card = document.createElement("article");
  card.className = `simulation-card${error ? " failed" : ""}`;
  const heading = document.createElement("div");
  heading.className = "simulation-heading";
  const title = document.createElement("strong");
  title.textContent = targetName;
  const state = document.createElement("span");
  state.textContent = error ? "Could not run" : `${payload.result.shots} shots · ${(payload.elapsed_ms / 1000).toFixed(2)}s`;
  heading.append(title, state);
  card.append(heading);

  if (error) {
    const message = document.createElement("p");
    message.className = "simulation-error";
    message.textContent = error;
    card.append(message);
    return card;
  }

  const counts = Object.entries(payload.result.counts);
  const total = counts.reduce((sum, entry) => sum + entry[1], 0);
  const visible = counts.sort((left, right) => right[1] - left[1]).slice(0, 16);
  const chart = document.createElement("div");
  chart.className = "counts-chart";
  visible.forEach(([stateName, count]) => {
    const row = document.createElement("div");
    row.className = "count-row";
    const key = document.createElement("code");
    key.textContent = `|${stateName}⟩`;
    const track = document.createElement("span");
    track.className = "count-track";
    const bar = document.createElement("i");
    const percent = total ? (count / total) * 100 : 0;
    bar.style.width = `${Math.max(percent, 0.7)}%`;
    track.append(bar);
    const value = document.createElement("span");
    value.textContent = `${count} · ${percent.toFixed(1)}%`;
    row.append(key, track, value);
    chart.append(row);
  });
  card.append(chart);
  if (counts.length > visible.length) {
    const note = document.createElement("small");
    note.textContent = `Showing the 16 most frequent of ${counts.length} measured states.`;
    card.append(note);
  }
  return card;
}

async function runOnTarget(qasm, target, shots) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-LoomQ-Session": sessionToken,
    },
    body: JSON.stringify({ qasm, target, shots }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "The simulator could not run this circuit.");
  return payload;
}

runnerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const qasm = qasmInput.value.trim();
  const shots = Number(simulatorShots.value);
  if (!qasm) return;
  const targets = simulatorTarget.value === "all"
    ? ["spinq", "originq", "braket"]
    : [simulatorTarget.value];
  const names = {
    spinq: "SpinQit Basic Simulator",
    originq: "Origin Quantum CPU Simulator",
    braket: "Amazon Braket Local Simulator",
  };
  simulationResults.replaceChildren();
  setRunnerBusy(true, targets.length > 1 ? "Comparing 1 of 3…" : "Running…");
  for (let index = 0; index < targets.length; index += 1) {
    const target = targets[index];
    if (targets.length > 1) setRunnerBusy(true, `Comparing ${index + 1} of 3…`);
    try {
      const payload = await runOnTarget(qasm, target, shots);
      simulationResults.append(createResultCard(payload.target_name, payload));
    } catch (error) {
      simulationResults.append(createResultCard(names[target], null, error.message));
    }
  }
  setRunnerBusy(false);
});

function setBusy(nextBusy) {
  busy = nextBusy;
  sendButton.disabled = nextBusy;
  input.disabled = nextBusy;
  sendButton.querySelector("span").textContent = nextBusy ? "Checking…" : "Ask LoomQ";
}

async function submitPrompt(prompt) {
  if (busy || !prompt.trim()) return;
  const cleanPrompt = prompt.trim();
  starterPrompts.hidden = true;
  addMessage("user", cleanPrompt);
  const loading = addMessage("assistant", "Interpreting, building, and checking your request", { loading: true });
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-LoomQ-Session": sessionToken,
      },
      body: JSON.stringify({ prompt: cleanPrompt, history }),
    });
    const payload = await response.json();
    loading.remove();
    if (!response.ok) throw new Error(payload.error || "The local agent could not answer.");
    addMessage("assistant", payload.answer, { kind: payload.kind });
    history.push({ role: "user", content: cleanPrompt }, { role: "assistant", content: payload.answer });
    history = history.slice(-6);
    input.value = "";
  } catch (error) {
    loading.remove();
    addMessage("assistant", `${error.message}\n\nCheck the local model configuration, then try again. Your prompt is still in the box.`, { error: true });
    input.value = cleanPrompt;
  } finally {
    setBusy(false);
    input.focus();
  }
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();
  submitPrompt(input.value);
});

input.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    composer.requestSubmit();
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
  });
});

document.querySelectorAll("[data-gate-example]").forEach((button) => {
  button.addEventListener("click", () => {
    qasmInput.value = gateExamples[button.dataset.gateExample];
    simulationResults.replaceChildren();
    runnerLab.open = true;
    runnerLab.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => qasmInput.focus(), 350);
  });
});

clearButton.addEventListener("click", () => {
  history = [];
  conversation.replaceChildren();
  starterPrompts.hidden = false;
  input.value = "";
  input.focus();
});

connect();
