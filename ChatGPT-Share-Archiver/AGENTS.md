# AGENTS.md — ChatGPT Share Archiver

> **AI Agent / 开发者接手文档**。先看本文件，再读 [README.md](README.md) 和具体源码。本文件记录项目边界、文件职责、数据流、验证方法与已知风险；它不是“线上功能已经全部验证”的保证。

## 1. 项目概况（快速检索）

| 字段 | 内容 |
| --- | --- |
| 项目 | ChatGPT Share Archiver（ChatGPT 聊天记录查看器） |
| 仓库 | `luckierboria-coder/General-Projects` |
| 子目录 | `ChatGPT-Share-Archiver/` |
| 当前代码版本 | v1.1.1（Codex 快照 + PyInstaller onefile 后台进程独立启动修复） |
| 用途 | 本地查看**公开分享**的 ChatGPT 对话 / Codex 任务记录，并保存为可检索的 XML |
| 实现 | Python 3 标准库、原生 HTML/CSS/JavaScript、Chrome/Edge（传统分享）、PyInstaller（Windows EXE） |
| 用户界面 | `http://127.0.0.1:8791/`，只在回环地址开放 |
| 持久化 | `chat_archives/*.xml`，用户本地保存；**不能提交到公共仓库** |
| 许可证 | 仓库根目录 `../LICENSE`（MIT）；非 OpenAI 官方产品 |
| 主要状态 | v1.1.1 增加独立后台进程补丁与 Windows EXE 运行时冒烟测试；线上 Codex 快照端到端验证**仍待补足** |

**不支持**直接读取需要登录的私人对话 `/c/...`、突破访问权限、恢复快照中不存在的内容、自动下载附件二进制或以此代替 ChatGPT 官方数据导出。

## 2. 支持的输入与路由

| 公开链接 | 读取方式 | 特点 |
| --- | --- | --- |
| `https://chatgpt.com/share/<UUID>` | `Chrome/Edge --headless=new --dump-dom`，解析 React Router 注入的页面数据 | 依赖页面内部数据结构，Chrome/Edge 必须可用 |
| `https://chatgpt.com/s/cx_<32位十六进制ID>` | 通过 Python `urllib` 请求 `https://chatgpt.com/backend-api/wham/shared_threads/<cx_ID>` | **无需启动浏览器**；依赖非稳定的内部公开快照接口 |
| `https://chatgpt.com/c/...` | 拒绝 | 私人登录态对话不属于本程序的公开分享读取范围 |

`validated_url()` 将允许的公开分享 URL 规范化：仅 HTTPS、`chatgpt.com` / `chat.openai.com`、标准端口、精确路径格式。**不得简单放开为任意 URL**，否则会把本地服务变成潜在的 SSRF 入口。

注意：`/s/cx_...` 与 `/share/UUID` 不仅 URL 不同，**负载结构也不同**。不能仅通过改正则解决兼容性。

## 3. 源码地图（从这里开始读代码）

```text
ChatGPT-Share-Archiver/
├── AGENTS.md                 # 本文件：Agent 快速接手与维护约定
├── README.md                 # 普通用户说明与命令示例
├── .gitignore                # 排除本地归档、EXE、构建产物、环境文件
├── assets/
│   └── chat-ui.html          # 单文件前端页面，含 CSS + 原生 JS
├── scripts/
│   ├── app_entry.py          # PyInstaller EXE 入口：主程序 / --serve 分流
│   ├── launch_ui.py          # 检查端口、尝试读取 Windows 系统代理、拉起后台服务与浏览器
│   ├── ui_server.py          # 本地 ThreadingHTTPServer、API、会话、XML 保存及下载
│   └── export_shares.py      # URL 校验、两类分享数据抓取/解析、XML 生成、CLI
├── tests/
│   └── test_codex_export.py  # 不联网、不启动 Chrome 的 unittest 回归测试
└── chat_archives/            # 运行时创建；被忽略，不得提交
```

仓库根目录另有 `../.github/workflows/build-chatgpt-share-archiver.yml`，负责 Windows 测试及 EXE 打包。

### 入口函数、关键调用

