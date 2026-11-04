"""Offline HTML export and JSON backup for publicly shared ChatGPT chats."""
from datetime import datetime, timezone
from html import escape
import json
import re
from urllib.parse import urlparse

import bleach
import markdown
from latex2mathml.converter import convert as mathml_convert

TAGS = ["p","br","hr","h1","h2","h3","h4","h5","h6","strong","b","em","i","del","s",
        "blockquote","pre","code","ol","ul","li","table","thead","tbody","tr","th","td",
        "a","img","sup","sub"]
ATTRS = {"a":["href","title"],"img":["src","alt","title"],"code":["class"],"td":["align"],"th":["align"]}
MATH = re.compile(r"(?<!\\)\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)|(?<!\\)\$([^\s$\n](?:[^$\n]*?[^\s$\n])?)\$", re.DOTALL)


def _math_markup(raw, block):
    try:
        xml = mathml_convert(raw, display="block" if block else "inline")
        tag = "div" if block else "span"
        return "<"+tag+' class="math-formula">'+xml+"</"+tag+">"
    except Exception:
        return "<code>"+escape(raw)+"</code>"


def _protect_math(text):
    placeholders, output, fenced = {}, [], None
    for line in (text or "").splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}([\x60~]{3,})", line)
        if marker:
            char = marker.group(1)[0]
            if fenced is None: fenced = char
            elif fenced == char: fenced = None
        if fenced or marker:
            output.append(line)
            continue
        def substitute(match):
            raw = next(x for x in match.groups() if x is not None)
            block = match.group(1) is not None or match.group(2) is not None
            token = "ARCHIVEMATHPLACEHOLDER"+str(len(placeholders)).zfill(6)+"END"
            placeholders[token] = _math_markup(raw, block)
            return token
        output.append(MATH.sub(substitute,line))
    return "".join(output),placeholders


def render_markdown(source):
    raw, math = _protect_math(source or "")
    parsed = markdown.markdown(escape(raw, quote=False),
        extensions=["fenced_code","tables","sane_lists","nl2br"],output_format="html5")
    clean = bleach.clean(parsed, tags=TAGS, attributes=ATTRS,
        protocols=["http","https","mailto"],strip=True)
    clean = re.sub(r"<a (?=[^>]*href=)",'<a rel="noopener noreferrer" target="_blank" ',clean)
    for token,markup in math.items(): clean = clean.replace(token,markup)
    return clean or "<p>〔无文字内容〕</p>"


def safe_url(value):
    try:
        parsed = urlparse((value or "").strip())
        if parsed.scheme in ("http","https") and parsed.hostname and not parsed.username and not parsed.password:
            return value.strip()
    except ValueError:
        pass
    return None


def element_record(node):
    value = {"tag":node.tag,"attributes":dict(node.attrib)}
    if node.text is not None: value["text"] = node.text
    if list(node): value["children"] = [element_record(x) for x in node]
    return value


def backup_json(root, raw_source=None):
    output = {"format":"chatgpt-share-archiver","version":2,
              "exported_at_utc":datetime.now(timezone.utc).isoformat(),
              "archive":element_record(root)}
    if raw_source is not None: output["source_data"] = raw_source
    return json.dumps(output,ensure_ascii=False,indent=2)


STYLE = """
:root{color-scheme:light;--fg:#232724;--muted:#65726a;--line:#e3e9e5;--bg:#fff;--bubble:#f4f6f4;--link:#176d53}
*{box-sizing:border-box}body{margin:0;color:var(--fg);background:var(--bg);font:15px/1.75 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
main{max-width:920px;margin:auto;padding:35px 22px 95px}
header{border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:36px}
.title{font-size:clamp(23px,3vw,32px);line-height:1.3;margin:0 0 12px;overflow-wrap:anywhere}
.meta{font-size:13px;color:var(--muted);overflow-wrap:anywhere}.meta p{margin:4px 0}a{color:var(--link)}
.message{display:flex;align-items:flex-start;gap:13px;margin:0 0 29px;overflow-wrap:anywhere;break-inside:avoid}
.user{flex-direction:row-reverse}.avatar{flex:none;width:33px;height:33px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700;background:#e4f0e9;color:#276e4e}
.user .avatar{background:#e5eaf2;color:#465a80}.message-content{min-width:0;width:100%;max-width:calc(100% - 46px)}
.user .message-content{width:auto;min-width:min(240px,75%);max-width:85%}
.role{font-size:12px;color:var(--muted);margin:0 0 8px}.user .role{text-align:right}
.body{font-size:15px;line-height:1.8;min-width:0}.user .body{padding:13px 17px;background:var(--bubble);border-radius:18px}
.body>:first-child{margin-top:0}.body>:last-child{margin-bottom:0}.body p{margin:.65em 0}
.body h1,.body h2,.body h3,.body h4{line-height:1.3;margin:1.35em 0 .5em}
.body h1{font-size:1.55em}.body h2{font-size:1.35em}.body h3{font-size:1.17em}
.body ol,.body ul{padding-left:1.6em}.body blockquote{margin:1em 0;padding:2px 14px;background:#f7f9f7;border-left:3px solid #a4b5a9}
.body pre,.raw pre{background:#f6f8f6;border:1px solid var(--line);border-radius:10px;padding:13px 15px;max-width:100%;overflow-x:auto;white-space:pre;tab-size:4;font:13px/1.6 Consolas,monospace}
.body code:not(pre code){background:#f0f3f0;border-radius:4px;padding:2px 5px;font:.93em Consolas,monospace}
.body pre code{font:inherit;background:none;padding:0}.body img{max-width:100%;height:auto;border-radius:8px}
.body table{max-width:100%;display:block;overflow-x:auto;border-collapse:collapse;margin:1em 0;font-size:14px}
.body th,.body td{border:1px solid var(--line);padding:8px 12px;text-align:left}.body th{background:#f5f7f5}
.math-formula{overflow-x:auto}.extra{border:1px solid var(--line);border-radius:8px;padding:8px 13px;background:#fbfcfb;margin-top:10px;color:var(--muted);font-size:13px}
.extra ul{padding-left:20px;margin:5px 0}.raw{border-top:1px dashed var(--line);padding-top:6px;margin-top:10px;font-size:13px;color:var(--muted)}
.raw summary{cursor:pointer}.raw pre{white-space:pre-wrap;overflow-wrap:anywhere}
.warning{background:#fff8e9;border:1px solid #e9dabc;border-radius:9px;padding:12px 15px;color:#81633c}
footer{border-top:1px solid var(--line);padding-top:14px;font-size:12px;color:var(--muted)}
@media print{main{max-width:none;padding:0}.raw{display:none}.message{break-inside:avoid}}
@media(prefers-color-scheme:dark){:root{color-scheme:dark;--fg:#e9efe9;--muted:#a6b8ab;--line:#36423a;--bg:#161c18;--bubble:#29362d;--link:#91d5b5}
.avatar{background:#2d4638}.user .avatar{background:#36465a;color:#e3eaff}
.body pre,.raw pre,.body code:not(pre code),.body th,.body blockquote,.extra{background:#222c25}.warning{background:#39301f;border-color:#605132;color:#e6c993}}
"""


