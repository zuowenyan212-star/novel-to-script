const HISTORY_KEY = "novelToScriptHistory";

const state = {
  chapterCount: 0,
  yaml: "",
  script: null,
  filename: "script_output.yaml",
  activeHistoryId: null,
  messages: [],
};

const els = {
  novelInput: document.querySelector("#novelInput"),
  wordCount: document.querySelector("#wordCount"),
  chapterCount: document.querySelector("#chapterCount"),
  chapterHint: document.querySelector("#chapterHint"),
  inputStatus: document.querySelector("#inputStatus"),
  notice: document.querySelector("#notice"),
  generateButton: document.querySelector("#generateButton"),
  newChatButton: document.querySelector("#newChatButton"),
  loadExampleButton: document.querySelector("#loadExampleButton"),
  pasteClipboardButton: document.querySelector("#pasteClipboardButton"),
  uploadFileButton: document.querySelector("#uploadFileButton"),
  fileInput: document.querySelector("#fileInput"),
  dropZone: document.querySelector("#dropZone"),
  validateButton: document.querySelector("#validateButton"),
  copyButton: document.querySelector("#copyButton"),
  downloadButton: document.querySelector("#downloadButton"),
  yamlOutput: document.querySelector("#yamlOutput"),
  validationBox: document.querySelector("#validationBox"),
  validationSummary: document.querySelector("#validationSummary"),
  providerBadge: document.querySelector("#providerBadge"),
  modelModeSelect: document.querySelector("#modelModeSelect"),
  styleSelect: document.querySelector("#styleSelect"),
  modeSelect: document.querySelector("#modeSelect"),
  detailSelect: document.querySelector("#detailSelect"),
  characterRows: document.querySelector("#characterRows"),
  sceneList: document.querySelector("#sceneList"),
  conversation: document.querySelector("#conversation"),
  resultMessage: document.querySelector("#resultMessage"),
  inputSummaryMessage: document.querySelector("#inputSummaryMessage"),
  inputSummaryText: document.querySelector("#inputSummaryText"),
  chatMessages: document.querySelector("#chatMessages"),
  historyList: document.querySelector("#historyList"),
};

let parseTimer = null;

function setNotice(message, type = "neutral") {
  els.notice.textContent = message;
  els.notice.style.color = type === "error" ? "var(--danger)" : type === "ok" ? "var(--ok)" : "var(--muted)";
}

function setValidation(report) {
  els.validationBox.className = "validation-box";
  if (!report) {
    els.validationBox.textContent = "暂无校验结果";
    els.validationSummary.textContent = "等待生成";
    return;
  }
  if (report.valid) {
    els.validationBox.classList.add(report.warnings && report.warnings.length ? "warn" : "ok");
    els.validationBox.textContent = report.warnings && report.warnings.length
      ? `校验通过，提示：${report.warnings.join("；")}`
      : "校验通过，YAML 符合当前 Schema。";
    els.validationSummary.textContent = "校验通过";
  } else {
    els.validationBox.classList.add("error");
    els.validationBox.textContent = `校验失败：${(report.errors || []).join("；")}`;
    els.validationSummary.textContent = "校验失败";
  }
}

function setGenerating(isGenerating, label = "生成中...") {
  els.generateButton.classList.toggle("loading", isGenerating);
  els.resultMessage.classList.toggle("is-loading", isGenerating);
  els.generateButton.disabled = isGenerating || !canSendCurrentInput();
  els.generateButton.textContent = isGenerating ? label : "发送";
}

function canSendCurrentInput() {
  const text = els.novelInput.value.trim();
  if (!text) {
    return false;
  }
  return Boolean(state.yaml || state.chapterCount >= 3);
}

function refreshSendButtonState() {
  els.generateButton.disabled = !canSendCurrentInput();
}

function localWordCount(text) {
  const cjk = text.match(/[\u4e00-\u9fff]/g) || [];
  const latin = text.match(/[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*/g) || [];
  return cjk.length + latin.length;
}

async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

async function apiUpload(path, file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(path, {
    method: "POST",
    body: formData,
  });
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.error || "文件识别失败");
  }
  return data;
}

