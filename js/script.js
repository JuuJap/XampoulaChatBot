const API_BASE = "/api";
const sessionId = crypto.randomUUID();

const chat = document.getElementById("chat");
const form = document.getElementById("chatForm");
const questionInput = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");
const newChatBtn = document.getElementById("newChatBtn");
const clearSavedBtn = document.getElementById("clearSavedBtn");
const savedList = document.getElementById("savedList");
const savedCount = document.getElementById("savedCount");
const charCount = document.getElementById("charCount");
const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const modelInfo = document.getElementById("modelInfo");
const toast = document.getElementById("toast");

let savedAnswers = [];
let sending = false;
let cooldownTimer = null;
let toastTimer = null;

function showToast(message, type = "info") {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast show ${type === "error" ? "error" : ""}`;
  toastTimer = setTimeout(() => {
    toast.className = "toast";
  }, 3500);
}

function parseError(data, fallback = "Ocorreu um erro.") {
  const detail = data?.detail;
  if (typeof detail === "string") {
    return { message: detail, code: "error", retryAfter: null };
  }
  if (detail && typeof detail === "object") {
    return {
      message: detail.message || fallback,
      code: detail.code || "error",
      retryAfter: detail.retry_after || null,
    };
  }
  return { message: fallback, code: "error", retryAfter: null };
}

function addMessage(role, text, options = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role} ${options.error ? "error" : ""}`;

  if (role === "bot") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "X";
    wrapper.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.appendChild(paragraph);

  if (role === "bot" && options.saveable) {
    const actions = document.createElement("div");
    actions.className = "message-actions";

    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "save-btn";
    saveButton.textContent = "☆ Salvar";
    saveButton.addEventListener("click", () => {
      saveAnswer(options.question || "", text, saveButton);
    });

    actions.appendChild(saveButton);
    bubble.appendChild(actions);
  }

  wrapper.appendChild(bubble);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
  return wrapper;
}

function addTypingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "message bot";
  wrapper.id = "typingMessage";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "X";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';

  wrapper.append(avatar, bubble);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
}

function removeTypingIndicator() {
  document.getElementById("typingMessage")?.remove();
}

function setSending(value) {
  sending = value;
  questionInput.disabled = value;
  sendBtn.disabled = value;
  if (!cooldownTimer) {
    sendBtn.textContent = value ? "Enviando…" : "Enviar";
  }
}

function startCooldown(seconds) {
  clearInterval(cooldownTimer);
  let remaining = Math.max(1, Number(seconds) || 10);
  sendBtn.disabled = true;

  const update = () => {
    sendBtn.textContent = `Aguarde ${remaining}s`;
    remaining -= 1;
    if (remaining < 0) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
      sendBtn.textContent = "Enviar";
      sendBtn.disabled = false;
      questionInput.disabled = false;
      questionInput.focus();
    }
  };

  update();
  cooldownTimer = setInterval(update, 1000);
}

async function sendQuestion(text) {
  if (sending || cooldownTimer) return;

  addMessage("user", text);
  addTypingIndicator();
  setSending(true);

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        question: text,
      }),
    });

    const data = await response.json().catch(() => ({}));
    removeTypingIndicator();

    if (!response.ok) {
      const error = parseError(data, "Não foi possível obter a resposta.");
      addMessage("bot", error.message, { error: true });

      if (response.status === 429) {
        startCooldown(error.retryAfter || 15);
      }
      return;
    }

    addMessage("bot", data.answer, {
      saveable: true,
      question: text,
    });
  } catch (error) {
    removeTypingIndicator();
    addMessage(
      "bot",
      "Não consegui falar com o servidor. Confirme se o python main.py está rodando.",
      { error: true }
    );
  } finally {
    if (!cooldownTimer) {
      setSending(false);
      questionInput.focus();
    } else {
      sending = false;
      questionInput.disabled = true;
    }
  }
}

