# AI 小说转剧本工具

本项目选择比赛题目三：AI 小说转剧本工具。

项目目标是将 3 个章节以上的小说文本自动转换为结构化 YAML 剧本，帮助小说作者快速获得可编辑、可继续打磨的剧本初稿。

## 当前版本：v0.3.1


### v0.3.1 修复说明

v0.3.1 在 v0.3 基础上修复了本地演示模型中角色名识别过度的问题。例如“王林苦笑说道”现在会识别为“王林”，不会再把“苦笑”合并进角色名；“台上朗声说道”“一眼沉声说道”等叙事片段也会被过滤，避免误判为人物。

同时，结构化预览区域不再单独展示“章节剧本预览”列表，章节划分仍完整保留在最终 YAML 的 `chapter_scripts` 字段中，避免页面重复拆分展示造成理解负担。

v0.3 在 v0.2 基础上继续增强以下能力：

1. **双启动模式**：快速启动只需 Python、不会自动安装依赖；安装环境启动提供完整 FastAPI、七牛云 API、图片 OCR 等能力；
2. **YAML 在线编辑**：生成后的 YAML 可直接在页面中编辑；
3. **编辑版复制/下载**：复制和下载均使用用户编辑后的 YAML 内容；
4. **修改历史记录**：页面记录生成、编辑、复制、下载、恢复等操作；
5. **按章节划分 YAML**：新增 `chapter_scripts` 字段，便于按章节查看剧本；
6. **独立台词索引**：新增 `dialogue_index` 字段，将所有台词单独拉出列表，并标清章节、场景、人物和台词内容；
7. **改编风格选择**：支持“忠于原文”“增强戏剧冲突化”“口语化”三种生成风格；
8. **保留 v0.2 能力**：多输入方式、多模型切换、人物关系图谱、Toast 提示、YAML 校验等能力继续保留。

## 核心功能

- 支持多章节小说文本输入；
- 自动识别章节数量、章节标题和字数；
- 支持上传 txt、md、docx、图片文件；
- 支持本地演示模型，无需 API Key 也能演示完整流程；
- 支持七牛云 OpenAI 兼容 API；
- 支持选择改编风格；
- 生成结构化 YAML 剧本；
- YAML 支持在线编辑、校验、复制和下载；
- 支持修改历史记录；
- 支持按章节查看剧本结构；
- 支持台词索引预览；
- 支持人物关系图谱可视化；
- 支持示例小说一键填充。

## 项目结构

```text
ai-novel-to-script/
├── backend/
│   ├── app.py
│   ├── dev_server.py
│   ├── config.py
│   ├── llm_client.py
│   ├── chapter_parser.py
│   ├── file_parser.py
│   ├── graph_builder.py
│   ├── script_generator.py
│   ├── yaml_codec.py
│   ├── yaml_validator.py
│   ├── prompt_templates.py
│   ├── schemas.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── docs/
│   ├── yaml-schema.md
│   ├── development-plan.md
│   └── upgrade-pr-plan.md
├── examples/
│   ├── novel_sample.txt
│   └── script_output.yaml
├── tests/
├── QUICK_START.md
├── requirements.txt
├── start.bat
├── start.sh
├── .env.example
├── .gitignore
└── README.md
```

## 启动方式

项目仅保留以下两种启动方式。

### 方式一：快速启动

适合直接体验本地演示模型。只要求本机已安装 Python 3.10 或更高版本，不创建虚拟环境、不执行 `pip install`，也不会修改本机 Python 环境。

#### Windows

双击运行：

```text
start.bat
```

或在项目根目录执行：

```bash
python -m backend.dev_server --host 127.0.0.1 --port 8000
```

#### macOS / Linux

```bash
chmod +x start.sh
./start.sh
```

也可以直接执行：

```bash
python3 -m backend.dev_server --host 127.0.0.1 --port 8000
```

快速启动支持章节解析、本地规则生成、YAML 编辑与校验、人物关系图谱，以及 txt、md、docx 文件上传。七牛云 API 和图片 OCR 请使用方式二。

### 方式二：安装环境启动

