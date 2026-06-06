#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "AI 小说转剧本工具 - 快速启动"
echo "无需安装第三方依赖，仅需 Python 3.10+"
python3 -m backend.dev_server --host 127.0.0.1 --port 8000