| 文件 | 函数 / 类 | 责任 |
| --- | --- | --- |
| `scripts/app_entry.py` | `__main__` | EXE 默认调用 `launch_ui.main()`，`--serve` 转入 `ui_server.main()` |
| `scripts/launch_ui.py` | `main()`, `is_our_server()`, `local_proxy()` | 检测 `127.0.0.1:8791`，通过 `/health` 的 `app` 和 `app_root` 判断是否本程序服务；启动后台 HTTP 进程 |
| `scripts/ui_server.py` | `AppServer`, `AppHandler`, `load_chat()`, `export_chat()` | 实现本地 UI/API；暂存已加载记录；保存并下载 XML |
| `scripts/export_shares.py` | `validated_url()`, `is_codex_share()` | 公共分享 URL 校验与路由 |
| 同上 | `fetch_codex_snapshot()`, `_snapshot_body()`, `add_codex_conversation()` | Codex JSON 读取、v1 turns/items 结构校验、可见文本抽取及原始 JSON 保留 |
| 同上 | `find_browser()`, `fetch_rendered()`, `embedded_share_data()`, `add_payload_conversation()` | 浏览器 HTML 获取、React Router 引用负载解析、传统分享 XML 生成 |
| 同上 | `add_dom_conversation()` | CLI 可选择部分 DOM 回退；不等于完整对话归档 |
| 同上 | `main()` | 命令行导出入口 |
| `assets/chat-ui.html` | `api()`, `render()` | `/api/load` 和 `/api/export` 前端交互、消息显示、XML 下载 |

## 4. 关键数据流

### 4.1 图形界面模式

1. 用户启动 `ChatGPT-Share-Archiver.exe`；`app_entry.py` → `launch_ui.py`。
2. `launch_ui.py` 检查 `/health` 或在 `127.0.0.1:8791` 启动 `--serve` 子进程，打开默认浏览器。冻结为 PyInstaller onefile EXE 时，`server_environment()` 将 `PYINSTALLER_RESET_ENVIRONMENT=1` 传给后台子进程，确保它独立解包且不依赖启动器的 `_MEI` 临时目录。
3. 前端 `POST /api/load`（携带 `X-Local-Token`）提交分享 URL。
4. `AppHandler.load_chat()` 通过 `validated_url()` 分类，走 **Codex JSON** 或 **传统分享 HTML** 路径。
5. 两路都归并成 `ElementTree` 的 `<conversation>` / `<message>`；生成供 UI 显示的简化消息数组。
6. 服务器以随机会话 ID 暂存 XML 根节点，最多保留约 10 个会话，尚未导出时只在内存中。
7. 用户输入“项目名称”后 `POST /api/export`，写入 `chat_archives/<项目名>-<标题>.xml`；随后 `GET /api/download?id=...` 下载。

**重点区分**：`/health` 的 `ok: true` 仅确认本地 Web 服务已经启动，不代表外部分享地址抓取成功。

### 4.2 Codex JSON 路径

`fetch_codex_snapshot()` → `_snapshot_body()` → `add_codex_conversation()`。

- 公共 API URL 固定为 `/backend-api/wham/shared_threads/<cx_ID>`；用 `urllib.request` 发起 JSON 请求，不使用浏览器，也无需对话 Cookie。
- 为降低异常响应风险，请求读取上限约 60 MB；HTTP 401/403/404、无效 JSON、未知版本应给出**明确失败**，不要伪造空成功。
- 当前只接受 `version=1`，在 `snapshot` / `thread` / `data` 等层级中寻找 `turns[] -> items[]`；不匹配时**拒绝导出不完整快照**。
- 将 `userMessage` / `agentMessage` 等转换为 UI 消息。进度或推理摘要类型（例如 `agentProgress`、`agentReasoning`）标记为 `channel="commentary"`；仅处理共享负载里实际公开的字段。
- 文件差异、其他未知事件和不可见附件**不强行伪装为文本消息**；整个快照 JSON 保留在 XML 的 `<codex_snapshot_json format="json" version="1">` 中。
- 不下载分享记录中提到的实际附件，也不推断缺失的信息。

### 4.3 传统 ChatGPT `/share/UUID` 路径

`find_browser()` → `fetch_rendered()` → `embedded_share_data()` → `add_payload_conversation()`。

- Chrome/Chromium/Edge 启动 `--headless=new --dump-dom`，使用临时浏览器配置目录及可选代理。
- 解析 `window.__reactRouterContext.streamController.enqueue(...)` 的引用数组、`loaderData`、`routes/share`、`serverResponse`、`linear_conversation`。
- 过滤隐藏/脱敏消息，只处理用户与指定 assistant 通道；XML 包含可用的时间、角色、文本和附件元信息。
- 当浏览器退出码为 0 但 `stdout` 为空时，也应报告“未返回 HTML”，不能据此断言是 React Router 解析失败。
- CLI 的 `--allow-dom-fallback` 仅用于部分可见 DOM 内容，输出会标记 `partial_rendered_dom`；不能无提示取代完整 payload。

