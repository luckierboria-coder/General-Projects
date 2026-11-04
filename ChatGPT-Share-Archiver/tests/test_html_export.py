"""Offline HTML export regression tests: formatting, lossless metadata, GUI save."""
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from html_export import build_html, backup_json, render_markdown
from ui_server import AppHandler


def fixture():
    root = ET.Element("chatgpt_share_archive",{
        "retrieved_at_utc":"2026-11-04T12:00:00+00:00","schema_version":"1"})
    conv = ET.SubElement(root,"conversation",{
        "title":"测试 <script>","source_url":"https://chatgpt.com/share/01234567-89ab-cdef-0123-456789abcdef",
        "source":"embedded_share_payload","message_count":"2","unembedded_attachment_count":"1"})
    user = ET.SubElement(conv,"message",{"index":"1","role":"user"})
    ET.SubElement(user,"text",{"format":"markdown"}).text = "这是我的测试：**你好**\n\n| A | B |\n|---|---|\n| 1 | 2 |"
    assistant = ET.SubElement(conv,"message",{"index":"2","role":"assistant","channel":"final"})
    code_fence = chr(96)*3
    ET.SubElement(assistant,"text",{"format":"markdown"}).text = (
        "# 结果\n\n- 第一项\n- 第二项\n\n"+
        code_fence+"python\nprint('<script>')\n"+code_fence+
        "\n\n公式：\\(x^2+y^2\\)\n\n<script>alert('x')</script>\n\n[link](javascript:alert(1))")
    attachments = ET.SubElement(assistant,"attachments")
    ET.SubElement(attachments,"attachment",{"name":"example.txt","mime_type":"text/plain"})
    ET.SubElement(assistant,"nontext_part",{"index":"1","embedded":"false"}).text = '{"asset_pointer":"img_missing"}'
    return root


class TestHtmlExport(unittest.TestCase):
    def test_html_renders_text_table_code_math_without_scripts(self):
        page = build_html(fixture())
        self.assertIn("<!doctype html>",page)
        self.assertIn("<strong>你好</strong>",page)
        self.assertIn("<table>",page)
        self.assertIn("language-python",page)
        self.assertIn("print(",page)
        self.assertIn("<math",page)
        self.assertIn("example.txt",page)
        self.assertIn("img_missing",page)
        self.assertIn("查看原始 Markdown",page)
        self.assertNotIn("<script>alert",page)
        self.assertNotIn('href="javascript:',page)
        self.assertIn("&lt;script&gt;",page)

    def test_json_preserves_raw_source_and_nontext(self):
        root = fixture()
        raw = {"kind":"chatgpt_react_router_indexed",
               "values":[{"chunk":"\\u4e2d\\u6587", "opaque":{"id":"x","items":[1,2,3]}}]}
        saved = json.loads(backup_json(root,raw))
        self.assertEqual(saved["source_data"],raw)
        self.assertEqual(saved["archive"]["children"][0]["attributes"]["title"],"测试 <script>")
        self.assertIn("img_missing",json.dumps(saved))

    def test_server_saves_html_json_without_overwriting(self):
        root = fixture()
        with tempfile.TemporaryDirectory() as folder:
            holder = SimpleNamespace(archive_dir=Path(folder),lock=threading.Lock(),
                      sessions={"k":{"root":root,"raw_source":{"kind":"fixture","raw":[1,2]},
                                     "file":None,"backup":None,"exports":{}}})
            handler = object.__new__(AppHandler)
            handler.server = holder
            responses = []
            handler.send_json = lambda status,value:responses.append((status,value))
            handler.export_chat({"id":"k","project":"工程/测试"})
            self.assertEqual(responses[-1][0],200)
            p = Path(responses[-1][1]["saved_path"])
            backup = Path(responses[-1][1]["backup_path"])
            self.assertEqual(p.suffix,".html")
            self.assertTrue(p.exists())
            self.assertTrue(backup.exists())
            self.assertEqual(json.loads(backup.read_text("utf-8"))["source_data"]["raw"],[1,2])
            self.assertIn("<strong>你好</strong>",p.read_text("utf-8"))
            handler.export_chat({"id":"k","project":"工程/测试"})
            self.assertEqual(responses[-1][1]["saved_path"],str(p))
            self.assertEqual(len(list(Path(folder).glob("*.html"))),1)

    def test_inline_preview_sanitizes_links(self):
        safe = render_markdown("**bold** [bad](javascript:alert(1)) [good](https://example.com)")
        self.assertIn("<strong>bold</strong>",safe)
        self.assertNotIn('href="javascript:',safe)
        self.assertIn("https://example.com",safe)


if __name__ == "__main__":
    unittest.main()
