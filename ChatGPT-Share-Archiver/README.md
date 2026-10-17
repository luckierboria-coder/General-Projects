# ChatGPT Share Archiver v1.1.1 — 支持 Codex 共享快照及独立后台进程修复

本项目保留原 ChatGPT 分享阅读/导出功能，并增加 **Codex 共享快照**（`https://chatgpt.com/s/cx_...`）支持。它不是官方 OpenAI 软件。

## 支持的链接

- `https://chatgpt.com/share/<UUID>`：沿用原来的 Chrome/Edge 分享页抓取、React Router payload 解析。
- `https://chatgpt.com/s/cx_<32个十六进制字符>`：直接请求公开共享快照 JSON API，不启动无头浏览器。

Codex 页面包含的用户消息、助手回复、进度/推理摘要（若公开快照包含）可显示在阅读界面；**原始快照 JSON 以 `<codex_snapshot_json>` 存放在 XML 的 `<conversation>` 下**，其他事件项、差异、资源信息不被丢弃。快照本身没有的附件二进制、工具调用原始结果和未公开信息，软件无法恢复。

## Windows 用户

请使用 GitHub Actions 构建后下载的 `ChatGPT_Share_Archiver_Windows.zip`，解压后双击新的 `ChatGPT-Share-Archiver.exe`。**不要继续运行旧 EXE**，旧 EXE 不会自动读取外部新 Python 源码。已有 `chat_archives` 保留，并复制回新软件目录即可；**不要覆盖或删除原 XML**。旧程序可能仍在运行：升级前在任务管理器结束旧 `ChatGPT-Share-Archiver.exe`，确保 8791 端口可被新程序使用。

本地 UI 仍位于 `http://127.0.0.1:8791`。若健康检查返回 `ok: true`，只是服务运行正常，不代表网络抓取一定成功。

### v1.1.1 修复：找不到 `_MEI.../base_library.zip`

旧版 `--onefile` EXE 运行时，启动器与长期运行的 `--serve` 后台进程可能共享 PyInstaller 临时解包目录；启动器退出会删除该目录，后台服务随后出现 `读取失败：[Errno 2] No such file or directory: ..._MEI.../base_library.zip`。v1.1.1 在冻结模式启动后台进程时设置 `PYINSTALLER_RESET_ENVIRONMENT=1`，令服务作为**独立的 PyInstaller 实例**重新解包；源码运行时仍继承原环境。

升级前请退出旧版后台进程及 EXE，再解压新包运行；**不需删除 `chat_archives` 或清理 Windows Temp**。勿把旧 EXE 与新源码混用。此补丁不改变 ChatGPT/Codex 数据解析逻辑。GitHub Actions 添加了 Windows EXE 后台服务冒烟验证（CI 设置 `CHATGPT_ARCHIVER_NO_BROWSER=1`，避免非交互 Runner 启动浏览器；用户正常运行不受影响），避免只验证编译成功。


## GitHub Actions 云编译

源码位于 `General-Projects/ChatGPT-Share-Archiver/`，Windows 构建工作流在仓库根目录 `.github/workflows/build-chatgpt-share-archiver.yml`。在 GitHub Actions 页面运行 **Windows EXE build** 工作流，下载 Artifacts 中的 `ChatGPT-Share-Archiver-Windows`；Windows runner 会自动运行离线回归测试并使用 PyInstaller 打包 EXE。本地无需安装 Python 或编译器。

## 源码命令行

```text
python scripts/export_shares.py https://chatgpt.com/s/cx_0123456789abcdef0123456789abcdef
python scripts/export_shares.py --json-file sample.json --source-url https://chatgpt.com/s/cx_0123456789abcdef0123456789abcdef
python -m unittest discover -s tests -v
```

## 边界与限制

公开快照接口 `/backend-api/wham/shared_threads/...` 是未正式承诺稳定性的内部接口，未来接口或 v1 数据结构变化需要继续适配。当前环境无法在线访问 ChatGPT API，因此 v1 解析器已做离线结构回归测试，**但还没有用实际线上快照完成端到端验证**。如果线上解析失败，请提供 HTTP 状态或去标识化的快照 JSON 结构，以便针对真实结构补丁修正。不会绕过访问权限。