def build_html(root):
    convs = root.findall("conversation")
    if not convs: raise ValueError("没有可导出的聊天记录")
    title = convs[0].get("title") or "未命名聊天记录"
    p = ['<!doctype html>','<html lang="zh-CN"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; img-src https: data:; object-src &#39;none&#39;; base-uri &#39;none&#39;">',
         "<title>"+escape(title)+" — ChatGPT 归档</title>","<style>"+STYLE+"</style></head><body><main>"]
    for conv in convs:
        items = conv.findall("message")
        p.append('<header><h1 class="title">'+escape(conv.get("title") or "未命名聊天记录")+'</h1><div class="meta">')
        p.append('<p>项目：'+escape(conv.get("project_name") or "未分类")+
                 " · 消息数："+str(len(items))+" · 来源："+escape(conv.get("source") or "public_share")+"</p>")
        url = safe_url(conv.get("source_url"))
        if url: p.append('<p>分享地址：<a rel="noreferrer noopener" href="'+escape(url,quote=True)+'">'+escape(url)+"</a></p>")
        p.append("<p>保存时间（UTC）："+escape(root.get("retrieved_at_utc") or "")+"</p></div></header>")
        missing = conv.get("unembedded_attachment_count")
        if missing and missing!="0":
            p.append('<p class="warning">有 '+escape(missing)+" 项资源未包含可离线恢复的原文件；保留原始引用和相关元数据。</p>")
        for item in items:
            user = item.get("role")=="user"
            source = item.findtext("text") or ""
            p.append('<article class="message '+("user" if user else "assistant")+'"><div class="avatar">'+("你" if user else "AI")+'</div><div class="message-content">')
            extra = (" · "+escape(item.get("channel"))) if item.get("channel") else ""
            when = (" · "+escape(item.get("created_at_utc"))) if item.get("created_at_utc") else ""
            p.append('<div class="role">'+("你" if user else "ChatGPT")+" · #"+escape(item.get("index") or "")+extra+when+"</div>")
            p.append('<div class="body">'+render_markdown(source)+"</div>")
            attachments = item.findall("./attachments/attachment")
            images = item.findall("./attachments/image")
            nontext = item.findall("nontext_part")
            if attachments or images or nontext:
                p.append('<section class="extra"><strong>附件与非文本数据</strong><ul>')
                for x in attachments:
                    label = escape(x.get("name") or x.get("mime_type") or x.get("id") or "附件")
                    link = safe_url(x.get("url"))
                    if link: label = '<a href="'+escape(link,quote=True)+'" rel="noopener noreferrer">'+label+"</a>"
                    p.append("<li>附件："+label+"（原文件未必包含在公开分享中）</li>")
                for x in images:
                    label = escape(x.get("alt") or "图片")
                    link = safe_url(x.get("src"))
                    if link: label = '<a href="'+escape(link,quote=True)+'" rel="noopener noreferrer">'+label+"</a>"
                    p.append("<li>图片："+label+"（可能需要联网）</li>")
                for x in nontext:
                    p.append('<li>非文本部分 #'+escape(x.get("index") or "")+
                             '：<details class="raw"><summary>查看原始内容</summary><pre>'+escape(x.text or "")+"</pre></details></li>")
                p.append("</ul></section>")
            p.append('<details class="raw"><summary>查看原始 Markdown</summary><pre>'+escape(source)+"</pre></details></div></article>")
    for x in root.findall("failure"):
        p.append('<p class="warning">读取失败：'+escape(x.get("source_url") or "")+"："+escape(x.get("reason") or "")+"</p>")
    p.append("<footer>ChatGPT Share Archiver · 独立 HTML 文件无需联网加载脚本。公开分享中未提供的原附件无法自动补全；详见同名 JSON 备份。</footer>")
    p.append("</main></body></html>")
    return "\n".join(p)
