# M3U8 Finder（Windows）

这是一个本地 GUI 工具，用于发现你有权限访问的网页的 HLS `.m3u8` 播放列表，并使用 FFmpeg 保存为 MP4。

## 安装

1. 电脑应安装 Python 3.10+。默认使用你现有的 Python 3.15；如 Playwright 在特定系统下安装失败，可改用 Python 3.13。
2. 双击 `install.bat`：安装 `playwright`、`imageio-ffmpeg`，以及 Playwright 专用的 Chromium 浏览器。
3. 双击 `run.bat` 启动程序。

命令行安装（如需）：

```cmd
python -m pip install -U playwright imageio-ffmpeg
python -m playwright install chromium
python m3u8_finder.py
```

首次安装 Chromium 需要下载浏览器文件。若 Playwright 下载失败，可检查网络连接或设置 HTTPS_PROXY 环境变量后重试。

## 使用

1. 输入 `https://...` 目标网页 URL。
2. 选择两种模式：
   - **网页扫描**：解析当前网页及站内一级链接（同站最多 15 页）。适合静态网页和源码中包含 `.m3u8` 的站点。
   - **浏览器捕获（推荐）**：打开 Chromium，在设定时间内监听请求和 HLS Content-Type；在浏览器中手动点击播放器“播放”、切换集数。适合动态播放器、iframe 和 JavaScript 加载的资源。
3. 搜索结果会自动去重显示。按住 Ctrl/Shift 可选择多个资源。
4. 多码率主播放列表可点击“解析选中清晰度”添加不同分辨率的子列表。
5. 选择保存目录，点击“下载选中”，调用本机 FFmpeg，以不转码方式封装为 MP4。
6. 可以点击“取消下载”终止下载。未完成的临时文件会被清理。

FFmpeg 会先尝试从 PATH 查找；如果找不到，会使用 `imageio-ffmpeg` 自带的二进制文件，因此无需修复 PATH。

## 说明和限制

- 网页扫描不会执行 JavaScript，动态网站请使用浏览器捕获。
- 只处理 HLS `.m3u8`。DASH `.mpd`、普通 `.mp4`、YouTube 专用流协议不在当前版本支持范围。
- 某些资源需要登录 Cookie、特殊授权标头、短时效签名，虽然抓到了 URL，FFmpeg 仍可能收到 HTTP 401/403。当前版本不会自动复制浏览器 Cookie，也不会绕过 DRM、付费墙或访问限制。
- 对于 `EXT-X-STREAM-INF` 的主列表，FFmpeg 默认自动挑选流；可使用“解析选中清晰度”选择具体的码率资源。
- 可能因音视频编码不兼容 MP4、直播未结束、链接过期、源站限制而下载失败。为了保持速度和画质，本工具使用 `-c copy`，不重新编码。
- 可选填写 HTTP(S) 代理，如 `http://127.0.0.1:7890`。浏览器和网页扫描会使用它，下载时会向 FFmpeg 传递 HTTP(S) 代理环境变量；不同 FFmpeg 构建/协议的实际代理支持可能不同。
- 仅访问经你授权的资源；遵守目标网站规则和适用法律。

## 测试项目

```cmd
python -m unittest -v test_m3u8_finder.py
```

可选：若使用特定的本地 Chrome/Chromium，可通过环境变量 `M3U8_BROWSER_EXE` 指定其可执行文件路径。