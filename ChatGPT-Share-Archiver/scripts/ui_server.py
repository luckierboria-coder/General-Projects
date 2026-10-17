#!/usr/bin/env python3
"""Local browser UI for reading public ChatGPT shares and exporting XML."""

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import sys
import threading
from urllib.parse import parse_qs, quote, urlparse
import xml.etree.ElementTree as ET

from export_shares import (add_payload_conversation, add_codex_conversation, fetch_codex_snapshot,
                           fetch_rendered, find_browser, is_codex_share, validated_url)


def xml_archive():
    return ET.Element("chatgpt_share_archive", {
        "schema_version": "1",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "public_share_user_visible_messages",
    })


def filename_part(value, limit):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value or ''))
    value = re.sub(r'\s+', ' ', value).strip(' .')[:limit].rstrip(' .')
    if not value:
        raise ValueError('项目名或聊天记录名不能为空。')
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value):
        value = '_' + value
    return value


class AppServer(ThreadingHTTPServer):
    def __init__(self, address, archive_dir, browser, proxy):
        super().__init__(address, AppHandler)
        self.archive_dir = archive_dir
        self.browser = browser
        self.proxy = proxy
        self.csrf = secrets.token_urlsafe(32)
        self.sessions = {}
        self.lock = threading.Lock()
        asset_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        self.page = (asset_root / "assets" / "chat-ui.html").read_text(encoding="utf-8")


class AppHandler(BaseHTTPRequestHandler):
    server: AppServer

    def log_message(self, format, *args):
        return

    def send_bytes(self, status, body, content_type, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = self.server.page.replace("__LOCAL_CSRF_TOKEN__", self.server.csrf).encode("utf-8")
            self.send_bytes(200, body, "text/html; charset=utf-8")
        elif parsed.path == "/health":
            app_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
            self.send_json(200, {"app": "chatgpt-share-ui", "app_root": str(app_root), "ok": True})
        elif parsed.path == "/api/download":
            key = parse_qs(parsed.query).get("id", [""])[0]
            with self.server.lock:
                record = self.server.sessions.get(key)
            if not record or not record.get("file"):
                self.send_json(404, {"error": "没有可下载的 XML。"})
                return
            file = record["file"]
            self.send_bytes(200, file.read_bytes(), "application/xml; charset=utf-8", {
                "Content-Disposition": f"attachment; filename=\"chatgpt-chat.xml\"; filename*=UTF-8''{quote(file.name)}"
            })
        else:
            self.send_json(404, {"error": "页面不存在。"})

    def do_POST(self):
        if self.headers.get("X-Local-Token") != self.server.csrf:
            self.send_json(403, {"error": "页面会话已失效，请刷新后重试。"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 1 or size > 8192:
                raise ValueError("请求长度无效")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("请求格式无效")
            if self.path == "/api/load":
                self.load_chat(data)
            elif self.path == "/api/export":
                self.export_chat(data)
            else:
                self.send_json(404, {"error": "接口不存在。"})
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            self.send_json(502, {"error": f"读取失败：{exc}"})

    def load_chat(self, data):
        url, _ = validated_url(str(data.get("url", "")).strip())
        root = xml_archive()
        if is_codex_share(url):
            payload = fetch_codex_snapshot(url, self.server.proxy, 100)
            count, missing, nodes, rendered = add_codex_conversation(root, url, payload)
        else:
            browser = self.server.browser or find_browser(None)
            html = fetch_rendered(url, browser, self.server.proxy, 100, 12000)
            count, missing, nodes, rendered = add_payload_conversation(root, url, html)
        conv = root.find("conversation")
        key = secrets.token_urlsafe(24)
        messages = []
        for message in conv.findall("message"):
            messages.append({
                "index": int(message.get("index")),
                "role": message.get("role"),
                "channel": message.get("channel"),
                "created_at_utc": message.get("created_at_utc"),
                "text": message.findtext("text") or "",
                "attachments": [attachment.get("name") or attachment.get("mime_type") or "文件" for attachment in message.findall("./attachments/attachment")],
                "nontext_count": len(message.findall("nontext_part")),
            })
        with self.server.lock:
            self.server.sessions[key] = {"root": root, "file": None, "exports": {}}
            if len(self.server.sessions) > 10:
                oldest = next(iter(self.server.sessions))
                if oldest != key:
                    self.server.sessions.pop(oldest, None)
        self.send_json(200, {
            "id": key, "title": conv.get("title"), "source_url": url,
            "message_count": count, "unembedded_attachment_count": missing,
            "payload_node_count": nodes, "rendered_message_count": rendered,
            "source_type": "codex" if is_codex_share(url) else "chatgpt",
            "messages": messages,
        })

    def export_chat(self, data):
        key = str(data.get("id", ""))
        project = filename_part(data.get("project"), 60)
        with self.server.lock:
            record = self.server.sessions.get(key)
        if not record:
            self.send_json(404, {"error": "聊天已从内存中清除，请重新加载分享链接。"})
            return
        if project not in record["exports"]:
            root = record["root"]
            conversation = root.find("conversation")
            title = filename_part(conversation.get("title") or "未命名聊天记录", 100)
            conversation.set("project_name", str(data.get("project", "")).strip())
            stem = f"{project}-{title}"
            self.server.archive_dir.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ")
            for number in range(1, 10000):
                suffix = "" if number == 1 else f"-{number}"
                file = self.server.archive_dir / f"{stem}{suffix}.xml"
                try:
                    with file.open("xb") as stream:
                        tree.write(stream, encoding="utf-8", xml_declaration=True)
                    break
                except FileExistsError:
                    continue
            else:
                raise RuntimeError("同名 XML 文件过多，请更换项目名称。")
            with self.server.lock:
                record["file"] = file
                record["exports"][project] = file
        else:
            with self.server.lock:
                record["file"] = record["exports"][project]
        self.send_json(200, {"saved_path": str(record["file"]), "download_url": f"/api/download?id={key}"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--browser", default=None)
    app_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    parser.add_argument("--archive-dir", type=Path, default=app_root / "chat_archives")
    args = parser.parse_args()
    server = AppServer((args.host, args.port), args.archive_dir.resolve(), args.browser, args.proxy)
    print(f"ChatGPT share UI: http://{args.host}:{args.port}/", flush=True)
    server.serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    main()