## 5. XML 数据契约

根节点：`<chatgpt_share_archive schema_version="1" retrieved_at_utc="..." scope="public_share_user_visible_messages">`。

每个 `<conversation>` 记录 `share_id`、`source_url`、`title`、`message_count` 等属性；`<message>` 记录 `index`、`role`、可选 `channel` / `created_at_utc` / `id`，子元素 `<text format="markdown">`。部分传统分享消息会包含 `<attachments>` 或 `<nontext_part>`。

Codex 记录特别包含：
- `source="codex_shared_snapshot"`、`snapshot_version="1"`、`snapshot_turn_count`、`snapshot_item_count`。
- `<codex_snapshot_json>` 原始快照序列化结果，用于之后重解析和恢复非文本事件信息。

**兼容性要求**：不要随意改动已有 XML 节点名、属性含义、编码（UTF-8）或根 schema；新字段应优先增量添加。存档写入使用 `open("xb")` 与编号后缀避免覆盖旧文件；绝不能静默覆写用户归档。

## 6. 本地运行、测试、云构建

### 源码运行（具有 Python 的开发环境）

在 `ChatGPT-Share-Archiver/` 目录：

```powershell
python scripts/app_entry.py
python -m unittest discover -s tests -v
python scripts/export_shares.py https://chatgpt.com/s/cx_0123456789abcdef0123456789abcdef
python scripts/export_shares.py --json-file sample.json --source-url https://chatgpt.com/s/cx_0123456789abcdef0123456789abcdef
```

上面 URL 仅为格式示例，**不是保证有效的真实分享记录**。单独启动服务：`python scripts/ui_server.py --host 127.0.0.1 --port 8791`。传统分享抓取需要可用的 Chrome/Edge；Codex 路径不需要。Windows 启动器尝试使用系统启用且可连接的本地代理，服务也支持显式 `--proxy`。

### GitHub Actions（推荐构建渠道）

工作流：`../.github/workflows/build-chatgpt-share-archiver.yml`，名称 **ChatGPT Share Archiver - Windows EXE**。

- `push` 到 `main` 且改动 `ChatGPT-Share-Archiver/**` 或该工作流，以及手工 `workflow_dispatch`，都会触发。
- Runner：`windows-latest`；Python：**3.12**。
- 先执行 `python -m unittest discover -s tests -v`，再安装 **PyInstaller 6.16.0**。
- 构建：`pyinstaller --noconfirm --clean --onefile --windowed --name ChatGPT-Share-Archiver --paths scripts --add-data 'assets/chat-ui.html;assets' scripts/app_entry.py`。
- 发布产物为 GitHub Actions 的 `ChatGPT-Share-Archiver-Windows` artifact，其中含 ZIP，ZIP 内有 EXE、README、scripts、assets 和**空的** `chat_archives` 目录。
- Windows 构建成功不等于真实 ChatGPT 接口在线测试成功。当前 unittest 使用的是模拟的 JSON / 网络响应。
- 默认不把 EXE 提交到 Git 仓库；通过 Actions artifact 下载。

## 7. 回归验证矩阵

`tests/test_codex_export.py` 当前包含以下 **6 项离线测试**：

1. 两种分享 URL 的校验、主机和协议拒绝规则。
2. Codex `turns/items` 消息提取以及整个原始快照 JSON 写入 XML。
3. 未知快照版本及异常 turns/items 结构的拒绝行为。
4. XML 不合法控制字符的过滤。
5. UI 加载 Codex 时跳过 Chrome 分支，返回预期源类型和消息数量。
6. 固定公共 JSON API 的请求地址及 Referer 路径（mock 网络）。

推荐的手动冒烟测试：启动新的 EXE → 检查 `/health` → 打开一个**用户有权访问的真实公开** `/s/cx_...` 分享 → 查看消息顺序 → XML 导出 → 用解析器读取 XML 并比对可见消息数、原始 JSON 字段。传统 `/share/UUID` 也必须测试，防止回归。不可将用户的真实快照原样提交到 GitHub。

## 8. 常见故障定位（先看这里）

