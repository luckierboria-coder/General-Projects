"""Offline regressions for HTTP-first ChatGPT shares and Windows browser fallback."""
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from export_shares import _fetch_public_share_html, embedded_share_data, fetch_rendered

URL = "https://chatgpt.com/share/01234567-89ab-cdef-0123-456789abcdef"
SHARE_ID = URL.rsplit("/", 1)[-1]


def embedded_fixture():
    values = [
        {"_1": 2}, "loaderData", {"_3": 4},
        "routes/share.$shareId.($action)",
        {"_5": 6, "_7": 11},
        "serverResponse", {"_8": 9}, "sharedConversationId", "data",
        {"_10": 12}, "linear_conversation", SHARE_ID, [],
    ]
    payload = json.dumps(values)
    point = len(payload) // 2
    script = "window.__reactRouterContext.streamController.enqueue("
    return ("<!doctype html><html><script>" + script + json.dumps(payload[:point]) + ");"
            + script + json.dumps(payload[point:]) + ");</script></html>")


class MockResponse:
    def __init__(self, html, url=URL):
        self.url = url
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.html = html
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, amount): return self.html.encode("utf-8")[:amount]


class TestShareFetch(unittest.TestCase):
    def test_split_react_stream_is_decoded(self):
        _, route, data, nodes = embedded_share_data(embedded_fixture())
        self.assertEqual(route["sharedConversationId"], 11)
        self.assertEqual(data["linear_conversation"], 12)
        self.assertEqual(nodes, [])

    def test_http_first_works_without_browser(self):
        html = embedded_fixture()
        opener = SimpleNamespace(open=lambda request, timeout: MockResponse(html))
        with patch("export_shares.build_opener", return_value=opener), \
             patch("export_shares.find_browser", side_effect=AssertionError("browser selected")), \
             patch("export_shares.subprocess.run", side_effect=AssertionError("browser launched")):
            self.assertEqual(fetch_rendered(URL, None, None, 30, 1000), html)

    def test_direct_http_rejects_wrong_share_id(self):
        wrong = MockResponse(embedded_fixture(), url=URL.replace(SHARE_ID, "0"*36))
        opener = SimpleNamespace(open=lambda request, timeout: wrong)
        with patch("export_shares.build_opener", return_value=opener):
            self.assertIsNone(_fetch_public_share_html(URL, None, 30))

    def test_empty_headless_stdout_retries_with_simple_mode(self):
        first = subprocess.CompletedProcess([], 0, b"", b"")
        second = subprocess.CompletedProcess([], 0, b"<html>retry worked</html>", b"")
        with patch("export_shares._fetch_public_share_html", return_value=None), \
             patch("export_shares.find_browser", return_value="fake-chrome.exe"), \
             patch("export_shares.subprocess.run", side_effect=[first, second]) as runner:
            html = fetch_rendered(URL, None, None, 30, 1000)
        self.assertIn("retry worked", html)
        self.assertIn("--headless=new", runner.call_args_list[0].args[0])
        self.assertIn("--headless", runner.call_args_list[1].args[0])
        self.assertFalse(any(x.startswith("--virtual-time-budget") for x in runner.call_args_list[1].args[0]))

    def test_all_browser_attempts_empty_gives_clear_error(self):
        empty = subprocess.CompletedProcess([], 0, b"", b"")
        with patch("export_shares._fetch_public_share_html", return_value=None), \
             patch("export_shares.find_browser", return_value="fake-chrome.exe"), \
             patch("export_shares.subprocess.run", return_value=empty):
            with self.assertRaisesRegex(RuntimeError, "HTML 0 字节"):
                fetch_rendered(URL, None, None, 30, 1000)


if __name__ == "__main__":
    unittest.main()
