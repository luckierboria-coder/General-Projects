#!/usr/bin/env python3
"""Export full user-visible ChatGPT share histories to a local XML archive."""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener
import xml.etree.ElementTree as ET

SHARE_PATH = re.compile(r"^/share/([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})/?$")
CODEX_PATH = re.compile(r"^/s/(cx_[0-9a-fA-F]{32})/?$")
MAX_SNAPSHOT_BYTES = 60 * 1024 * 1024
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "br", "li", "pre", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}
SKIP = {"svg", "button", "script", "style"}


def validated_url(value):
    """Return a canonical public share URL and ID; never accept arbitrary hosts."""
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname not in {"chatgpt.com", "chat.openai.com"} or parsed.port not in (None, 443):
        raise ValueError("仅支持 https://chatgpt.com 的公开分享链接")
    if parsed.username or parsed.password:
        raise ValueError("分享链接不能包含用户名或密码")
    standard = SHARE_PATH.fullmatch(parsed.path)
    if standard:
        share_id = standard.group(1).lower()
        return f"https://chatgpt.com/share/{share_id}", share_id
    codex = CODEX_PATH.fullmatch(parsed.path)
    if codex:
        share_id = codex.group(1).lower()
        return f"https://chatgpt.com/s/{share_id}", share_id
    raise ValueError("链接格式不正确：支持 /share/<UUID> 或 /s/cx_<32位十六进制ID>")


def is_codex_share(url):
    return CODEX_PATH.fullmatch(urlparse(url).path) is not None


def fetch_codex_snapshot(url, proxy=None, timeout=90):
    """Read a public Codex snapshot using its JSON endpoint, not headless Chrome."""
    canonical, share_id = validated_url(url)
    if not is_codex_share(canonical):
        raise ValueError("不是 Codex 共享快照链接")
    api = f"https://chatgpt.com/backend-api/wham/shared_threads/{share_id}"
    proxies = {"https": proxy, "http": proxy} if proxy else None
    opener = build_opener(ProxyHandler(proxies))
    req = Request(api, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 ChatGPT-Share-Archiver/1.1",
        "Referer": canonical,
    })
    try:
        with opener.open(req, timeout=timeout) as response:
            if not response.url.startswith("https://chatgpt.com/"):
                raise RuntimeError("JSON 接口跳转到了非 ChatGPT 地址，已拒绝读取")
            raw = response.read(MAX_SNAPSHOT_BYTES + 1)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(f"Codex 快照接口 HTTP {exc.code}：快照无公开访问权限、已失效或被网络验证拦截") from exc
        if exc.code == 404:
            raise RuntimeError("Codex 快照 HTTP 404：分享已失效或链接 ID 不存在") from exc
        raise RuntimeError(f"Codex 快照接口 HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Codex 快照网络请求失败：{exc}") from exc
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise RuntimeError("Codex 快照过大（超过 60 MB），已停止读取以保护内存")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Codex 快照接口未返回有效 JSON；可能遇到登录页或反爬验证") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Codex 快照 JSON 根节点不是对象")
    return payload


def _snapshot_body(data):
    """Locate the v1 snapshot body without treating unrelated arrays as turns."""
    if not isinstance(data, dict):
        raise RuntimeError("Codex 快照 JSON 内容不是对象")
    version = data.get("version")
    if version not in (1, "1"):
        raise RuntimeError(f"不支持的 Codex 快照版本：{version!r}，目前仅支持 version=1")
    choices = [data]
    for key in ("snapshot", "thread", "data"):
        candidate = data.get(key)
        if isinstance(candidate, dict):
            choices.append(candidate)
            for nested in ("snapshot", "thread"):
                sub = candidate.get(nested)
                if isinstance(sub, dict):
                    choices.append(sub)
    for body in choices:
        if isinstance(body.get("turns"), list):
            turns = body["turns"]
            if not all(isinstance(turn, dict) and isinstance(turn.get("items"), list) for turn in turns):
                raise RuntimeError("Codex 快照 turns/items 结构不符合预期，拒绝导出不完整记录")
            return body, turns
    raise RuntimeError("Codex 快照缺少 turns/items；接口数据结构可能已更新")


def _snapshot_item_type(item):
    return str(item.get("type") or item.get("item_type") or item.get("kind") or "").replace("_", "").replace("-", "").lower()


