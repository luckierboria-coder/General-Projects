"""Offline regression tests; no OpenAI network access or browser required."""
import json
import sys
import threading
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export_shares import (validated_url, is_codex_share, add_codex_conversation,
                           fetch_codex_snapshot, _snapshot_body)
from ui_server import AppHandler

COD_URL = 'https://chatgpt.com/s/cx_0123456789abcdef0123456789abcdef'
STD_URL = 'https://chatgpt.com/share/01234567-89ab-cdef-0123-456789abcdef'


def fixture():
    return {
        'version': 1,
        'snapshot': {
            'title': '示例 Codex 记录',
            'turns': [
                {'items': [
                    {'type': 'userMessage', 'id': 'u1', 'content': [{'type': 'text', 'text': '请修复'}]},
                    {'type': 'agentProgress', 'text': '检查代码…'},
                    {'type': 'fileChange', 'path': 'foo.py', 'diff': '+new'},
                    {'type': 'agentMessage', 'id': 'a1', 'text': '修复完成'},
                ]},
                {'items': [
                    {'item': {'type': 'user_message', 'content': {'text': '再检查一下'}}},
                    {'type': 'agent_reasoning', 'summary': '再运行测试'},
                    {'type': 'agent_message', 'content': [{'type': 'text', 'text': '已检查'}]},
                ]},
            ],
        },
        'metadata': {'privateFields': '保留原始信息但不推断缺失字段'},
    }


class TestCodex(unittest.TestCase):
    def test_url_formats_and_reject_unsafe(self):
        self.assertEqual(validated_url(COD_URL)[1], 'cx_0123456789abcdef0123456789abcdef')
        self.assertEqual(validated_url(STD_URL)[1], '01234567-89ab-cdef-0123-456789abcdef')
        self.assertTrue(is_codex_share(COD_URL))
        self.assertFalse(is_codex_share(STD_URL))
        for invalid in ('https://evil.com/s/cx_' + '1'*32,
                        'http://chatgpt.com/s/cx_' + '1'*32,
                        'https://chatgpt.com/c/abcdef',
                        'https://chatgpt.com/s/cx_nothex',
                        'https://chatgpt.com:444/s/cx_' + '1'*32):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validated_url(invalid)

    def test_export_keeps_full_snapshot(self):
        root = ET.Element('chatgpt_share_archive')
        data = fixture()
        count, missing, nodes, rendered = add_codex_conversation(root, COD_URL, data)
        self.assertEqual((count, missing, nodes, rendered), (6, 0, 7, 6))
        conv = root.find('conversation')
        self.assertEqual(conv.get('snapshot_turn_count'), '2')
        self.assertEqual(conv.get('title'), '示例 Codex 记录')
        self.assertEqual(conv.findall('message')[0].findtext('text'), '请修复')
        self.assertEqual(conv.findall('message')[1].get('channel'), 'commentary')
        self.assertEqual(json.loads(conv.findtext('codex_snapshot_json')), data)
        self.assertEqual(json.loads(conv.findtext('codex_snapshot_json'))['snapshot']['turns'][0]['items'][2]['diff'], '+new')
        self.assertTrue(ET.fromstring(ET.tostring(root)).find('conversation') is not None)

    def test_bad_version_and_missing_items(self):
        for data in ({'version': 2, 'turns': []},
                     {'version': 1, 'turns': [{'items': 'bad'}]},
                     {'version': 1, 'turns': [{'other': []}]}):
            with self.assertRaises(RuntimeError):
                _snapshot_body(data)

    def test_xml_unsafe_chars_filtered(self):
        data = fixture()
        data['snapshot']['turns'][0]['items'][0]['content'] = 'hello\x01world'
        root = ET.Element('root')
        add_codex_conversation(root, COD_URL, data)
        self.assertIn('helloworld', ET.tostring(root, encoding='unicode'))

    def test_ui_codex_load_skips_browser(self):
        handler = object.__new__(AppHandler)
        handler.server = SimpleNamespace(browser=None, proxy=None, lock=threading.Lock(), sessions={})
        replies = []
        handler.send_json = lambda status, result: replies.append((status, result))
        with patch('ui_server.fetch_codex_snapshot', return_value=fixture()), \
             patch('ui_server.fetch_rendered', side_effect=AssertionError('browser called')):
            handler.load_chat({'url': COD_URL})
        self.assertEqual(replies[0][0], 200)
        self.assertEqual(replies[0][1]['source_type'], 'codex')
        self.assertEqual(replies[0][1]['message_count'], 6)
        self.assertIn('codex_snapshot_json', ET.tostring(next(iter(handler.server.sessions.values()))['root'], encoding='unicode'))

    def test_fetch_api_uses_pinned_endpoint(self):
        data = fixture()
        class FakeResponse:
            url = 'https://chatgpt.com/backend-api/wham/shared_threads/' + COD_URL.rsplit('/', 1)[-1]
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return json.dumps(data).encode()
        class FakeOpener:
            def open(self, request, timeout):
                self_url = request.full_url
                self_ref = request.get_header('Referer')
                assert self_url.endswith('/' + COD_URL.rsplit('/', 1)[-1])
                assert self_ref == COD_URL
                return FakeResponse()
        with patch('export_shares.build_opener', return_value=FakeOpener()):
            self.assertEqual(fetch_codex_snapshot(COD_URL), data)


if __name__ == '__main__':
    unittest.main()