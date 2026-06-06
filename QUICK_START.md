# v0.4 快速启动说明

v0.4 修复并增强了 `start.bat` 快速启动流程。用户下载项目后，不需要手动安装 requirements，也可以快速体验；配置七牛云 API Key 后，快速启动模式也能直接调用大模型。

## Windows

双击：

```text
start.bat
```

启动脚本会自动：

1. 切换到项目根目录；
2. 检测 `py -3` 或 `python`；
3. 打开浏览器访问 `http://127.0.0.1:8000`；
4. 启动本地服务；
5. 如未配置七牛云 API Key，会询问是否现在配置。

也可以在终端运行：

```powershell
python -m backend.dev_server --setup-qiniu --host 127.0.0.1 --port 8000
```

## macOS / Linux

```bash
chmod +x start.sh
./start.sh
```

## 七牛云大模型配置

启动时按提示输入 API Key，或提前复制 `.env.example` 为 `.env`，填写：

```env
LLM_PROVIDER=qiniu
LLM_API_KEY=你的七牛云API_KEY
LLM_BASE_URL=https://api.qnaigc.com/v1
LLM_MODEL=deepseek-v3
LLM_USE_SYSTEM_PROXY=false
```

配置后页面会默认选择“七牛云 API”。如果你的网络需要代理访问模型接口，将：

```env
LLM_USE_SYSTEM_PROXY=true
```

## v0.4 新增能力

选择大模型后，可以使用“AI 短片辅助创作”模块：

- 生成分镜建议；
- 生成镜头提示词；
- 捕获角色情绪；
- 生成微表情提示词；
- 生成场景描绘提示词；
- 支持漫剧、真人短剧、电影感、动画风格。

如果当前选择本地演示模型，上述能力会禁用，并提示需要选择大模型。

## 访问地址

```text
http://127.0.0.1:8000
```
