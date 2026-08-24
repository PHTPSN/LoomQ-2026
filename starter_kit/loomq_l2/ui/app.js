const conversation = document.querySelector("#conversation");
const composer = document.querySelector("#composer");
const input = document.querySelector("#prompt-input");
const sendButton = document.querySelector("#send-button");
const starterPrompts = document.querySelector("#starter-prompts");
const statusElement = document.querySelector("#service-status");
const statusText = document.querySelector("#service-status-text");
const clearButton = document.querySelector("#clear-button");
const template = document.querySelector("#message-template");

let sessionToken = "";
let history = [];
let busy = false;

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
    toolbar.append(badge, copy);
    message.append(toolbar);
  } else {
    body.textContent = content;
  }

  conversation.append(message);
  message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return message;
}

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

clearButton.addEventListener("click", () => {
  history = [];
  conversation.replaceChildren();
  starterPrompts.hidden = false;
  input.value = "";
  input.focus();
});

connect();