def _message_text(item):
    """Extract only message-like content; full JSON is always kept separately."""
    def chunks(value, depth=0):
        if depth > 5 or value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            result = []
            for part in value:
                result.extend(chunks(part, depth + 1))
            return result
        if isinstance(value, dict):
            # Avoid recursively interpreting filenames, ids, or opaque resource objects as prose.
            for key in ("text", "message", "content", "parts", "summary", "value"):
                candidate = value.get(key)
                if candidate is not None and not isinstance(candidate, (int, float, bool)):
                    return chunks(candidate, depth + 1)
        return []
    for key in ("text", "message", "content", "summary", "parts"):
        if key in item:
            result = [x for x in chunks(item[key]) if x.strip()]
            if result:
                return "\n".join(result)
    return ""


def _xml_safe(text):
    return "".join(ch for ch in text if ch in "\t\n\r" or 0x20 <= ord(ch) <= 0xD7FF or 0xE000 <= ord(ch) <= 0xFFFD or 0x10000 <= ord(ch) <= 0x10FFFF)


def add_codex_conversation(root, supplied_url, data):
    """Export visible Codex items and preserve the untouched snapshot in XML."""
    url, share_id = validated_url(supplied_url)
    if not is_codex_share(url):
        raise ValueError("不是 Codex 共享链接")
    body, turns = _snapshot_body(data)
    if not turns:
        raise RuntimeError("Codex 快照没有任何轮次")
    title = next((value for value in (
        body.get("title"), body.get("name"), data.get("title"), data.get("name"),
        (data.get("thread") or {}).get("title") if isinstance(data.get("thread"), dict) else None,
    ) if isinstance(value, str) and value.strip()), "Codex 共享记录")
    item = ET.SubElement(root, "conversation", {
        "share_id": share_id, "source_url": url, "title": _xml_safe(title),
        "source": "codex_shared_snapshot", "snapshot_version": "1",
        "snapshot_turn_count": str(len(turns)),
    })
    count = 0
    total_items = 0
    missing = 0
    for turn_index, turn in enumerate(turns, 1):
        for item_index, entry in enumerate(turn["items"], 1):
            total_items += 1
            # Some exported item entries wrap the actual item in an `item` key.
            payload = entry.get("item") if isinstance(entry.get("item"), dict) else entry
            kind = _snapshot_item_type(payload)
            role = ""
            channel = ""
            if kind in ("usermessage", "user", "inputmessage"):
                role = "user"
            elif kind in ("agentmessage", "assistantmessage", "assistant", "outputmessage"):
                role = "assistant"
            elif kind in ("agentreasoning", "reasoning", "reasoningsummary", "agentprogress", "progress", "planupdate"):
                role, channel = "assistant", "commentary"
            else:
                # Tools, diffs and unknown item kinds remain in original JSON.
                continue
            text = _message_text(payload)
            if not text:
                # Image-only messages still remain visible, with a placeholder.
                if kind in ("usermessage", "user", "inputmessage"):
                    text = "〔该轮消息包含非文本内容；详情见 XML 中的 codex_snapshot_json〕"
                else:
                    continue
            count += 1
            attrs = {"index": str(count), "role": role, "content_type": "text",
                     "turn_index": str(turn_index), "item_index": str(item_index),
                     "item_type": str(payload.get("type") or kind)}
            if payload.get("id") is not None:
                attrs["id"] = str(payload["id"])
            if channel:
                attrs["channel"] = channel
            when = payload.get("created_at") or payload.get("createdAt")
            if isinstance(when, (int, float)):
                when = iso_time(when)
            if isinstance(when, str):
                attrs["created_at_utc"] = when
            message_node = ET.SubElement(item, "message", attrs)
            ET.SubElement(message_node, "text", {"format": "markdown"}).text = _xml_safe(text)
    # Store exact snapshot values in JSON, not an attempted lossy reconstruction.
    # User-visible XML text excludes invalid XML control characters.
    ET.SubElement(item, "codex_snapshot_json", {"format": "json", "version": "1"}).text = _xml_safe(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    item.set("message_count", str(count))
    item.set("snapshot_item_count", str(total_items))
    item.set("unembedded_attachment_count", str(missing))
    item.set("status", "snapshot_with_original_json")
    return count, missing, total_items, count


def find_browser(explicit):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"browser not found: {path}")
        return str(path)
    candidates = [shutil.which(x) for x in ("chrome", "chromium", "msedge", "microsoft-edge")]
    if sys.platform == "win32":
        candidates += [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError("Chrome/Chromium/Edge not found; pass --browser PATH")


def fetch_rendered(url, browser, proxy, timeout, virtual_time):
    with tempfile.TemporaryDirectory(prefix="chatgpt-share-") as profile:
        command = [
            browser, "--headless=new", "--disable-gpu", "--no-first-run",
            "--disable-extensions", "--disable-sync", "--disable-component-update",
            f"--user-data-dir={profile}", f"--virtual-time-budget={virtual_time}",
            "--dump-dom",
        ]
        if proxy:
            command.append(f"--proxy-server={proxy}")
        command.append(url)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, creationflags=flags, check=False,
        )
        if result.returncode or not result.stdout:
            error = result.stderr.decode("utf-8", errors="replace")[-600:].strip()
            raise RuntimeError(f"Chrome/Edge 未返回页面 HTML（退出码 {result.returncode}，错误输出：{error or '空'}）。请检查浏览器无头模式、代理和访问限制")
        return result.stdout.decode("utf-8", errors="strict")


class ShareParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.messages = []
        self.title = ""
        self.canonical = ""
        self.in_title = False
        self.current = None
        self.div_depth = 0
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href", "")
        if self.current is None:
            if tag == "div" and attrs.get("data-message-author-role") in {"user", "assistant"}:
                self.current = {
                    "role": attrs["data-message-author-role"],
                    "id": attrs.get("data-message-id", ""),
                    "model": attrs.get("data-message-model-slug", ""),
                    "parts": [], "links": [], "images": [],
                }
                self.div_depth = 1
            return
        if tag == "div":
            self.div_depth += 1
        if tag in SKIP:
            self.skip_depth += 1
        if self.skip_depth:
            return
        if tag in BLOCK:
            self.current["parts"].append("\n")
        if tag == "a" and attrs.get("href"):
            self.current["links"].append(attrs["href"])
        if tag == "img":
            self.current["images"].append({"src": attrs.get("src", ""), "alt": attrs.get("alt", "")})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if self.current is None:
            return
        if tag in SKIP and self.skip_depth:
            self.skip_depth -= 1
        if tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                text = "".join(self.current.pop("parts"))
                text = re.sub(r"[ \t]+\n", "\n", text)
                text = re.sub(r"\n{3,}", "\n\n", text).strip()
                self.current["text"] = text
                self.messages.append(self.current)
                self.current = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.current is not None and not self.skip_depth:
            self.current["parts"].append(data)


def add_dom_conversation(root, url, share_id, html):
    parser = ShareParser()
    parser.feed(html)
    if not parser.messages:
        raise RuntimeError("share page rendered no user/assistant messages")
    if parser.canonical:
        canonical, canonical_id = validated_url(parser.canonical)
        if canonical_id != share_id:
            raise RuntimeError(f"canonical share ID mismatch: {canonical}")
    item = ET.SubElement(root, "conversation", {
        "share_id": share_id, "source_url": url,
        "title": parser.title.strip(), "message_count": str(len(parser.messages)),
    })
    unembedded = 0
    for index, message in enumerate(parser.messages, 1):
        node = ET.SubElement(item, "message", {
            "index": str(index), "role": message["role"], "id": message["id"],
        })
        if message["model"]:
            node.set("model", message["model"])
        ET.SubElement(node, "text").text = message["text"]
        if message["links"]:
            refs = ET.SubElement(node, "links")
            for href in dict.fromkeys(message["links"]):
                ET.SubElement(refs, "link", {"href": href})
        markers = re.findall(r"Uploaded an? (?:file|image)", message["text"])
        if markers or message["images"]:
            attachments = ET.SubElement(node, "attachments")
            for marker in markers:
                ET.SubElement(attachments, "attachment", {"type": marker.split()[-1], "embedded": "false"})
                unembedded += 1
            for image in message["images"]:
                ET.SubElement(attachments, "image", {"src": image["src"], "alt": image["alt"], "embedded": "false"})
                unembedded += 1
    item.set("unembedded_attachment_count", str(unembedded))
    item.set("status", "partial_rendered_dom")
    return len(parser.messages), unembedded


STREAM_CHUNK = re.compile(
    r'window\.__reactRouterContext\.streamController\.enqueue\(("(?:\\.|[^"\\])*")\)',
    re.DOTALL,
)