| 现象 | 更可能的层级 | 首选排查 |
| --- | --- | --- |
| 浏览器打不开 `http://127.0.0.1:8791` | 启动器/端口 | 进程是否启动、8791 端口是否被占用、`--serve` 是否异常退出 |
| `/health` 返回 `{"ok":true}` 但载入失败 | 外部抓取/解析 | 此结果**只证明 HTTP 服务正常**；检查载入错误原文 |
| `expected /share/... ` 或“链接格式不正确” | URL 校验 | 是否是 `/s/cx_...`、`/share/UUID`，是否用了旧 EXE |
| `Chrome/Edge 未返回页面 HTML（退出码 0 ...）` | 传统分享浏览器抓取 | 浏览器 `stdout` 为空；检查无头模式、代理、网络；还未进入 payload 解析 |
| `complete conversation payload absent` | 传统分享 React Router 解析 | 页面内容变化或尚未加载；核查 `embedded_share_data()`，谨慎使用 DOM 回退 |
| `Codex 快照接口 HTTP 401/403/404` | Codex 网络/访问 | 链接是否公开有效、代理是否可用；不绕过认证 |
| `Codex 快照缺少 turns/items` / 不支持 `version` | Codex 数据格式 | 使用去标识化的真实结构样本，扩展解析器并新增测试；不可静默忽略 |
| 导出提示名称为空、同名 XML | 文件存储 | 项目名是文件名前缀；非法 Windows 文件名字符被替换；同名档案生成序号 |
| 旧版本仍然显示原报错 | EXE/端口缓存 | 确认旧进程退出，检查 `/health` 的 `app_root` 是否指向新版目录 |
| `读取失败：[Errno 2] ..._MEI.../base_library.zip` | PyInstaller onefile 后台进程解包目录被提前清理 | v1.1.1 起检查 `launch_ui.server_environment()` 与 `subprocess.Popen(env=...)`；冻结后的 `--serve` 必须使用 `PYINSTALLER_RESET_ENVIRONMENT=1` 作为独立实例，不要靠手动删除 Temp 修复 |

**避免的误判**：`browser exit 0` 并不是“浏览器崩溃”；它可能是正常退出却没有标准输出。传统链接解析失败与 Codex URL 校验失败是不同故障；必须分别排查。

## 9. 安全、隐私与可靠性约束

- 仅处理公开分享，不使用私有对话 Cookie/认证绕过；任何外部地址输入必须经过严格验证。
- Web 服务绑定 `127.0.0.1`；`POST` 接口使用 `X-Local-Token`，不应改成对局域网或公网开放。
- `chat_archives/`、原始聊天 XML/JSON、快照、用户路径、Cookie、账号、代理密码、日志、EXE/打包结果均不得入库；回归 fixture 用人工去标识化样本。
- 与 ChatGPT 的网络交互应考虑超时、代理、非 JSON/重定向、体积上限；不要在错误消息中输出完整用户快照。
- 本项目是公开快照**阅读/归档工具**，不是聊天编辑器；不应擅自写入 ChatGPT 账号或远程分享内容。
- 对已有档案保持前向可读与不覆盖。更改提取规则必须覆盖传统分享和 Codex 两条路径。

## 10. 当前限制与下一步工作

截至 **2026-10-17** 可确认：
- v1.1 已推入 GitHub；原有 6 项离线回归测试通过；Windows Actions 已成功创建 EXE artifact。
- v1.1.1 针对 `base_library.zip` 失踪增加了冻结 EXE 的独立后台实例修复、launcher 回归测试与 Windows 二进制冒烟测试。此项的 GitHub Actions 结果以最新构建记录为准。
- 尚未以真实 Codex 在线快照完成端到端验证；公开内部 JSON API 和其 `version=1` 格式可能改变。
- 传统 ChatGPT 分享 HTML 解析依赖网站内嵌 React Router payload，网站更新会破坏它。
- 原始快照的 JSON 虽能保留未知项目，但 UI 只显示被识别的用户/助手/进度文本；文件变更、工具输出及多模态附件不保证可视化。
- 当前没有独立附件二进制下载器、自动登录、批量账户导出或增量同步功能。

建议后续迭代优先级：
1. 使用去标识化、获许可的真实在线响应确认 Codex API 和 XML 解析。
2. 增加传统 `/share/UUID` 的可复用离线 HTML fixture 和回归测试。
3. 改善后台 `--serve` 启动诊断（目前后台 stdout/stderr 丢弃，难以追踪启动失败）。
4. 如需支持新 `snapshot` 版本，采用版本分支适配并保留原始内容；补充回归测试。
5. 增加不会暴露隐私的错误分类、构建版本号和“程序实际路径”诊断输出。

**修改后交付要求**：说明改动文件与原因；运行 `python -m unittest discover -s tests -v`；如修改打包相关文件，确认 GitHub Actions 成功；将“离线成功 / 云构建成功 / 在线验证成功”作为三个独立状态报告，并同步更新本文件。
