import unittest
from m3u8_finder import extract_m3u8, parse_variants, safe_filename, collect_site_links


class TestM3U8Finder(unittest.TestCase):
    def test_extract_absolute_query(self):
        s = '<video src="https://cdn.example.com/x/index.m3u8?token=abc&amp;v=1"></video>'
        self.assertEqual(extract_m3u8(s, 'https://site.example/page'),
                         ['https://cdn.example.com/x/index.m3u8?token=abc&v=1'])

    def test_extract_relative(self):
        s = "var src='/hls/720p.m3u8'; var other='../master.m3u8'"
        self.assertEqual(extract_m3u8(s, 'https://example.com/show/episode/1'),
                         ['https://example.com/hls/720p.m3u8', 'https://example.com/show/master.m3u8'])

    def test_extract_escaped(self):
        s = r'const url="https:\/\/cdn.example.org\/hls\/index.m3u8?x=1\u0026y=2"'
        self.assertEqual(extract_m3u8(s, 'https://example.com'),
                         ['https://cdn.example.org/hls/index.m3u8?x=1&y=2'])

    def test_variants(self):
        s = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1600000,RESOLUTION=1280x720
720/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360
360/index.m3u8
"""
        self.assertEqual(parse_variants(s, 'https://cdn.example.com/master.m3u8'), [
            ('https://cdn.example.com/720/index.m3u8', '1280x720 / 1.60 Mbps'),
            ('https://cdn.example.com/360/index.m3u8', '640x360 / 0.50 Mbps'),
        ])

    def test_site_links(self):
        s = '<a href="/movie/1">a</a><a href="https://evil.example/track">b</a><a href="/logout">c</a>'
        self.assertEqual(collect_site_links(s, 'https://example.com/', 'example.com'), ['https://example.com/movie/1'])

    def test_safe_filename(self):
        self.assertEqual(safe_filename('A:B / C?*'), 'A_B _ C__')


if __name__ == '__main__':
    unittest.main()
