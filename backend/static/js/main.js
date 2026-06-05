const novelText = document.getElementById("novelText");
const wordCount = document.getElementById("wordCount");
const chapterCount = document.getElementById("chapterCount");
const chapterHint = document.getElementById("chapterHint");
const chapterList = document.getElementById("chapterList");
const generateBtn = document.getElementById("generateBtn");
const fillExampleBtn = document.getElementById("fillExampleBtn");
const statusText = document.getElementById("statusText");
const yamlOutput = document.getElementById("yamlOutput");
const validationBox = document.getElementById("validationBox");
const downloadBtn = document.getElementById("downloadBtn");
const copyBtn = document.getElementById("copyBtn");
const characterPreview = document.getElementById("characterPreview");
const scenePreview = document.getElementById("scenePreview");

let latestYaml = "";
let latestTitle = "script_output";
let parseTimer = null;

function countText(text) {
  const chinese = (text.match(/[\u4e00-\u9fff]/g) || []).length;
  const english = (text.match(/[A-Za-z0-9_]+/g) || []).length;
  return chinese + english;
}

function setStatus(message) {
  statusText.textContent = message || "";
}

function setValidation(valid, errors = [], warnings = []) {
  validationBox.className = "validation " + (valid ? "ok" : "error");
  if (valid) {
    validationBox.textContent = warnings.length ? `校验通过，提示：${warnings.join("；")}` : "YAML 校验通过";
  } else {
    validationBox.textContent = `校验失败：${errors.join("；")}`;
  }
}

function renderChapters(chapters) {
  chapterList.innerHTML = "";
  chapters.forEach(chapter => {
    const li = document.createElement("li");
    li.textContent = `${chapter.chapter_id}｜${chapter.title}｜${chapter.word_count}字`;
    chapterList.appendChild(li);
  });
}

function renderPreview(data) {
  characterPreview.innerHTML = "";
  scenePreview.innerHTML = "";

  if (!data) return;

  latestTitle = data.title || "script_output";

  (data.characters || []).forEach(character => {
    const li = document.createElement("li");
    li.textContent = `${character.id}｜${character.name}｜${character.role || ""}`;
    characterPreview.appendChild(li);
  });

  (data.scenes || []).forEach(scene => {
    const li = document.createElement("li");
    li.textContent = `${scene.id}｜${scene.title}｜${scene.location || ""}`;
    scenePreview.appendChild(li);
  });
}

async function parseChapters() {
  const text = novelText.value.trim();
  wordCount.textContent = countText(text);

  if (!text) {
    chapterCount.textContent = "0";
    chapterHint.textContent = "请至少输入 3 个章节";
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
      chapterHint.style.color = "#047857";
      generateBtn.disabled = false;
    } else {
      chapterHint.textContent = `当前仅检测到 ${result.chapter_count} 个章节，请至少输入 3 个章节`;
      chapterHint.style.color = "#b45309";
      generateBtn.disabled = true;
    }
  } catch (error) {
    chapterHint.textContent = "章节解析失败，请检查后端服务";
    generateBtn.disabled = true;
  }
}

novelText.addEventListener("input", () => {
  clearTimeout(parseTimer);
  parseTimer = setTimeout(parseChapters, 300);
});

fillExampleBtn.addEventListener("click", async () => {
  const response = await fetch("/api/example");
  const result = await response.json();
  novelText.value = result.novel_text || "";
  await parseChapters();
});

generateBtn.addEventListener("click", async () => {
  const text = novelText.value.trim();
  if (!text) return;

  generateBtn.disabled = true;
  setStatus("生成中，请稍候……");
  yamlOutput.textContent = "";
  validationBox.className = "validation";
  validationBox.textContent = "正在生成并校验 YAML";
  characterPreview.innerHTML = "";
  scenePreview.innerHTML = "";

  try {
    const response = await fetch("/api/generate-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        novel_text: text,
        style: document.getElementById("style").value,
        language: document.getElementById("language").value,
      }),
    });

    const result = await response.json();

    if (!result.success) {
      latestYaml = result.yaml || "";
      yamlOutput.textContent = result.yaml || "";
      setValidation(false, result.validation?.errors || [result.message || "生成失败"]);
      setStatus(result.message || "生成失败");
      downloadBtn.disabled = !latestYaml;
      copyBtn.disabled = !latestYaml;
      return;
    }

    latestYaml = result.yaml || "";
    yamlOutput.textContent = latestYaml;
    setValidation(result.validation.valid, result.validation.errors, result.validation.warnings);
    renderPreview(result.data);
    downloadBtn.disabled = false;
    copyBtn.disabled = false;
    setStatus(result.mock_mode ? "生成完成（Mock 演示模式）" : "生成完成");
  } catch (error) {
    setValidation(false, ["接口请求失败，请确认后端已启动。"]);
    setStatus("生成失败，请稍后重试");
  } finally {
    await parseChapters();
  }
});

copyBtn.addEventListener("click", async () => {
  if (!latestYaml) return;
  await navigator.clipboard.writeText(latestYaml);
  setStatus("YAML 已复制到剪贴板");
});

downloadBtn.addEventListener("click", () => {
  if (!latestYaml) return;
  const safeTitle = (latestTitle || "script_output").replace(/[\\/:*?"<>|\s]+/g, "_");
  const now = new Date();
  const timestamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}`;
  const filename = safeTitle ? `script_${safeTitle}_${timestamp}.yaml` : "script_output.yaml";

  const blob = new Blob([latestYaml], {type: "text/yaml;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});
