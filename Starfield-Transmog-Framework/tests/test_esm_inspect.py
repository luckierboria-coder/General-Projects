import struct
import unittest
import zlib
from tools.esm_inspect import inspect_bytes, subrecords, ParseError


def field(tag, value):
    return tag + struct.pack("<H", len(value)) + value


def record(tag, payload, flags=0):
    return struct.pack("<4sIIIII", tag, len(payload), flags, 0, 0, 0) + payload


def group(contents):
    return struct.pack("<4sI4sIII", b"GRUP", 24 + len(contents), b"ARMO", 0, 0, 0) + contents


class TestESMInspector(unittest.TestCase):
    def setUp(self):
        self.header = record(b"TES4", field(b"MAST", b"Starfield.esm\0"))

    def test_counts_and_masters(self):
        result = inspect_bytes(self.header + group(record(b"ARMA", b"")))
        self.assertEqual(result["masters"], ["Starfield.esm"])
        self.assertEqual(result["record_counts"], {"ARMA": 1, "TES4": 1})

    def test_compression(self):
        payload = field(b"EDID", b"Test\0")
        data = struct.pack("<I", len(payload)) + zlib.compress(payload)
        result = inspect_bytes(self.header + group(record(b"OMOD", data, 0x00040000)))
        self.assertEqual(result["record_counts"]["OMOD"], 1)

    def test_malformed(self):
        with self.assertRaises(ParseError):
            inspect_bytes(self.header[:-1])

    def test_extended_subrecords(self):
        payload = b"XXXX" + struct.pack("<HI", 4, 70000) + b"DATA" + struct.pack("<H", 0) + b"x" * 70000
        self.assertEqual(len(list(subrecords(payload))[0][1]), 70000)


if __name__ == "__main__":
    unittest.main()
