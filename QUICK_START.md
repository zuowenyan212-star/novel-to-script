# 启动说明

项目仅有两种启动方式。

## 方式一：快速启动

只需 Python 3.10+，不会安装任何第三方依赖。

### Windows

双击 `start.bat`，或在项目根目录执行：

```powershell
python -m backend.dev_server --host 127.0.0.1 --port 8000
```

### macOS / Linux

```bash
chmod +x start.sh
./start.sh
```

快速启动使用本地演示模型，支持 YAML 生成、编辑、校验、人物关系图谱，以及 txt、md、docx 文件上传。

## 方式二：安装环境启动

需要完整 FastAPI、七牛云 API 或图片 OCR 功能时使用。

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

启动后访问：

```text
http://127.0.0.1:8000
```