async function readJsonResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return { error: (await response.text()).slice(0, 240) || "服务未返回 JSON。" };
}

function updateInputSummary() {
  const text = els.novelInput.value.trim();
  if (!text) {
    els.inputSummaryMessage.hidden = true;
    return;
  }
  const preview = text.replace(/\s+/g, " ").slice(0, 160);
  els.inputSummaryText.textContent = `${preview}${text.length > 160 ? "..." : ""}`;
  els.inputSummaryMessage.hidden = false;
}

function updateBasicStats() {
  const text = els.novelInput.value;
  els.wordCount.textContent = localWordCount(text);
  updateInputSummary();
  if (!text.trim()) {
    state.chapterCount = 0;
    els.chapterCount.textContent = "0";
    els.chapterHint.textContent = "当前 0 个章节";
    els.inputStatus.textContent = "待输入";
    refreshSendButtonState();
  } else if (state.yaml) {
    els.inputStatus.textContent = "可续聊";
    refreshSendButtonState();
  }
}

async function parseChapters() {
  const text = els.novelInput.value;
  updateBasicStats();
  if (!text.trim()) {
    return;
  }
  try {
    const data = await apiPost("/api/parse-chapters", { novel_text: text });
    state.chapterCount = data.chapter_count || 0;
    els.chapterCount.textContent = state.chapterCount;
    els.wordCount.textContent = data.total_word_count || localWordCount(text);
    els.chapterHint.textContent = `当前 ${state.chapterCount} 个章节`;
    els.inputStatus.textContent = data.meets_requirement ? "可生成" : state.yaml ? "可续聊" : "章节不足";
    refreshSendButtonState();
    if (!data.meets_requirement) {
      setNotice(
        state.yaml
          ? "将作为本轮修改要求发送。"
          : `当前仅检测到 ${state.chapterCount} 个章节，请至少输入 3 个章节。`,
        state.yaml ? "ok" : "error"
      );
    } else {
      setNotice("章节检测通过，可以生成剧本。", "ok");
    }
  } catch (error) {
    setNotice(error.message, "error");
  }
}

function scheduleParse() {
  window.clearTimeout(parseTimer);
  updateBasicStats();
  refreshSendButtonState();
  parseTimer = window.setTimeout(parseChapters, 280);
}

async function loadExample() {
  setNotice("正在载入示例...");
  const response = await fetch("/api/example");
  const data = await response.json();
  els.novelInput.value = data.novel_text || "";
  await parseChapters();
  scrollConversationToBottom();
}