async function saveAnswer(question, answer, button) {
  if (!question || !answer || button.disabled) return;

  button.disabled = true;
  button.textContent = "Salvando…";

  try {
    const response = await fetch(`${API_BASE}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        question,
        answer,
      }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = parseError(data, "Não foi possível salvar.");
      throw new Error(error.message);
    }

    button.textContent = "✓ Salva";
    showToast("Resposta salva no MySQL.");
    await loadSavedAnswers();
  } catch (error) {
    button.disabled = false;
    button.textContent = "☆ Salvar";
    showToast(error.message || "Erro ao salvar no banco.", "error");
  }
}

function formatDate(value) {
  if (!value) return "agora";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "agora";
  return date.toLocaleString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderSavedAnswers() {
  savedCount.textContent = String(savedAnswers.length);

  if (!savedAnswers.length) {
    savedList.innerHTML = `
      <div class="empty-state">
        <span>☆</span>
        <p>Nenhuma resposta salva.</p>
        <small>Use “Salvar” em uma resposta da IA.</small>
      </div>`;
    return;
  }

  savedList.innerHTML = "";

  savedAnswers.forEach((item) => {
    const card = document.createElement("article");
    card.className = "saved-card";

    const q = document.createElement("p");
    q.className = "saved-question";
    q.textContent = item.pergunta;

    const a = document.createElement("p");
    a.className = "saved-answer";
    a.textContent = item.resposta;

    const meta = document.createElement("div");
    meta.className = "saved-meta";

    const time = document.createElement("span");
    time.textContent = formatDate(item.criado_em);

    const del = document.createElement("button");
    del.type = "button";
    del.className = "card-delete-btn";
    del.textContent = "Excluir";
    del.addEventListener("click", () => deleteSavedAnswer(item.id));

    meta.append(time, del);
    card.append(q, a, meta);
    savedList.appendChild(card);
  });
}

async function loadSavedAnswers() {
  try {
    const response = await fetch(`${API_BASE}/saved/${sessionId}`);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const error = parseError(data, "Banco indisponível.");
      throw new Error(error.message);
    }

    savedAnswers = data.saved || [];
    renderSavedAnswers();
  } catch (error) {
    savedAnswers = [];
    renderSavedAnswers();
  }
}

async function deleteSavedAnswer(id) {
  try {
    const response = await fetch(
      `${API_BASE}/saved/${id}?session_id=${encodeURIComponent(sessionId)}`,
      { method: "DELETE" }
    );
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = parseError(data, "Não foi possível excluir.");
      throw new Error(error.message);
    }

    savedAnswers = savedAnswers.filter((item) => item.id !== id);
    renderSavedAnswers();
    showToast("Resposta excluída.");
  } catch (error) {
    showToast(error.message || "Erro ao excluir.", "error");
  }
}

async function clearSavedAnswers() {
  if (!savedAnswers.length) return;

  try {
    const response = await fetch(`${API_BASE}/saved/session/${sessionId}`, {
      method: "DELETE",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = parseError(data, "Não foi possível limpar.");
      throw new Error(error.message);
    }

    savedAnswers = [];
    renderSavedAnswers();
    showToast("Respostas salvas removidas.");
  } catch (error) {
    showToast(error.message || "Erro ao limpar o banco.", "error");
  }
}

async function resetChat() {
  try {
    await fetch(`${API_BASE}/chat/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch (_) {
    // A interface ainda pode ser limpa mesmo se o backend não responder.
  }

  chat.innerHTML = `
    <div class="message bot">
      <div class="avatar" aria-hidden="true">X</div>
      <div class="bubble"><p>Conversa zerada. Manda outra.</p></div>
    </div>`;
  questionInput.focus();
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();

    modelInfo.textContent = `Modelo: ${data.model || "Gemini"}`;

    if (data.api && data.gemini_configured && data.database) {
      statusBadge.className = "status-badge online";
      statusText.textContent = "Tudo online";
    } else if (data.api && data.gemini_configured) {
      statusBadge.className = "status-badge";
      statusText.textContent = "IA online • MySQL offline";
    } else {
      statusBadge.className = "status-badge error";
      statusText.textContent = "Configuração pendente";
    }
  } catch (_) {
    statusBadge.className = "status-badge error";
    statusText.textContent = "Servidor offline";
    modelInfo.textContent = "Modelo: indisponível";
  }
}

function resizeTextarea() {
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 160)}px`;
  charCount.textContent = `${questionInput.value.length} / 4000`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = questionInput.value.trim();
  if (!text || sending || cooldownTimer) return;

  questionInput.value = "";
  resizeTextarea();
  sendQuestion(text);
});

questionInput.addEventListener("input", resizeTextarea);
questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

newChatBtn.addEventListener("click", resetChat);
clearSavedBtn.addEventListener("click", clearSavedAnswers);

// Tenta encerrar a sessão no servidor ao sair da página.
window.addEventListener("pagehide", () => {
  const payload = new Blob(
    [JSON.stringify({ session_id: sessionId })],
    { type: "application/json" }
  );
  navigator.sendBeacon(`${API_BASE}/session/close`, payload);
});

checkHealth();
loadSavedAnswers();
resizeTextarea();
questionInput.focus();