class RefView:
    """Read React Router's indexed JSON payload without expanding the whole graph."""

    def __init__(self, values):
        self.values = values

    def scalar(self, ref):
        if not isinstance(ref, int) or ref < 0:
            return None
        return self.values[ref]

    def obj(self, ref):
        raw = self.scalar(ref)
        if not isinstance(raw, dict):
            return {}
        return {self.values[int(k[1:])]: value for k, value in raw.items() if k.startswith("_")}

    def expand(self, ref, ancestors=None):
        if not isinstance(ref, int) or ref < 0:
            return None
        if ancestors is None:
            ancestors = set()
        if ref in ancestors:
            return {"circular_ref": ref}
        raw = self.values[ref]
        if isinstance(raw, (str, float, bool)) or raw is None:
            return raw
        if isinstance(raw, int):
            return raw
        ancestors = ancestors | {ref}
        if isinstance(raw, list):
            return [self.expand(item, ancestors) for item in raw]
        if isinstance(raw, dict):
            return {key: self.expand(value, ancestors) for key, value in self.obj(ref).items()}
        return str(raw)


def embedded_share_data(html):
    for match in STREAM_CHUNK.finditer(html):
        try:
            values = json.loads(json.loads(match.group(1)))
            if not isinstance(values, list):
                continue
            view = RefView(values)
            loader = view.obj(view.obj(0)["loaderData"])
            route_ref = next(value for key, value in loader.items() if key.startswith("routes/share"))
            route = view.obj(route_ref)
            server = view.obj(route["serverResponse"])
            data = view.obj(server["data"])
            nodes = view.scalar(data["linear_conversation"])
            if isinstance(nodes, list):
                return view, route, data, nodes
        except (KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError):
            continue
    raise RuntimeError("complete conversation payload absent; page may be partial or the site format changed")


