# Windows 快速启动

当前仓库没有 `start.bat`，请在项目根目录打开 PowerShell 或终端运行命令。

## 零依赖快速体验

要求 Windows 已安装 Python 3.10 或更高版本：

```powershell
python -m backend.dev_server --host 127.0.0.1 --port 8000
```

启动成功后访问：

```text
http://127.0.0.1:8000
```

按 `Ctrl+C` 停止服务。

快速模式不会创建虚拟环境，也不会安装依赖。它支持本地规则模型、TXT/Markdown/DOCX 上传、YAML 编辑与校验、人物关系图谱，以及已配置七牛云 API 时的大模型和 AI 短片辅助能力。

## 启动时配置七牛云

```powershell
python -m backend.dev_server --setup-qiniu --host 127.0.0.1 --port 8000
```

按终端提示输入 API Key、模型名和 Base URL。配置会写入本地 `.env`，请勿提交包含真实密钥的文件。

也可以复制 `.env.example` 为 `.env` 后手动填写：

```env
LLM_PROVIDER=qiniu
LLM_API_KEY=your_qiniu_api_key_here
LLM_BASE_URL=https://api.qnaigc.com/v1
LLM_MODEL=deepseek-v3
LLM_USE_SYSTEM_PROXY=false
```

## 完整环境启动

图片 OCR 和 FastAPI 完整服务需要安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

图片 OCR 还要求 Windows 已安装 Tesseract OCR。

## 常见问题

### `python` 命令不存在

重新安装 Python，并在安装界面勾选“Add Python to PATH”，然后重新打开终端。

### 端口 8000 已被占用

改用其他端口：

```powershell
python -m backend.dev_server --host 127.0.0.1 --port 8010
```

访问 `http://127.0.0.1:8010`。

### 页面可打开但七牛云不可用

检查 `.env` 中的 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。修改后停止并重新启动服务。
