# ChatGPT Share Archiver v2.0 — HTML 优先，高保真离线归档

本项目支持普通 ChatGPT 公开分享链接和 Codex 共享快照。**默认导出可双击离线打开的 HTML，而不是 XML**；同时将可获取的源数据保存为同名 JSON 文件。软件不属于 OpenAI 官方产品。

## 默认导出格式

- 项目名-聊天标题.html：单文件 HTML，内置 CSS，不依赖在线脚本；展示聊天角色、消息顺序、Markdown 标题、粗体、列表、引用、代码块、表格与可转换的 LaTeX 数学公式；每条消息均可展开原始 Markdown。
- 项目名-聊天标题.json：结构化备份，保留未渲染的原始会话字段。Codex 保存接口 JSON 快照；普通 ChatGPT 分享保存 React Router 索引数据（只限公开页面实际返回的内容）。
- 程序将 HTML 和 JSON 同时保存到 chat_archives；浏览器自动下载 HTML，并提供 JSON 备份下载链接。原有 XML 文件不会被覆盖或删除。

## 支持内容与限制

- 支持 https://chatgpt.com/share/UUID 和 https://chatgpt.com/s/cx_... 公开分享。
- 文本尽可能保持原有内容和次序。源数据没有提供的图片原文件、附件二进制、未公开的工具调用结果无法恢复；已有资源引用和非文本记录尽量保留。
- HTML 离线可以查看文本、排版、代码、表格与 MathML 公式；网络图片可能仍需要联网。不会在导出 HTML 中加载第三方 JavaScript。
- 页面结构变化、网络代理、分享权限或接口风控均可能导致抓取失败；请保留诊断信息用于后续适配。

## Windows 使用

在 GitHub Actions 的 ChatGPT Share Archiver - Windows EXE 构建中下载 ChatGPT-Share-Archiver-Windows，解压后双击 ChatGPT-Share-Archiver.exe。此前的 EXE 不会读取新的源码改动，请停止旧后台进程后再运行新 EXE。本地 UI 地址为 http://127.0.0.1:8791。

## 命令行

python scripts/export_shares.py https://chatgpt.com/share/01234567-89ab-cdef-0123-456789abcdef

默认生成 HTML 与 JSON。若需要旧 XML 兼容格式，可使用 --format xml。使用 --format json 则仅保存 JSON 结构备份。

## 历史修复

- v1.1.2：公开分享页直接 HTTPS 获取及 Chrome/Edge 空 HTML 重试。
- v1.1.1：PyInstaller 后台子进程独立解包，避免 base_library.zip 被提前删除。
- 2026-11-04 Crashpad 修复：忽略浏览器临时配置文件清理时的 WinError 5。

## 构建与测试

运行 python -m unittest discover -s tests -v。GitHub Actions 安装 HTML 渲染依赖、执行离线回归测试、构建 PyInstaller Windows EXE，并做启动冒烟测试；真实联网分享读取仍需要在用户环境确认。
