const state = {
  chapterCount: 0,
  yaml: "",
  script: null,
  filename: "script_output.yaml",
};

const els = {
  novelInput: document.querySelector("#novelInput"),
  wordCount: document.querySelector("#wordCount"),
  chapterCount: document.querySelector("#chapterCount"),
  chapterHint: document.querySelector("#chapterHint"),
  inputStatus: document.querySelector("#inputStatus"),
  notice: document.querySelector("#notice"),
  generateButton: document.querySelector("#generateButton"),
  loadExampleButton: document.querySelector("#loadExampleButton"),
  validateButton: document.querySelector("#validateButton"),
  copyButton: document.querySelector("#copyButton"),
  downloadButton: document.querySelector("#downloadButton"),
  yamlOutput: document.querySelector("#yamlOutput"),
  validationBox: document.querySelector("#validationBox"),
  validationSummary: document.querySelector("#validationSummary"),
  providerBadge: document.querySelector("#providerBadge"),
  styleSelect: document.querySelector("#styleSelect"),
  modeSelect: document.querySelector("#modeSelect"),
  detailSelect: document.querySelector("#detailSelect"),
  characterRows: document.querySelector("#characterRows"),
  sceneList: document.querySelector("#sceneList"),
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
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

function updateBasicStats() {
  const text = els.novelInput.value;
  els.wordCount.textContent = localWordCount(text);
  if (!text.trim()) {
    state.chapterCount = 0;
    els.chapterCount.textContent = "0";
    els.chapterHint.textContent = "当前 0 个章节";
    els.inputStatus.textContent = "待输入";
    els.generateButton.disabled = true;
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
    els.inputStatus.textContent = data.meets_requirement ? "可生成" : "章节不足";
    els.generateButton.disabled = !data.meets_requirement;
    if (!data.meets_requirement) {
      setNotice(`当前仅检测到 ${state.chapterCount} 个章节，请至少输入 3 个章节。`, "error");
    } else {
      setNotice("章节检测通过。", "ok");
    }
  } catch (error) {
    setNotice(error.message, "error");
  }
}

function scheduleParse() {
  window.clearTimeout(parseTimer);
  parseTimer = window.setTimeout(parseChapters, 280);
}

async function loadExample() {
  setNotice("正在载入示例...");
  const response = await fetch("/api/example");
  const data = await response.json();
  els.novelInput.value = data.novel_text || "";
  await parseChapters();
}

async function generateScript() {
  if (state.chapterCount < 3) {
    await parseChapters();
    return;
  }
  els.generateButton.disabled = true;
  els.generateButton.textContent = "生成中...";
  setNotice("正在生成剧本...");
  try {
    const data = await apiPost("/api/generate-script", {
      novel_text: els.novelInput.value,
      style: els.styleSelect.value,
      language: "zh-CN",
      adaptation_mode: els.modeSelect.value,
      detail_level: els.detailSelect.value,
    });
    if (!data.success) {
      throw new Error(data.error || "生成结果未通过校验");
    }
    state.yaml = data.yaml || "";
    state.script = data.script || null;
    state.filename = data.filename || "script_output.yaml";
    els.providerBadge.textContent = data.provider === "mock" ? "本地演示模式" : data.provider;
    els.yamlOutput.textContent = state.yaml;
    setValidation(data.validation);
    renderPreview(state.script);
    els.validateButton.disabled = false;
    els.copyButton.disabled = false;
    els.downloadButton.disabled = false;
    setNotice("剧本已生成。", "ok");
  } catch (error) {
    setNotice(error.message, "error");
    setValidation({ valid: false, errors: [error.message], warnings: [] });
  } finally {
    els.generateButton.textContent = "生成剧本";
    els.generateButton.disabled = state.chapterCount < 3;
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

els.novelInput.addEventListener("input", scheduleParse);
els.loadExampleButton.addEventListener("click", loadExample);
els.generateButton.addEventListener("click", generateScript);
els.validateButton.addEventListener("click", validateYaml);
els.copyButton.addEventListener("click", copyYaml);
els.downloadButton.addEventListener("click", downloadYaml);
updateBasicStats();

