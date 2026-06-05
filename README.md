# AI 小说转剧本工具

一个面向小说作者的网页工具，可将 3 个章节以上的小说文本转换为结构化 YAML 剧本初稿，并提供章节检测、角色表预览、场景列表预览、YAML 校验和下载。

## 已实现功能

- 多章节小说文本输入与实时字数统计
- 常见章节标题识别：`第一章`、`第1章`、`Chapter 1`、`一、开端`
- 至少 3 个章节的生成前校验
- 本地演示生成器：无 API Key 也能生成可校验 YAML
- OpenAI 兼容接口调用：可接入 OpenAI、DeepSeek、通义千问等兼容服务
- YAML Schema 校验与轻量自动修复
- 前端 YAML 预览、角色表预览、场景列表预览
- 复制 YAML 与下载 `.yaml` 文件
- 示例小说输入与示例 YAML 输出

## 项目结构

```text
backend/
  app.py                  FastAPI 应用入口
  dev_server.py           零依赖本地演示服务器
  config.py               环境变量配置
  llm_client.py           OpenAI 兼容接口客户端
  chapter_parser.py       小说章节解析
  script_generator.py     剧本生成编排
  yaml_codec.py           YAML 编解码
  yaml_validator.py       YAML Schema 校验
  prompt_templates.py     大模型提示词
  templates/index.html    前端页面
  static/                 CSS 与 JavaScript
docs/
  yaml-schema.md          YAML Schema 设计文档
  development-plan.md     开发计划与记录
examples/
  novel_sample.txt        示例小说文本
  script_output.yaml      示例剧本输出
tests/
  test_chapter_parser.py
  test_yaml_validator.py
```

## 快速运行

当前环境没有安装 FastAPI 时，可以先使用零依赖演示服务器：

```bash
python -m backend.dev_server --host 127.0.0.1 --port 8000
```

浏览器访问：

```text
http://127.0.0.1:8000
```

## 使用 FastAPI 运行

创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

启动服务：

```bash
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

## 大模型配置

默认配置为 `LLM_PROVIDER=mock`，使用本地演示生成器，不需要 API Key。要调用真实大模型，复制 `.env.example` 为 `.env` 并配置：

```env
LLM_PROVIDER=openai-compatible
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

七牛云大模型可按 OpenAI 兼容接口配置：

```env
LLM_PROVIDER=qiniu
QINIU_API_KEY=your_qiniu_api_key_here
QINIU_BASE_URL=https://openai.qiniu.com/v1
QINIU_MODEL=deepseek-v3
```

如果控制台显示模型名不同，以七牛云模型广场中的模型 ID 为准。DeepSeek、通义千问等其他 OpenAI 兼容接口只需要替换 `LLM_BASE_URL`、`LLM_MODEL` 和 API Key。

## 测试

项目核心逻辑使用标准库 `unittest`，不依赖 pytest：

```bash
python -m unittest discover -s tests
```

## 接口

- `GET /`：网页首页
- `GET /api/example`：读取示例小说
- `POST /api/parse-chapters`：解析章节数量与章节信息
- `POST /api/generate-script`：生成 YAML 剧本
- `POST /api/validate-yaml`：校验 YAML 是否符合 Schema

## 说明

需求文档中要求“API Key 未配置时提示错误”。为了让 Demo 更稳定，本项目将默认模式调整为本地演示生成器；当 `LLM_PROVIDER` 设置为远程兼容接口时，仍会严格检查 API Key 并返回明确错误。

Demo 视频链接需要在本地录屏后补充到项目说明中。
