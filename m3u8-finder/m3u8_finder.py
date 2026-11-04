# -*- coding: utf-8 -*-
"""M3U8 Finder: limited site crawler, browser network capture, FFmpeg download GUI.
Only scan/download content for which you have permission.
"""
from __future__ import annotations

import html
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from tkinter import Tk, StringVar, END, filedialog, messagebox, ttk
from tkinter import scrolledtext
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urldefrag
from urllib.request import Request, ProxyHandler, build_opener

APP_NAME = "M3U8 Finder"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
MAX_HTML_BYTES = 2_000_000
MAX_CRAWL_PAGES = 15

# Includes absolute, root-relative, directory-relative and filename-only HLS paths.
# A post-filter prevents unrelated text from being accepted as an HTTP URL.
M3U8_RE = re.compile(
    r'''(?ix)
    (?: https?:// | // | \.\./ | \./ | / | (?<![A-Z0-9_])[A-Z0-9_.%-] )
    [A-Z0-9_~%.:@!$&*+;/-]*?\.m3u8
    (?:\?[A-Z0-9_~%.:@!$&*+;=/?#-]*)?
    '''
)
TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
RES_RE = re.compile(r"(?i)\bRESOLUTION=(\d+x\d+)")
BW_RE = re.compile(r"(?i)\bBANDWIDTH=(\d+)")


def normalize_url(raw: str, base_url: str) -> str | None:
    raw = html.unescape(raw).strip().strip("\"'` ")
    raw = raw.replace("\\/", "/").replace("\\u0026", "&").replace("\\u003d", "=")
    if raw.startswith("//"):
        raw = f"{urlsplit(base_url).scheme or 'https'}:{raw}"
    candidate = urljoin(base_url, raw)
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    return candidate


def extract_m3u8(text: str, base_url: str) -> list[str]:
    text = html.unescape(text).replace("\\/", "/")
    text = re.sub(r"\\u0026", "&", text, flags=re.IGNORECASE)
    urls: list[str] = []
    seen: set[str] = set()
    for match in M3U8_RE.finditer(text):
        token = match.group(0).rstrip(".,;)")
        if not token or ".m3u8" not in token.lower():
            continue
        url = normalize_url(token, base_url)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def parse_variants(text: str, base_url: str) -> list[tuple[str, str]]:
    """Return (variant URL, label) for HLS master playlists."""
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    stream_inf = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXT-X-STREAM-INF:"):
            stream_inf = line
        elif stream_inf and line and not line.startswith("#"):
            url = normalize_url(line, base_url)
            if url and url not in seen:
                resolution = RES_RE.search(stream_inf)
                bandwidth = BW_RE.search(stream_inf)
                label = resolution.group(1) if resolution else "未知分辨率"
                if bandwidth:
                    label += f" / {int(bandwidth.group(1)) / 1_000_000:.2f} Mbps"
                results.append((url, label))
                seen.add(url)
            stream_inf = ""
    return results


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return (name[:100].rstrip(" .") or "video")


def find_ffmpeg() -> str | None:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if Path(path).is_file():
            return path
    except (ImportError, OSError):
        pass
    win = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "FFmpeg" / "ffmpeg.exe"
    return str(win) if win.is_file() else None


def make_opener(proxy: str = ""):
    if proxy.strip():
        return build_opener(ProxyHandler({"http": proxy.strip(), "https": proxy.strip()}))
    return build_opener()


@dataclass(frozen=True)
class Stream:
    url: str
    referer: str
    label: str
    via: str
    quality: str = "自动"


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.attributes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        for k, v in attrs:
            if not v:
                continue
            if k.lower() == "href" and tag.lower() == "a":
                self.links.append(v)
            if k.lower() in {"src", "href", "data-src", "data-url", "data-hls", "data-file", "content"}:
                self.attributes.append(v)


def is_web_url(url: str) -> bool:
    p = urlsplit(url)
    return p.scheme in ("http", "https") and bool(p.hostname)


def collect_site_links(html_text: str, base: str, host: str) -> list[str]:
    parser = LinkCollector()
    parser.feed(html_text)
    urls = []
    for raw in parser.links:
        url = normalize_url(raw, base)
        if not url or urlsplit(url).hostname != host:
            continue
        low = urlsplit(url).path.lower()
        if any(low.endswith(x) for x in (
            ".zip", ".rar", ".pdf", ".jpg", ".png", ".gif", ".webp", ".mp4", ".mp3", ".ts", ".m3u8", ".exe"
        )):
            continue
        if any(x in low for x in ("/logout", "/signout", "/delete", "/remove", "/unsubscribe")):
            continue
        urls.append(urldefrag(url).url)
    return list(dict.fromkeys(urls))


class MainApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("M3U8 Finder · FFmpeg 下载器")
        self.root.geometry("1100x740")
        self.root.minsize(820, 570)
        self.url_var = StringVar(value="")
        self.proxy_var = StringVar(value="")
        self.seconds_var = StringVar(value="60")
        self.folder_var = StringVar(value=str(Path.home() / "Downloads"))
        self.status_var = StringVar(value="就绪。输入网址后选择扫描模式。")
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.streams: dict[str, Stream] = {}
        self.url_to_id: dict[str, str] = {}
        self.scan_stop = threading.Event()
        self.download_stop = threading.Event()
        self.scan_thread: threading.Thread | None = None
        self.download_thread: threading.Thread | None = None
        self.ffmpeg_process: subprocess.Popen | None = None
        self._make_ui()
        self.root.after(100, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _make_ui(self):
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="目标 URL").grid(row=0, column=0, sticky="w")
        url_box = ttk.Entry(top, textvariable=self.url_var)
        url_box.grid(row=0, column=1, columnspan=6, sticky="ew", padx=(7, 0))
        ttk.Label(top, text="代理（可选）").grid(row=1, column=0, sticky="w", pady=(9, 0))
        ttk.Entry(top, textvariable=self.proxy_var, width=27).grid(row=1, column=1, sticky="ew", padx=(7, 8), pady=(9, 0))
        ttk.Label(top, text="浏览器监听秒数").grid(row=1, column=2, sticky="e", pady=(9, 0))
        ttk.Entry(top, textvariable=self.seconds_var, width=7).grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(9, 0))
        ttk.Button(top, text="网页扫描", command=lambda: self._begin_scan("site")).grid(row=2, column=0, pady=(11, 0), sticky="ew")
        ttk.Button(top, text="浏览器捕获（推荐）", command=lambda: self._begin_scan("browser")).grid(row=2, column=1, pady=(11, 0), sticky="w", padx=(7, 0))
        ttk.Button(top, text="停止扫描", command=self.scan_stop.set).grid(row=2, column=2, pady=(11, 0), sticky="e")
        ttk.Button(top, text="解析选中清晰度", command=self._probe_selected).grid(row=2, column=3, pady=(11, 0), padx=(8, 0))
        ttk.Button(top, text="复制选中 URL", command=self._copy_selected).grid(row=2, column=4, pady=(11, 0), padx=(8, 0))
        top.columnconfigure(1, weight=1)
        top.columnconfigure(5, weight=1)

        ttk.Label(self.root, text="发现的播放列表（Ctrl / Shift 多选，双击复制 URL）", padding=(12, 0)).pack(anchor="w")
        center = ttk.Frame(self.root, padding=(12, 5, 12, 7))
        center.pack(fill="both", expand=True)
        columns = ("n", "label", "quality", "via", "url")
        self.tree = ttk.Treeview(center, columns=columns, show="headings", selectmode="extended")
        titles = {"n": "#", "label": "资源", "quality": "清晰度", "via": "发现方式", "url": "M3U8 地址"}
        widths = {"n": 45, "label": 240, "quality": 160, "via": 110, "url": 540}
        for col in columns:
            self.tree.heading(col, text=titles[col])
            self.tree.column(col, width=widths[col], minwidth=35, stretch=col in ("label", "url"))
        yscroll = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(center, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda _: self._copy_selected())

        lower = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        lower.pack(fill="x")
        ttk.Label(lower, text="保存位置").grid(row=0, column=0)
        ttk.Entry(lower, textvariable=self.folder_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(lower, text="浏览…", command=self._choose_folder).grid(row=0, column=2)
        ttk.Button(lower, text="下载选中", command=self._download_selected).grid(row=0, column=3, padx=(13, 6))
        ttk.Button(lower, text="取消下载", command=self._stop_download).grid(row=0, column=4)
        lower.columnconfigure(1, weight=1)

        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 2)).pack(fill="x")
        ttk.Label(self.root, text="运行日志", padding=(12, 0)).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(self.root, height=8, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="x", padx=12, pady=(3, 12))
        ffmpeg = find_ffmpeg()
        self._log(f"FFmpeg: {ffmpeg or '未找到（请安装 imageio-ffmpeg 或将 ffmpeg 加入 PATH）'}")
        self._log("网页扫描：最多同站 15 页、深度 1；浏览器捕获：可在打开的页面中点击播放。")

    def _log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert(END, f"[{datetime.now():%H:%M:%S}] {msg}\n")
        self.log.see(END)
        self.log.configure(state="disabled")

    def _emit(self, kind: str, payload: object):
        self.events.put((kind, payload))

    def _poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "found":
                    self._add_stream(payload)
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "log":
                    self._log(str(payload))
                elif kind == "scan_done":
                    self.status_var.set(f"扫描结束。共发现 {len(self.streams)} 条 M3U8 资源。")
                    self._log(str(payload))
                elif kind == "download_done":
                    self.status_var.set(str(payload))
                    self._log(str(payload))
                elif kind == "error":
                    self._log("错误：" + str(payload))
                    self.status_var.set("出现错误，详见运行日志。")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _add_stream(self, stream: Stream):
        if stream.url in self.url_to_id:
            return
        row_id = str(len(self.streams) + 1)
        self.streams[row_id] = stream
        self.url_to_id[stream.url] = row_id
        self.tree.insert("", END, iid=row_id,
                         values=(row_id, stream.label, stream.quality, stream.via, stream.url))
        self.status_var.set(f"已找到 {len(self.streams)} 条播放列表")

    def _begin_scan(self, mode: str):
        if self.scan_thread and self.scan_thread.is_alive():
            messagebox.showinfo(APP_NAME, "已有扫描任务正在执行，请先停止。")
            return
        url = self.url_var.get().strip()
        if not is_web_url(url):
            messagebox.showerror(APP_NAME, "请输入 http:// 或 https:// 开头的网址。")
            return
        try:
            seconds = int(self.seconds_var.get())
            if not 5 <= seconds <= 3600:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, "监听秒数请输入 5～3600 的整数。")
            return
        self.scan_stop.clear()
        proxy = self.proxy_var.get().strip()
        target = self._scan_site if mode == "site" else self._scan_browser
        self._log(f"开始{'网页扫描' if mode == 'site' else '浏览器捕获'}：{url}")
        self.scan_thread = threading.Thread(target=target, args=(url, proxy, seconds), daemon=True)
        self.scan_thread.start()

    def _scan_site(self, url: str, proxy: str, _seconds: int):
        pages = deque([(url, 0)])
        visited: set[str] = set()
        found: set[str] = set()
        host = urlsplit(url).hostname
        opener = make_opener(proxy)
        count = 0
        while pages and len(visited) < MAX_CRAWL_PAGES and not self.scan_stop.is_set():
            current, depth = pages.popleft()
            if current in visited:
                continue
            visited.add(current)
            try:
                request = Request(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
                with opener.open(request, timeout=15) as response:
                    final_url = response.geturl()
                    if urlsplit(final_url).hostname != host:
                        continue
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "mpegurl" in content_type or ".m3u8" in urlsplit(final_url).path.lower():
                        self._emit("found", Stream(final_url, current, "直接播放列表", "页面请求"))
                        count += 1
                        continue
                    if content_type and not any(x in content_type for x in ("html", "text/plain")):
                        continue
                    html_text = response.read(MAX_HTML_BYTES).decode("utf-8", errors="replace")
                match = TITLE_RE.search(html_text)
                title = safe_filename(html.unescape(re.sub(r"<[^>]+>", "", match.group(1)))) if match else "网页资源"
                parser = LinkCollector()
                parser.feed(html_text)
                sources = extract_m3u8(html_text, final_url)
                for attr in parser.attributes:
                    sources.extend(extract_m3u8(attr, final_url))
                for media in dict.fromkeys(sources):
                    if media not in found:
                        found.add(media)
                        self._emit("found", Stream(media, final_url, title, "网页 HTML"))
                        count += 1
                self._emit("status", f"扫描网页 {len(visited)}/{MAX_CRAWL_PAGES}：已发现 {count} 条")
                if depth < 1:
                    for link in collect_site_links(html_text, final_url, host):
                        if link not in visited:
                            pages.append((link, depth + 1))
                if pages:
                    time.sleep(0.25)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                self._emit("log", f"页面访问失败：{current}（{exc}）")
            except Exception as exc:
                self._emit("log", f"解析页面失败：{current}（{exc}）")
        self._emit("scan_done", f"网页扫描完成，共访问 {len(visited)} 页；扫描队列中发现 {count} 个资源。")

    def _scan_browser(self, url: str, proxy: str, seconds: int):
        try:
            from playwright.sync_api import sync_playwright, Error as PlaywrightError
        except ImportError:
            self._emit("error", "缺少 Playwright。请执行 python -m pip install playwright 以及 python -m playwright install chromium")
            self._emit("scan_done", "浏览器捕获未启动。")
            return
        seen: set[str] = set()
        title = "浏览器资源"
        try:
            with sync_playwright() as p:
                launch_opts = {"headless": False}
                browser_executable = os.environ.get("M3U8_BROWSER_EXE", "").strip()
                if browser_executable:
                    launch_opts["executable_path"] = browser_executable
                if proxy:
                    launch_opts["proxy"] = {"server": proxy}
                browser = p.chromium.launch(**launch_opts)
                try:
                    context = browser.new_context(user_agent=USER_AGENT, ignore_https_errors=False)
                    def capture(url_to_check: str, referer: str, via: str):
                        if url_to_check in seen:
                            return
                        seen.add(url_to_check)
                        self._emit("found", Stream(url_to_check, referer or url, title, via))

                    def on_request(request):
                        req_url = request.url
                        if ".m3u8" in urlsplit(req_url).path.lower():
                            try:
                                referer = request.headers.get("referer", url)
                            except Exception:
                                referer = url
                            capture(req_url, referer, "网络请求")

                    def on_response(response):
                        ctype = response.headers.get("content-type", "").lower()
                        if "mpegurl" in ctype:
                            try:
                                referer = response.request.headers.get("referer", url)
                            except Exception:
                                referer = url
                            capture(response.url, referer, "HLS MIME")

                    context.on("request", on_request)
                    context.on("response", on_response)
                    page = context.new_page()
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    except PlaywrightError as exc:
                        self._emit("log", f"初次导航有异常，但将继续监听：{exc}")
                    self._emit("log", f"浏览器已打开。请手动点击播放/切换集数，最多监听 {seconds} 秒。")
                    deadline = time.monotonic() + seconds
                    last_scan = 0.0
                    while not self.scan_stop.is_set() and time.monotonic() < deadline:
                        active_pages = [p for p in context.pages if not p.is_closed()]
                        if not active_pages:
                            break
                        now = time.monotonic()
                        if now - last_scan >= 2:
                            for pg in active_pages:
                                try:
                                    title = safe_filename(pg.title())
                                    for frame in pg.frames:
                                        content = frame.content()
                                        base = frame.url if is_web_url(frame.url) else pg.url
                                        for found_url in extract_m3u8(content, base):
                                            capture(found_url, pg.url, "渲染 HTML")
                                except PlaywrightError:
                                    continue
                            last_scan = now
                        try:
                            active_pages[0].wait_for_timeout(250)
                        except PlaywrightError:
                            time.sleep(0.1)
                        self._emit("status", f"浏览器监听中：剩余 {max(0, int(deadline - time.monotonic()))} 秒，捕获 {len(seen)} 条")
                    self._emit("log", "浏览器监听结束。")
                finally:
                    browser.close()
        except Exception as exc:
            self._emit("error", f"浏览器扫描失败：{exc}")
        self._emit("scan_done", f"浏览器捕获完成：本轮发现 {len(seen)} 条资源。")

    def _selected(self) -> list[Stream]:
        return [self.streams[row_id] for row_id in self.tree.selection() if row_id in self.streams]

    def _copy_selected(self):
        chosen = self._selected()
        if not chosen:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(x.url for x in chosen))
        self._log(f"已复制 {len(chosen)} 个 URL 到剪贴板。")

    def _choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder_var.get())
        if chosen:
            self.folder_var.set(chosen)

    def _probe_selected(self):
        chosen = self._selected()
        if not chosen:
            messagebox.showinfo(APP_NAME, "请选择一条或多条 M3U8 资源。")
            return
        threading.Thread(target=self._probe_worker,
                         args=(chosen, self.proxy_var.get().strip()), daemon=True).start()

    def _probe_worker(self, chosen: list[Stream], proxy: str):
        opener = make_opener(proxy)
        for stream in chosen:
            try:
                request = Request(stream.url, headers={"User-Agent": USER_AGENT, "Referer": stream.referer})
                with opener.open(request, timeout=12) as response:
                    body = response.read(1_000_000).decode("utf-8-sig", errors="replace")
                    final_url = response.geturl()
                variants = parse_variants(body, final_url)
                if variants:
                    for variant_url, label in variants:
                        self._emit("found", Stream(variant_url, stream.referer,
                                                    stream.label + " / " + label, "多码率变体", label))
                    self._emit("log", f"已解析 {len(variants)} 个码率变体。")
                else:
                    self._emit("log", "选中资源不是可展开的 HLS 主列表，或没有多码率信息。")
            except Exception as exc:
                self._emit("log", f"播放列表解析失败：{exc}（可能需要登录 Cookies 或资源已过期）")

    def _download_selected(self):
        chosen = self._selected()
        if not chosen:
            messagebox.showinfo(APP_NAME, "请先在列表中选择要下载的资源。")
            return
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo(APP_NAME, "已有下载任务进行中。")
            return
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(APP_NAME, "未检测到 FFmpeg。运行 python -m pip install imageio-ffmpeg 后重试。")
            return
        folder = Path(self.folder_var.get().strip()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"无法创建下载目录：{exc}")
            return
        self.download_stop.clear()
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(chosen, folder, ffmpeg, self.proxy_var.get().strip()), daemon=True
        )
        self.download_thread.start()

    def _download_worker(self, chosen: list[Stream], folder: Path, ffmpeg: str, proxy: str):
        successes = 0
        for index, stream in enumerate(chosen, start=1):
            if self.download_stop.is_set():
                break
            tag = stream.quality if stream.quality != "自动" else ""
            base = safe_filename(f"{stream.label} {tag}")
            dest = folder / f"{base}.mp4"
            n = 2
            while dest.exists() or dest.with_name(dest.stem + ".part.mp4").exists():
                dest = folder / f"{base} ({n}).mp4"
                n += 1
            temp = dest.with_name(dest.stem + ".part.mp4")
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-nostats",
                "-progress", "pipe:1", "-y", "-user_agent", USER_AGENT,
            ]
            if stream.referer:
                cmd.extend(["-referer", stream.referer])
            cmd.extend(["-i", stream.url, "-c", "copy", "-movflags", "+faststart", str(temp)])
            env = os.environ.copy()
            if proxy:
                env["http_proxy"] = proxy
                env["https_proxy"] = proxy
                env["HTTP_PROXY"] = proxy
                env["HTTPS_PROXY"] = proxy
            self._emit("log", f"开始下载 {index}/{len(chosen)}：{dest.name}")
            errors: deque[str] = deque(maxlen=16)
            proc = None
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding="utf-8", errors="replace", env=env,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                self.ffmpeg_process = proc
                out_time, speed = "", ""
                assert proc.stdout is not None
                for line in proc.stdout:
                    line = line.strip()
                    if line.startswith("out_time="):
                        out_time = line.partition("=")[2]
                    elif line.startswith("speed="):
                        speed = line.partition("=")[2]
                        self._emit("status", f"下载 {index}/{len(chosen)} | 已处理时长 {out_time} | {speed}")
                    elif line and "=" not in line:
                        errors.append(line)
                    if self.download_stop.is_set():
                        proc.terminate()
                        break
                return_code = proc.wait(timeout=10)
                if self.download_stop.is_set():
                    self._emit("log", f"用户取消下载：{dest.name}")
                elif return_code == 0 and temp.is_file() and temp.stat().st_size > 0:
                    temp.replace(dest)
                    successes += 1
                    self._emit("log", f"完成：{dest}")
                else:
                    self._emit("log", f"下载失败：{dest.name}（退出码 {return_code}）" +
                               ("；" + " | ".join(errors) if errors else ""))
            except Exception as exc:
                self._emit("log", f"下载异常：{dest.name}（{exc}）")
                if proc and proc.poll() is None:
                    proc.kill()
                    proc.wait()
            finally:
                self.ffmpeg_process = None
                if temp.exists():
                    try:
                        temp.unlink()
                    except OSError:
                        pass
        self._emit("download_done", f"下载任务结束：成功 {successes}/{len(chosen)}；目录：{folder}")

    def _stop_download(self):
        self.download_stop.set()
        proc = self.ffmpeg_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def _close(self):
        self.scan_stop.set()
        self._stop_download()
        self.root.destroy()


def main():
    root = Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()