async function pasteFromClipboard() {
  try {
    if (!navigator.clipboard || !navigator.clipboard.readText) {
      throw new Error("当前浏览器不支持读取剪贴板，请手动粘贴。");
    }
    const text = await navigator.clipboard.readText();
    if (!text.trim()) {
      throw new Error("剪贴板里没有可用文本。");
    }
    els.novelInput.value = text;
    await parseChapters();
    setNotice("已从剪贴板读取文本。", "ok");
    scrollConversationToBottom();
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function uploadFile(file) {
  if (!file) {
    return;
  }
  setNotice(`正在识别文件：${file.name}...`);
  els.uploadFileButton.disabled = true;
  try {
    const extension = file.name.split(".").pop().toLowerCase();
    if (["txt", "md", "markdown"].includes(extension)) {
      els.novelInput.value = await file.text();
      await parseChapters();
      setNotice(`已读取 ${file.name}。`, "ok");
      scrollConversationToBottom();
      return;
    }
    const data = await apiUpload("/api/extract-text", file);
    els.novelInput.value = data.text || "";
    await parseChapters();
    setNotice(`已识别 ${data.filename}，共 ${data.char_count || 0} 个字符。`, "ok");
    scrollConversationToBottom();
  } catch (error) {
    setNotice(error.message, "error");
  } finally {
    els.uploadFileButton.disabled = false;
    els.fileInput.value = "";
  }
}

async function generateScript() {
  const message = els.novelInput.value.trim();
  if (!message) {
    setNotice("请输入小说文本或本轮修改要求。", "error");
    return;
  }
  if (!state.yaml && state.chapterCount < 3) {
    await parseChapters();
    return;
  }
  const isRevision = Boolean(state.yaml && state.chapterCount < 3);
  appendConversationMessage("user", isRevision ? "修改要求" : "小说文本", summarizeForBubble(message));
  state.messages.push({ role: "user", title: isRevision ? "修改要求" : "小说文本", text: summarizeForBubble(message) });
  els.resultMessage.hidden = false;
  setGenerating(true, isRevision ? "改稿中..." : "生成中...");
  setNotice(isRevision ? "正在根据本轮要求更新剧本..." : "正在生成剧本...");
  setValidation(null);
  scrollConversationToBottom();
  try {
    const endpoint = isRevision ? "/api/chat-turn" : "/api/generate-script";
    const payload = isRevision ? {
      message,
      existing_yaml: state.yaml,
      style: els.styleSelect.value,
      language: "zh-CN",
      adaptation_mode: els.modeSelect.value,
      detail_level: els.detailSelect.value,
      model_mode: els.modelModeSelect.value,
    } : {
      novel_text: message,
      style: els.styleSelect.value,
      language: "zh-CN",
      adaptation_mode: els.modeSelect.value,
      detail_level: els.detailSelect.value,
      model_mode: els.modelModeSelect.value,
    };
    const data = await apiPost(endpoint, payload);
    if (!data.success) {
      throw new Error(data.error || "生成结果未通过校验");
    }
    state.yaml = data.yaml || "";
    state.script = data.script || null;
    state.filename = data.filename || "script_output.yaml";
    els.providerBadge.textContent = data.model_mode === "llm" ? `七牛云大模型：${data.model || ""}` : "普通模型（本地）";
    els.yamlOutput.textContent = state.yaml;
    setValidation(data.validation);
    renderPreview(state.script);
    enableResultButtons(true);
    appendConversationMessage("assistant", isRevision ? "已完成本轮改稿" : "已生成剧本", data.reply || "已更新结构化 YAML。");
    state.messages.push({ role: "assistant", title: isRevision ? "已完成本轮改稿" : "已生成剧本", text: data.reply || "已更新结构化 YAML。" });
    saveHistory(data);
    setNotice("剧本已生成。", "ok");
    els.novelInput.value = "";
    updateBasicStats();
  } catch (error) {
    setNotice(error.message, "error");
    setValidation({ valid: false, errors: [error.message], warnings: [] });
    appendConversationMessage("assistant", "处理失败", error.message);
  } finally {
    setGenerating(false);
    refreshSendButtonState();
    scrollConversationToBottom();
  }
}

async function validateYaml() {
  if (!state.yaml) {
    return;
  }
  try {
    const data = await apiPost("/api/validate-yaml", { yaml_text: state.yaml, repair: true });
    setValidation(data);
    setNotice(data.valid ? "YAML 校验通过。" : "YAML 校验失败。", data.valid ? "ok" : "error");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function copyYaml() {
  if (!state.yaml) {
    return;
  }
  await navigator.clipboard.writeText(state.yaml);
  setNotice("YAML 已复制。", "ok");
}

function downloadYaml() {
  if (!state.yaml) {
    return;
  }
  const blob = new Blob([state.yaml], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = state.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderPreview(script) {
  if (!script) {
    els.characterRows.innerHTML = "";
    els.sceneList.innerHTML = "";
    return;
  }
  const characters = Array.isArray(script.characters) ? script.characters : [];
  const characterMap = Object.fromEntries(characters.map((item) => [item.id, item]));
  els.characterRows.innerHTML = characters.map((character) => `
    <tr>
      <td>${escapeHtml(character.id)}</td>
      <td>${escapeHtml(character.name)}</td>
      <td>${escapeHtml(character.role)}</td>
      <td>${escapeHtml(character.goal)}</td>
    </tr>
  `).join("");

  const scenes = Array.isArray(script.scenes) ? script.scenes : [];
  els.sceneList.innerHTML = scenes.map((scene) => {
    const names = (scene.characters || []).map((id) => characterMap[id]?.name || id).join("、");
    const firstLine = Array.isArray(scene.dialogue) && scene.dialogue[0]
      ? `${characterMap[scene.dialogue[0].speaker]?.name || scene.dialogue[0].speaker}：${scene.dialogue[0].line}`
      : "暂无对白";
    return `
      <article class="scene-item">
        <h3>${escapeHtml(scene.id)} ${escapeHtml(scene.title)}</h3>
        <div class="scene-meta">
          <span>${escapeHtml(scene.source_chapter)}</span>
          <span>${escapeHtml(scene.location)}</span>
          <span>${escapeHtml(scene.time)}</span>
          <span>${escapeHtml(names)}</span>
        </div>
        <p>${escapeHtml(scene.summary)}</p>
        <p>${escapeHtml(firstLine)}</p>
      </article>
    `;
  }).join("");
}

function newChat() {
  state.chapterCount = 0;
  state.yaml = "";
  state.script = null;
  state.filename = "script_output.yaml";
  state.activeHistoryId = null;
  state.messages = [];
  els.novelInput.value = "";
  els.yamlOutput.textContent = "生成后的 YAML 会显示在这里。";
  els.resultMessage.hidden = true;
  els.inputSummaryMessage.hidden = true;
  els.chatMessages.innerHTML = "";
  els.characterRows.innerHTML = "";
  els.sceneList.innerHTML = "";
  enableResultButtons(false);
  setValidation(null);
  setNotice("");
  updateBasicStats();
  renderHistory();
}

function saveHistory(data) {
  const script = data.script || {};
  const title = script.title || inferHistoryTitle(els.novelInput.value);
  const item = {
    id: String(Date.now()),
    title,
    createdAt: new Date().toLocaleString(),
    yaml: state.yaml,
    script: state.script,
    filename: state.filename,
    inputPreview: els.novelInput.value.trim().replace(/\s+/g, " ").slice(0, 220),
    validation: data.validation,
    provider: els.providerBadge.textContent,
    messages: state.messages,
  };
  try {
    const history = loadHistory().filter((entry) => entry.id !== state.activeHistoryId);
    history.unshift(item);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 8)));
    state.activeHistoryId = item.id;
    renderHistory();
  } catch {
    setNotice("剧本已生成，但浏览器本地记录空间不足，未保存到最近记录。", "ok");
  }
}

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function renderHistory() {
  const history = loadHistory();
  if (!history.length) {
    els.historyList.innerHTML = "<p>暂无生成记录</p>";
    return;
  }
  els.historyList.innerHTML = history.map((item) => `
    <div class="history-item ${item.id === state.activeHistoryId ? "active" : ""}" data-history-id="${escapeHtml(item.id)}">
      <button class="history-open" data-history-open="${escapeHtml(item.id)}" type="button" title="打开会话">
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.createdAt)}</span>
      </button>
      <button class="history-delete" data-history-delete="${escapeHtml(item.id)}" type="button" title="删除会话">删除</button>
    </div>
  `).join("");
}

function deleteHistoryItem(id) {
  const history = loadHistory().filter((entry) => entry.id !== id);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  if (state.activeHistoryId === id) {
    state.activeHistoryId = null;
    if (history[0]) {
      openHistoryItem(history[0].id);
    } else {
      newChat();
    }
    return;
  }
  renderHistory();
  setNotice("已删除该会话记录。", "ok");
}

function openHistoryItem(id) {
  const item = loadHistory().find((entry) => entry.id === id);
  if (!item) {
    return;
  }
  state.activeHistoryId = item.id;
  state.yaml = item.yaml || "";
  state.script = item.script || null;
  state.filename = item.filename || "script_output.yaml";
  state.messages = Array.isArray(item.messages) ? item.messages : [];
  els.novelInput.value = "";
  els.providerBadge.textContent = item.provider || "历史记录";
  els.yamlOutput.textContent = state.yaml || "生成后的 YAML 会显示在这里。";
  els.resultMessage.hidden = !state.yaml;
  setValidation(item.validation || null);
  renderPreview(state.script);
  renderConversationMessages();
  enableResultButtons(Boolean(state.yaml));
  updateBasicStats();
  els.inputSummaryText.textContent = item.inputPreview || "已打开历史生成结果。";
  els.inputSummaryMessage.hidden = false;
  renderHistory();
  scrollConversationToBottom();
}

function appendConversationMessage(role, title, text) {
  els.chatMessages.insertAdjacentHTML("beforeend", renderMessageHtml(role, title, text));
}

function renderConversationMessages() {
  els.chatMessages.innerHTML = state.messages.map((message) => renderMessageHtml(message.role, message.title, message.text)).join("");
}

function renderMessageHtml(role, title, text) {
  const isUser = role === "user";
  return `
    <article class="message ${isUser ? "user-message" : "assistant-message"} turn-message">
      <div class="avatar">${isUser ? "你" : "AI"}</div>
      <div class="message-body">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(text)}</p>
      </div>
    </article>
  `;
}

function summarizeForBubble(text) {
  const clean = text.replace(/\s+/g, " ").trim();
  return clean.length > 260 ? `${clean.slice(0, 260)}...` : clean;
}

function inferHistoryTitle(text) {
  const match = text.match(/《([^》]{2,30})》/);
  if (match) {
    return match[1];
  }
  return text.trim().split(/\n/).find(Boolean)?.slice(0, 24) || "未命名剧本";
}

function enableResultButtons(enabled) {
  els.validateButton.disabled = !enabled;
  els.copyButton.disabled = !enabled;
  els.downloadButton.disabled = !enabled;
}

function scrollConversationToBottom() {
  requestAnimationFrame(() => {
    els.conversation.scrollTop = els.conversation.scrollHeight;
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.view}View`).classList.add("active");
  });
});

els.historyList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-history-delete]");
  if (deleteButton) {
    event.stopPropagation();
    deleteHistoryItem(deleteButton.dataset.historyDelete);
    return;
  }
  const openButton = event.target.closest("[data-history-open]");
  if (openButton) {
    openHistoryItem(openButton.dataset.historyOpen);
  }
});

els.novelInput.addEventListener("input", scheduleParse);
els.newChatButton.addEventListener("click", newChat);
els.loadExampleButton.addEventListener("click", loadExample);
els.pasteClipboardButton.addEventListener("click", pasteFromClipboard);
els.uploadFileButton.addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", () => uploadFile(els.fileInput.files[0]));
els.dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  els.dropZone.classList.add("dragging");
});
els.dropZone.addEventListener("dragleave", () => els.dropZone.classList.remove("dragging"));
els.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  event.stopPropagation();
  els.dropZone.classList.remove("dragging");
  uploadFile(event.dataTransfer.files[0]);
});
document.addEventListener("dragover", (event) => {
  if (event.dataTransfer && Array.from(event.dataTransfer.types).includes("Files")) {
    event.preventDefault();
    els.dropZone.classList.add("dragging");
  }
});
document.addEventListener("drop", (event) => {
  if (!event.dataTransfer || !event.dataTransfer.files.length) {
    return;
  }
  event.preventDefault();
  els.dropZone.classList.remove("dragging");
  uploadFile(event.dataTransfer.files[0]);
});
els.generateButton.addEventListener("click", generateScript);
els.validateButton.addEventListener("click", validateYaml);
els.copyButton.addEventListener("click", copyYaml);
els.downloadButton.addEventListener("click", downloadYaml);

updateBasicStats();
renderHistory();
