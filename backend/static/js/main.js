const novelText = document.getElementById("novelText");
const wordCount = document.getElementById("wordCount");
const chapterCount = document.getElementById("chapterCount");
const chapterHint = document.getElementById("chapterHint");
const chapterList = document.getElementById("chapterList");
const generateBtn = document.getElementById("generateBtn");
const fillExampleBtn = document.getElementById("fillExampleBtn");
const clearBtn = document.getElementById("clearBtn");
const statusText = document.getElementById("statusText");
const yamlEditor = document.getElementById("yamlEditor");
const validationBox = document.getElementById("validationBox");
const downloadBtn = document.getElementById("downloadBtn");
const copyBtn = document.getElementById("copyBtn");
const validateEditBtn = document.getElementById("validateEditBtn");
const restoreBtn = document.getElementById("restoreBtn");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const historyList = document.getElementById("historyList");
const characterPreview = document.getElementById("characterPreview");
const scenePreview = document.getElementById("scenePreview");
const dialoguePreview = document.getElementById("dialoguePreview");
const providerSelect = document.getElementById("providerSelect");
const modelSelect = document.getElementById("modelSelect");
const adaptationStyle = document.getElementById("adaptationStyle");
const fileInput = document.getElementById("fileInput");
const toastWrap = document.getElementById("toastWrap");
const graphEl = document.getElementById("graph");

let latestYaml = "";
let generatedYaml = "";
let latestTitle = "script_output";
let latestGraph = null;
let parseTimer = null;
let editTimer = null;
let historyItems = [];

const fallbackModels = {
  local: [{ value: "local-rule", label: "本地规则演示模型（无需 API Key）" }],
  qiniu: [
    { value: "deepseek-v3", label: "七牛云 DeepSeek V3" },
    { value: "deepseek-chat", label: "七牛云 DeepSeek Chat" },
  ],
};

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastWrap.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(24px)";
    toast.style.transition = "all 0.25s ease";
  }, 2200);

  setTimeout(() => toast.remove(), 2600);
}

function countText(text) {
  const chinese = (text.match(/[\u4e00-\u9fff]/g) || []).length;
  const english = (text.match(/[A-Za-z0-9_]+/g) || []).length;
  return chinese + english;
}

function setStatus(message) {
  statusText.textContent = message || "";
}

function formatTime(date = new Date()) {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
}

function pushHistory(action) {
  const text = yamlEditor.value || "";
  const item = {
    time: formatTime(),
    action,
    length: text.length,
    preview: text.slice(0, 60).replace(/\n/g, " "),
  };
  historyItems.unshift(item);
  historyItems = historyItems.slice(0, 20);
  renderHistory();
}