适合使用完整 FastAPI 服务、七牛云 API、图片 OCR 和全部第三方依赖能力。

#### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

如果 PowerShell 不允许执行激活脚本，也可以不激活环境：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

两种方式启动后都访问：

```text
http://127.0.0.1:8000
```

## 七牛云 API 配置

七牛云 API 仅在“方式二：安装环境启动”中使用。不配置 API Key 时，可以继续选择页面中的“本地演示模型”。

如需调用七牛云 API，请复制 `.env.example` 为 `.env`，并填写：

```env
LLM_PROVIDER=qiniu
LLM_API_KEY=你的七牛云API_KEY
LLM_BASE_URL=https://api.qnaigc.com/v1
LLM_MODEL=deepseek-v3
LLM_USE_SYSTEM_PROXY=false
```

不要将真实 `.env` 文件提交到公开仓库。

## v0.3 YAML 结构说明

v0.3 推荐输出 `schema_version: "1.1"`，新增两个核心字段：

### 1. chapter_scripts

按章节组织剧本，记录每章对应哪些场景：

```yaml
chapter_scripts:
  - chapter_id: "chapter_001"
    chapter_title: "第一章 初入县衙"
    summary: "本章剧情摘要"
    scene_ids:
      - "scene_001"
```

### 2. dialogue_index

将所有台词独立拉出，便于作者快速查看人物对白：

```yaml
dialogue_index:
  - id: "dialogue_001"
    chapter_id: "chapter_001"
    chapter_title: "第一章 初入县衙"
    scene_id: "scene_001"
    speaker: "char_001"
    speaker_name: "林安"
    line: "那就从第一桩开始。"
    emotion: "平静"
```

## 推荐 Demo 流程

1. 打开首页；
2. 点击“填入示例”；
3. 选择“本地演示模型”；
4. 选择改编风格，例如“忠于原文”或“增强戏剧冲突化”；
5. 点击“生成剧本”；
6. 展示 YAML 编辑器；
7. 手动修改一行 YAML，展示修改历史记录；
8. 点击“校验编辑版”，确认编辑后的 YAML 可以校验；
9. 点击“复制 YAML”和“下载 YAML”，展示成功提示；
10. 展示章节剧本预览、台词索引预览和人物关系图谱；
11. 如已配置七牛云 API，切换到“七牛云 API”测试真实模型调用。

## API 接口

### 首页

```text
GET /
```

### 模型选项

```text
GET /api/models
```

### 示例文本

```text
GET /api/example
```

### 文件文本提取

```text
POST /api/extract-text
```

### 章节解析

```text
POST /api/parse-chapters
```

### 剧本生成

```text
POST /api/generate-script
```

请求示例：

```json
{
  "novel_text": "小说全文",
  "style": "影视剧本",
  "language": "zh-CN",
  "provider": "local",
  "model": "local-rule",
  "adaptation_style": "faithful"
}
```

`adaptation_style` 可选：

- `faithful`：忠于原文；
- `dramatic`：增强戏剧冲突化；
- `colloquial`：口语化。

### YAML 校验

```text
POST /api/validate-yaml
```

### 人物关系图谱

```text
POST /api/character-graph
```

## 测试

```bash
pytest
```

## 原创部分说明

本项目原创部分包括：

1. 剧本 YAML Schema 设计；
2. 小说章节识别与章节统计逻辑；
3. 小说转剧本 Prompt 设计；
4. YAML 自动校验与基础修复流程；
5. 七牛云 API 与本地演示模型切换逻辑；
6. 文件上传与文本提取流程；
7. 人物关系图谱生成逻辑；
8. YAML 在线编辑与修改历史记录；
9. 按章节划分 YAML 和台词索引设计；
10. 复制、下载成功提示交互；
11. 页面视觉与 Demo 演示流程设计。

## 后续迭代方向

- 支持上传 PDF；
- 支持局部重新生成某一场；
- 支持导出 Markdown / JSON；
- 支持拖拽式角色关系图谱；
- 支持用户自定义 Schema；
- 支持更多模型供应商。
