# AI 小说转剧本工具

本项目选择比赛题目三：AI 小说转剧本工具。

项目目标是将 3 个章节以上的小说文本自动转换为结构化 YAML 剧本，帮助小说作者快速获得可编辑、可继续打磨的剧本初稿。

## 本版本升级内容

在第一版 MVP 基础上，本版本完成以下增强：

1. 点击复制、下载后增加简约美观的 Toast 提示；
2. 增加多种输入方式：粘贴输入、txt/md 文件、Word docx 文件、图片 OCR；
3. 增加多模型切换：本地演示模型、七牛云 API；
4. 增加人物关系图谱可视化；
5. 优化页面视觉风格和交互体验；
6. 保留章节检测、YAML 校验、角色表预览、场景列表预览等原 MVP 能力。

## 核心功能

- 支持多章节小说文本输入；
- 自动识别章节数量、章节标题和字数；
- 支持上传 txt、md、docx、图片文件；
- 支持本地演示模型，无需 API Key 也能演示完整流程；
- 支持七牛云 OpenAI 兼容 API；
- 生成结构化 YAML 剧本；
- 支持 YAML Schema 校验；
- 支持角色表、场景列表预览；
- 支持人物关系图谱可视化；
- 支持复制 YAML 与下载 `.yaml` 文件；
- 支持示例小说一键填充。

## 项目结构

```text
ai-novel-to-script/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── llm_client.py
│   ├── chapter_parser.py
│   ├── file_parser.py
│   ├── graph_builder.py
│   ├── script_generator.py
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
│   └── development-plan.md
├── examples/
│   ├── novel_sample.txt
│   └── script_output.yaml
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 技术栈

- 后端：Python + FastAPI
- 前端：HTML + CSS + JavaScript
- 模板：Jinja2
- YAML 处理：PyYAML
- 数据校验：Pydantic
- 环境变量：python-dotenv
- 大模型：OpenAI SDK / 七牛云 OpenAI 兼容 API
- Word 解析：python-docx
- 图片 OCR：Pillow + pytesseract
- 图谱可视化：原生 SVG

## 第三方依赖

见 `requirements.txt`，主要包括：

- fastapi
- uvicorn
- jinja2
- python-dotenv
- pydantic
- PyYAML
- openai
- python-multipart
- python-docx
- pillow
- pytesseract
- pytest

说明：图片 OCR 除 Python 包外，还需要本机安装 Tesseract OCR 程序。若未安装，txt、md、docx 上传和核心生成流程不受影响。

## 原创部分说明

本项目原创部分包括：

1. 剧本 YAML Schema 设计；
2. 小说章节识别与章节统计逻辑；
3. 小说转剧本 Prompt 设计；
4. YAML 自动校验与基础修复流程；
5. 七牛云 API 与本地演示模型切换逻辑；
6. 文件上传与文本提取流程；
7. 人物关系图谱生成逻辑；
8. 角色表、场景表预览交互；
9. 复制、下载成功提示交互；
10. 页面视觉与 Demo 演示流程设计。

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例配置：

```bash
cp .env.example .env
```

如果只想使用页面上的“本地演示模型”，可以不填写 API Key。

如需调用七牛云 API，请修改 `.env`：

```env
LLM_PROVIDER=qiniu
LLM_API_KEY=你的七牛云API_KEY
LLM_BASE_URL=https://api.qnaigc.com/v1
LLM_MODEL=deepseek-v3
LLM_USE_SYSTEM_PROXY=false
```

兼容旧版变量名：

```env
OPENAI_API_KEY=你的七牛云API_KEY
OPENAI_BASE_URL=https://api.qnaigc.com/v1
OPENAI_MODEL=deepseek-v3
```

不要将真实 `.env` 文件提交到公开仓库。

### 3. 启动项目

```bash
uvicorn backend.app:app --reload
```

浏览器访问：

```text
http://127.0.0.1:8000
```

## 推荐 Demo 流程

1. 打开首页；
2. 点击“填入示例”；
3. 选择“本地演示模型”；
4. 点击“生成剧本”；
5. 展示 YAML 结果；
6. 点击“复制 YAML”，展示成功提示；
7. 点击“下载 YAML”，展示成功提示；
8. 展示人物关系图谱；
9. 上传 `examples/novel_sample.txt`，展示文件输入能力；
10. 切换到“七牛云 API”，说明可调用真实模型；
11. 打开 `docs/yaml-schema.md` 说明 Schema 设计原因。

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

支持：txt、md、docx、png、jpg、jpeg、webp、bmp。

### 章节解析

```text
POST /api/parse-chapters
```

请求：

```json
{
  "novel_text": "第一章……第二章……第三章……"
}
```

### 剧本生成

```text
POST /api/generate-script
```

请求：

```json
{
  "novel_text": "小说全文",
  "style": "影视剧本",
  "language": "zh-CN",
  "provider": "local",
  "model": "local-rule"
}
```

七牛云调用示例：

```json
{
  "novel_text": "小说全文",
  "style": "影视剧本",
  "language": "zh-CN",
  "provider": "qiniu",
  "model": "deepseek-v3"
}
```

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

## Demo 视频

待补充：请将 Demo 视频上传到 B 站或网盘后，把链接填写到这里。

## 后续迭代方向

- 支持上传 PDF；
- 支持局部重新生成某一场；
- 支持导出 Markdown / JSON；
- 支持拖拽式角色关系图谱；
- 支持用户自定义 Schema；
- 支持更多模型供应商。