function renderHistory() {
  historyList.innerHTML = "";
  if (!historyItems.length) {
    const li = document.createElement("li");
    li.textContent = "暂无修改记录";
    historyList.appendChild(li);
    clearHistoryBtn.disabled = true;
    return;
  }

  historyItems.forEach((item, index) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${index + 1}. ${item.action}</strong><br><span>${item.time}｜${item.length} 字｜${item.preview}</span>`;
    historyList.appendChild(li);
  });
  clearHistoryBtn.disabled = false;
}

function setValidation(valid, errors = [], warnings = []) {
  validationBox.className = "validation " + (valid ? "ok" : "error");
  if (valid) {
    validationBox.textContent = warnings.length
      ? `校验通过，提示：${warnings.join("；")}`
      : "YAML 校验通过：结构完整，可继续编辑、复制或下载。";
  } else {
    validationBox.textContent = `校验失败：${errors.join("；") || "未知错误"}`;
  }
}

function updateModelOptions(modelsMap = fallbackModels) {
  const provider = providerSelect.value;
  modelSelect.innerHTML = "";

  const options = modelsMap[provider] || fallbackModels[provider] || [];
  options.forEach(item => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    modelSelect.appendChild(option);
  });
}

async function loadModelOptions() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    const modelsMap = {};
    const providers = data.providers || [];

    if (providers.length) {
      providerSelect.innerHTML = "";
    }
    providers.forEach(provider => {
      modelsMap[provider.value] = provider.models || [];
      const option = document.createElement("option");
      option.value = provider.value;
      option.textContent = provider.label;
      providerSelect.appendChild(option);
    });

    if (data.default_provider) {
      providerSelect.value = data.default_provider;
    }
    updateModelOptions(modelsMap);
    providerSelect.addEventListener("change", () => updateModelOptions(modelsMap));
  } catch (error) {
    updateModelOptions(fallbackModels);
    providerSelect.addEventListener("change", () => updateModelOptions(fallbackModels));
  }
}

function renderChapters(chapters) {
  chapterList.innerHTML = "";
  if (!chapters || !chapters.length) {
    const li = document.createElement("li");
    li.textContent = "暂未检测到章节";
    chapterList.appendChild(li);
    return;
  }

  chapters.forEach(chapter => {
    const li = document.createElement("li");
    li.textContent = `${chapter.chapter_id}｜${chapter.title}｜${chapter.word_count}字`;
    chapterList.appendChild(li);
  });
}

function buildCharacterNameMap(data) {
  const map = {};
  (data?.characters || []).forEach(character => {
    map[character.id] = character.name || character.id;
  });
  return map;
}

function renderPreview(data) {
  characterPreview.innerHTML = "";
  scenePreview.innerHTML = "";
  dialoguePreview.innerHTML = "";

  if (!data) return;

  latestTitle = data.title || "script_output";
  const charMap = buildCharacterNameMap(data);

  (data.characters || []).forEach(character => {
    const li = document.createElement("li");
    li.textContent = `${character.id || ""}｜${character.name || ""}｜${character.role || ""}`;
    characterPreview.appendChild(li);
  });

  (data.scenes || []).forEach(scene => {
    const li = document.createElement("li");
    li.textContent = `${scene.id || ""}｜${scene.source_chapter || ""}｜${scene.title || ""}｜${scene.location || ""}`;
    scenePreview.appendChild(li);
  });

  let dialogues = data.dialogue_index || [];
  if (!dialogues.length) {
    (data.scenes || []).forEach(scene => {
      (scene.dialogue || []).forEach(item => {
        dialogues.push({
          id: item.id || "",
          chapter_id: scene.source_chapter || "",
          scene_id: scene.id || "",
          speaker: item.speaker || "",
          speaker_name: item.speaker_name || charMap[item.speaker] || item.speaker || "",
          line: item.line || "",
        });
      });
    });
  }

  dialogues.slice(0, 30).forEach(dialogue => {
    const li = document.createElement("li");
    const speakerName = dialogue.speaker_name || charMap[dialogue.speaker] || dialogue.speaker || "未知角色";
    li.textContent = `${dialogue.id || ""}｜${dialogue.chapter_id || ""}｜${dialogue.scene_id || ""}｜${speakerName}：${dialogue.line || ""}`;
    dialoguePreview.appendChild(li);
  });
}

async function parseChapters() {
  const text = novelText.value.trim();
  wordCount.textContent = countText(text);

  if (!text) {
    chapterCount.textContent = "0";
    chapterHint.textContent = "请至少输入 3 个章节";
    chapterHint.className = "hint";
    generateBtn.disabled = true;
    chapterList.innerHTML = "";
    return;
  }

  try {
    const response = await fetch("/api/parse-chapters", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({novel_text: text}),
    });
    const result = await response.json();
    chapterCount.textContent = result.chapter_count;
    renderChapters(result.chapters || []);

    if (result.chapter_count >= 3) {
      chapterHint.textContent = "章节数量满足要求";
      chapterHint.className = "hint success";
      generateBtn.disabled = false;
    } else {
      chapterHint.textContent = `当前仅检测到 ${result.chapter_count} 个章节，请至少输入 3 个章节`;
      chapterHint.className = "hint warning";
      generateBtn.disabled = true;
    }
  } catch (error) {
    chapterHint.textContent = "章节解析失败，请检查后端服务";
    chapterHint.className = "hint error";
    generateBtn.disabled = true;
  }
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  setStatus("正在解析上传文件……");
  const response = await fetch("/api/extract-text", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "文件解析失败");
  }

  return response.json();
}

function resetResult() {
  latestYaml = "";
  generatedYaml = "";
  latestGraph = null;
  yamlEditor.value = "";
  validationBox.className = "validation";
  validationBox.textContent = "等待生成结果";
  downloadBtn.disabled = true;
  copyBtn.disabled = true;
  validateEditBtn.disabled = true;
  restoreBtn.disabled = true;
  characterPreview.innerHTML = "";
  scenePreview.innerHTML = "";
  dialoguePreview.innerHTML = "";
  historyItems = [];
  renderHistory();
  drawGraph(null);
}

function setLoading(loading) {
  generateBtn.disabled = loading;
  fileInput.disabled = loading;
  generateBtn.textContent = loading ? "生成中..." : "生成剧本";
}

async function validateEditedYaml(showSuccessToast = true) {
  const text = yamlEditor.value.trim();
  if (!text) {
    showToast("暂无可校验内容", "error");
    return;
  }

  try {
    const response = await fetch("/api/validate-yaml", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({yaml_text: text}),
    });
    const result = await response.json();
    setValidation(result.valid, result.errors || [], result.warnings || []);
    renderPreview(result.data);

    const graphResponse = await fetch("/api/character-graph", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({yaml_text: text}),
    });
    latestGraph = await graphResponse.json();
    drawGraph(latestGraph);

    if (showSuccessToast) {
      showToast(result.valid ? "编辑版 YAML 校验通过" : "编辑版 YAML 仍有问题", result.valid ? "success" : "error");
    }
  } catch (error) {
    setValidation(false, ["校验接口请求失败"]);
    if (showSuccessToast) showToast("校验失败，请确认后端服务正常", "error");
  }
}

async function generateScript() {
  const text = novelText.value.trim();
  if (!text) {
    showToast("请先输入或上传小说文本", "error");
    return;
  }

  setLoading(true);
  setStatus("生成中，请稍候……");
  yamlEditor.value = "";
  validationBox.className = "validation";
  validationBox.textContent = "正在生成并校验 YAML";
  characterPreview.innerHTML = "";
  scenePreview.innerHTML = "";
  dialoguePreview.innerHTML = "";

  try {
    const response = await fetch("/api/generate-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        novel_text: text,
        style: document.getElementById("style").value,
        language: document.getElementById("language").value,
        provider: providerSelect.value,
        model: modelSelect.value,
        adaptation_style: adaptationStyle.value,
      }),
    });

    const result = await response.json();

    latestYaml = result.yaml || "";
    generatedYaml = latestYaml;
    yamlEditor.value = latestYaml || "";
    setValidation(Boolean(result.validation?.valid), result.validation?.errors || [], result.validation?.warnings || []);
    renderPreview(result.data);
    latestGraph = result.graph || null;
    drawGraph(latestGraph);

    downloadBtn.disabled = !latestYaml;
    copyBtn.disabled = !latestYaml;
    validateEditBtn.disabled = !latestYaml;
    restoreBtn.disabled = !latestYaml;

    if (result.success) {
      pushHistory(`生成 YAML（${adaptationStyle.options[adaptationStyle.selectedIndex].text}）`);
      setStatus(result.message || "生成完成");
      showToast(result.mock_mode ? "本地演示生成成功" : "剧本生成成功", "success");
    } else {
      setStatus(result.message || "生成失败");
      showToast(result.message || "生成失败，请检查配置", "error");
    }
  } catch (error) {
    setValidation(false, ["接口请求失败，请确认后端已启动。"]);
    setStatus("生成失败，请稍后重试");
    showToast("生成失败，请确认后端服务已启动", "error");
  } finally {
    setLoading(false);
    await parseChapters();
  }
}

async function copyYaml() {
  const text = yamlEditor.value.trim();
  if (!text) {
    showToast("暂无可复制内容", "error");
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    pushHistory("复制编辑版 YAML");
    showToast("复制成功，已复制编辑后的 YAML", "success");
  } catch (error) {
    showToast("复制失败，请手动选择文本复制", "error");
  }
}

function downloadYaml() {
  const text = yamlEditor.value.trim();
  if (!text) {
    showToast("暂无可下载内容", "error");
    return;
  }

  const safeTitle = (latestTitle || "script_output").replace(/[\\/:*?"<>|\s]+/g, "_");
  const now = new Date();
  const timestamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}`;
  const filename = safeTitle ? `script_${safeTitle}_${timestamp}.yaml` : "script_output.yaml";

  const blob = new Blob([text], {type: "text/yaml;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);

  pushHistory("下载编辑版 YAML");
  showToast("下载成功，已保存编辑后的 YAML", "success");
}

function drawGraph(graph) {
  graphEl.innerHTML = "";

  if (!graph || !graph.nodes || graph.nodes.length === 0) {
    graphEl.innerHTML = `<div class="empty-graph">生成剧本后，这里会展示人物关系图谱。</div>`;
    return;
  }

  const width = graphEl.clientWidth || 1000;
  const height = 420;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.34;

  const nodes = graph.nodes.map((node, index) => {
    const angle = (Math.PI * 2 * index) / graph.nodes.length;
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  const nodeMap = {};
  nodes.forEach(node => {
    nodeMap[node.id] = node;
  });

  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const edgeGroup = document.createElementNS(svgNS, "g");
  const nodeGroup = document.createElementNS(svgNS, "g");

  (graph.edges || []).forEach(edge => {
    const source = nodeMap[edge.source];
    const target = nodeMap[edge.target];
    if (!source || !target) return;

    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", source.x);
    line.setAttribute("y1", source.y);
    line.setAttribute("x2", target.x);
    line.setAttribute("y2", target.y);
    line.setAttribute("stroke", "#a5b4fc");
    line.setAttribute("stroke-width", Math.min(6, 1.5 + (edge.weight || 1)));
    line.setAttribute("opacity", "0.75");
    edgeGroup.appendChild(line);

    if (edge.weight > 1) {
      const label = document.createElementNS(svgNS, "text");
      label.setAttribute("x", (source.x + target.x) / 2);
      label.setAttribute("y", (source.y + target.y) / 2);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", "11");
      label.setAttribute("fill", "#6366f1");
      label.textContent = edge.weight;
      edgeGroup.appendChild(label);
    }
  });

  nodes.forEach(node => {
    const group = document.createElementNS(svgNS, "g");

    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", node.x);
    circle.setAttribute("cy", node.y);
    circle.setAttribute("r", 28);
    circle.setAttribute("fill", "#4f46e5");
    circle.setAttribute("opacity", "0.94");

    const initials = document.createElementNS(svgNS, "text");
    initials.setAttribute("x", node.x);
    initials.setAttribute("y", node.y + 5);
    initials.setAttribute("text-anchor", "middle");
    initials.setAttribute("font-size", "15");
    initials.setAttribute("font-weight", "700");
    initials.setAttribute("fill", "#ffffff");
    initials.textContent = (node.label || node.id).slice(0, 2);

    const text = document.createElementNS(svgNS, "text");
    text.setAttribute("x", node.x);
    text.setAttribute("y", node.y + 50);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", "13");
    text.setAttribute("fill", "#1f2937");
    text.textContent = node.label || node.id;

    group.appendChild(circle);
    group.appendChild(initials);
    group.appendChild(text);
    nodeGroup.appendChild(group);
  });

  svg.appendChild(edgeGroup);
  svg.appendChild(nodeGroup);
  graphEl.appendChild(svg);
}

novelText.addEventListener("input", () => {
  clearTimeout(parseTimer);
  parseTimer = setTimeout(parseChapters, 300);
});

yamlEditor.addEventListener("input", () => {
  latestYaml = yamlEditor.value;
  if (!latestYaml.trim()) return;

  downloadBtn.disabled = false;
  copyBtn.disabled = false;
  validateEditBtn.disabled = false;
  restoreBtn.disabled = !generatedYaml;

  clearTimeout(editTimer);
  editTimer = setTimeout(() => {
    pushHistory("编辑 YAML 内容");
  }, 800);
});

fillExampleBtn.addEventListener("click", async () => {
  const response = await fetch("/api/example");
  const result = await response.json();
  novelText.value = result.novel_text || "";
  await parseChapters();
  showToast("示例小说已填入", "success");
});

clearBtn.addEventListener("click", async () => {
  novelText.value = "";
  resetResult();
  await parseChapters();
  showToast("输入内容已清空", "info");
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  try {
    const result = await uploadFile(file);
    novelText.value = result.text || "";
    await parseChapters();
    showToast(result.message || "文件解析成功", "success");
    setStatus(`已解析文件：${result.filename || file.name}`);
  } catch (error) {
    showToast(error.message || "文件解析失败", "error");
    setStatus("文件解析失败");
  } finally {
    fileInput.value = "";
  }
});

generateBtn.addEventListener("click", generateScript);
copyBtn.addEventListener("click", copyYaml);
downloadBtn.addEventListener("click", downloadYaml);
validateEditBtn.addEventListener("click", () => validateEditedYaml(true));

restoreBtn.addEventListener("click", async () => {
  if (!generatedYaml) return;
  yamlEditor.value = generatedYaml;
  latestYaml = generatedYaml;
  pushHistory("恢复为生成版 YAML");
  await validateEditedYaml(false);
  showToast("已恢复为生成版 YAML", "success");
});

clearHistoryBtn.addEventListener("click", () => {
  historyItems = [];
  renderHistory();
  showToast("修改历史已清空", "info");
});

renderHistory();
loadModelOptions();
parseChapters();
