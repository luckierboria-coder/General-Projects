# General-Projects

个人通用软件与自动化工具的公共源码仓库。不同项目相互隔离；不要将不相关工具混入同一目录。

## 项目索引

| 项目 | 目的 | 技术栈 | 文档 | 构建 |
| --- | --- | --- | --- | --- |
| [ChatGPT Share Archiver](ChatGPT-Share-Archiver/) | 读取公开 ChatGPT / Codex 分享链接并保存 XML | Python 3.12、标准库 HTTP 服务、HTML/JavaScript、PyInstaller | [项目 Agent 指南](ChatGPT-Share-Archiver/AGENTS.md) · [用户 README](ChatGPT-Share-Archiver/README.md) | [Windows Actions](.github/workflows/build-chatgpt-share-archiver.yml) |

## 对 AI Agent 的导航

1. **先看根目录 [AGENTS.md](AGENTS.md)**：项目边界、保密要求、仓库惯例。
2. **再看目标项目下的 `AGENTS.md`**：具体架构、入口、数据结构、验证命令、已知限制和修改注意事项。
3. 根据项目的 `README.md`、实际源码和测试确认当前状态，不要把 README 或说明文件视为已完成测试的证明。
4. 新增项目时，在 `<Project>/` 下创建 `README.md` 和 `AGENTS.md`，同时更新本索引。

## 隐私与构建约定

- **禁止提交**聊天记录 XML、原始分享快照（可能包含个人信息）、Cookie、令牌、密钥、本地日志、浏览器用户资料及私人配置。
- 生成的 EXE、ZIP 等二进制产物由 GitHub Actions Artifacts 分发，默认不入库。
- 修改某个项目时，只操作相关目录及必要的工作流文件；不改动其他项目。
- 许可见仓库根目录 [LICENSE](LICENSE)。后续项目如采用不同许可，应在其目录内说明。