def iso_time(value):
    if not isinstance(value, (int, float)) or not value:
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def add_payload_conversation(root, supplied_url, html):
    view, route, data, nodes = embedded_share_data(html)
    share_id = view.scalar(route["sharedConversationId"])
    url, expected_id = validated_url(supplied_url) if supplied_url else (
        f"https://chatgpt.com/share/{share_id}", share_id
    )
    if share_id != expected_id:
        raise RuntimeError(f"share ID mismatch: page={share_id} requested={expected_id}")
    visible_parser = ShareParser()
    visible_parser.feed(html)
    item = ET.SubElement(root, "conversation", {
        "share_id": share_id, "source_url": url,
        "title": str(view.scalar(data["title"])),
        "payload_node_count": str(len(nodes)),
        "rendered_message_count": str(len(visible_parser.messages)),
        "source": "embedded_share_payload",
    })
    unembedded = 0
    for node_ref in nodes:
        node = view.obj(node_ref)
        message_ref = node.get("message", -1)
        if message_ref < 0:
            continue
        message = view.obj(message_ref)
        author = view.obj(message.get("author", -1))
        role = view.scalar(author.get("role", -1))
        channel = view.scalar(message.get("channel", -1))
        recipient = view.scalar(message.get("recipient", -1))
        content = view.obj(message.get("content", -1))
        content_type = view.scalar(content.get("content_type", -1))
        metadata = view.obj(message.get("metadata", -1))
        hidden = view.scalar(metadata.get("is_visually_hidden_from_conversation", -1))
        redacted = view.scalar(metadata.get("is_redacted", -1))
        if hidden or redacted or recipient not in (None, "all"):
            continue
        if role == "user":
            pass
        elif role == "assistant" and channel in (None, "final", "commentary"):
            pass
        else:
            continue
        if content_type not in ("text", "multimodal_text"):
            continue
        attrs = {
            "index": str(len(item.findall("message")) + 1),
            "role": role,
            "id": str(view.scalar(message.get("id", -1)) or ""),
            "content_type": content_type,
        }
        if channel:
            attrs["channel"] = channel
        created = iso_time(view.scalar(message.get("create_time", -1)))
        if created:
            attrs["created_at_utc"] = created
        out = ET.SubElement(item, "message", attrs)
        parts_ref = content.get("parts", -1)
        parts = view.scalar(parts_ref)
        text_parts = []
        if isinstance(parts, list):
            for part_index, part_ref in enumerate(parts, 1):
                part = view.expand(part_ref)
                if isinstance(part, str):
                    text_parts.append(part)
                elif part is not None:
                    ET.SubElement(out, "nontext_part", {
                        "index": str(part_index), "embedded": "false"
                    }).text = json.dumps(part, ensure_ascii=False, separators=(",", ":"))
                    unembedded += 1
        ET.SubElement(out, "text", {"format": "markdown"}).text = "\n".join(text_parts)
        attachments_ref = metadata.get("attachments", -1)
        attachments = view.scalar(attachments_ref)
        if isinstance(attachments, list) and attachments:
            group = ET.SubElement(out, "attachments")
            for attachment_ref in attachments:
                detail = view.obj(attachment_ref)
                fields = {
                    key: str(view.scalar(detail[key]))
                    for key in ("id", "name", "mime_type", "size")
                    if key in detail and view.scalar(detail[key]) is not None
                }
                fields["embedded"] = "false"
                ET.SubElement(group, "attachment", fields)
                unembedded += 1
    count = len(item.findall("message"))
    if not count:
        root.remove(item)
        raise RuntimeError("payload contained no user-visible messages")
    item.set("message_count", str(count))
    item.set("unembedded_attachment_count", str(unembedded))
    item.set("status", "payload_text_with_unembedded_attachments" if unembedded else "payload_text")
    return count, unembedded, len(nodes), len(visible_parser.messages)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", nargs="*", help="Public ChatGPT share URLs")
    ap.add_argument("--html-file", action="append", type=Path, default=[], help="Saved share-page HTML for offline extraction; repeat for multiple pages")
    ap.add_argument("--json-file", action="append", type=Path, default=[], help="Saved Codex snapshot JSON; must contain source_url or specify --source-url")
    ap.add_argument("--source-url", help="Public Codex /s/cx_... URL matching --json-file")
    ap.add_argument("--output", type=Path, help="Destination XML file; defaults to a timestamped local chat_archives file")
    ap.add_argument("--allow-dom-fallback", action="store_true", help="Export visibly rendered messages when the full payload is absent; marks the result partial")
    ap.add_argument("--browser", help="Chrome/Chromium/Edge executable")
    ap.add_argument("--proxy", help="Optional browser proxy URL")
    ap.add_argument("--timeout", type=int, default=90, help="Seconds per page")
    ap.add_argument("--virtual-time", type=int, default=12000, help="Browser page settling time in ms")
    args = ap.parse_args()
    if not args.urls and not args.html_file and not args.json_file:
        ap.error("provide at least one share URL or --html-file")
    if args.output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        local_dir = Path(__file__).resolve().parents[1] / "chat_archives"
        args.output = local_dir / f"chatgpt-share-{stamp}.xml"
    if args.output.exists():
        ap.error(f"output exists; choose a new path to preserve the earlier archive: {args.output}")
    browser = find_browser(args.browser) if any(not is_codex_share(validated_url(url)[0]) for url in args.urls if url.startswith("https://")) else None
    root = ET.Element("chatgpt_share_archive", {
        "schema_version": "1", "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "public_share_user_visible_messages",
    })
    failures = 0
    sources = [(url, None, None) for url in args.urls] + [(None, file, None) for file in args.html_file] + [(None, None, file) for file in args.json_file]
    for supplied, file, json_file in sources:
        try:
            url = validated_url(supplied)[0] if supplied else None
            if json_file or (url and is_codex_share(url)):
                payload = json.loads(json_file.read_text(encoding="utf-8-sig")) if json_file else fetch_codex_snapshot(url, args.proxy, args.timeout)
                codex_url = url or args.source_url or payload.get("source_url") or payload.get("url")
                if not codex_url:
                    raise ValueError("--json-file 需要 --source-url 参数指定原始 /s/cx_... 链接")
                count, missing, nodes, rendered = add_codex_conversation(root, codex_url, payload)
                print(f"OK {codex_url}: {count} visible messages, {nodes} snapshot items; original JSON preserved", file=sys.stderr)
                continue
            html = fetch_rendered(url, browser, args.proxy, args.timeout, args.virtual_time) if url else file.read_text(encoding="utf-8")
            try:
                count, missing, nodes, rendered = add_payload_conversation(root, url, html)
                print(f"OK {url or file}: {count} messages from {nodes} payload nodes (DOM displayed {rendered}); {missing} unembedded attachments", file=sys.stderr)
            except RuntimeError:
                if not args.allow_dom_fallback:
                    raise
                parser = ShareParser()
                parser.feed(html)
                if not parser.canonical:
                    raise RuntimeError("no share URL in saved HTML for DOM fallback")
                url, share_id = validated_url(parser.canonical)
                count, missing = add_dom_conversation(root, url, share_id, html)
                print(f"PARTIAL {url}: {count} rendered messages; {missing} unembedded attachment markers", file=sys.stderr)
        except Exception as exc:
            failures += 1
            source = supplied or str(file or json_file)
            ET.SubElement(root, "failure", {"source_url": source, "reason": str(exc)})
            print(f"FAIL {source}: {exc}", file=sys.stderr)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {args.output} ({len(root.findall('conversation'))} conversations; {failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())