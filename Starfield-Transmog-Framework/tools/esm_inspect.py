#!/usr/bin/env python3
"""Read-only Starfield ESM/ESP record inventory, not a full xEdit replacement."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

HEADER_SIZE = 24
COMPRESSED = 0x00040000


class ParseError(ValueError):
    pass


def subrecords(payload: bytes):
    """Iterate Bethesda subrecords, including XXXX extended-length values."""
    pos = 0
    extended = None
    while pos + 6 <= len(payload):
        tag = payload[pos:pos + 4]
        length = struct.unpack_from("<H", payload, pos + 4)[0]
        pos += 6
        if tag == b"XXXX":
            if length != 4 or pos + 4 > len(payload):
                raise ParseError("Invalid XXXX extension")
            extended = struct.unpack_from("<I", payload, pos)[0]
            pos += 4
            continue
        if extended is not None:
            length = extended
            extended = None
        if pos + length > len(payload):
            raise ParseError("Subrecord overruns payload")
        yield tag, payload[pos:pos + length]
        pos += length
    if pos != len(payload) or extended is not None:
        raise ParseError("Trailing or truncated subrecord")


def inspect_bytes(blob: bytes) -> dict:
    if blob[:4] != b"TES4":
        raise ParseError("Missing TES4 plugin header")
    counts = Counter()
    masters = []
    omod_samples = []

    def walk(start: int, end: int) -> None:
        pos = start
        while pos < end:
            if pos + HEADER_SIZE > end:
                raise ParseError(f"Truncated record at 0x{pos:x}")
            tag, size = struct.unpack_from("<4sI", blob, pos)
            if tag == b"GRUP":
                if size < HEADER_SIZE or pos + size > end:
                    raise ParseError("Invalid GRUP size")
                walk(pos + HEADER_SIZE, pos + size)
                pos += size
                continue
            record_end = pos + HEADER_SIZE + size
            if record_end > end:
                raise ParseError(f"Invalid {tag!r} record size")
            flags = struct.unpack_from("<I", blob, pos + 8)[0]
            payload = blob[pos + HEADER_SIZE:record_end]
            if flags & COMPRESSED:
                if len(payload) < 4:
                    raise ParseError("Compressed record is truncated")
                expected = struct.unpack_from("<I", payload)[0]
                try:
                    payload = zlib.decompress(payload[4:])
                except zlib.error as exc:
                    raise ParseError("Compressed record is invalid") from exc
                if len(payload) != expected:
                    raise ParseError("Uncompressed-size mismatch")
            counts[tag.decode("ascii", "replace")] += 1
            if tag in (b"TES4", b"OMOD"):
                for field, value in subrecords(payload):
                    if tag == b"TES4" and field == b"MAST":
                        masters.append(value.rstrip(b"\0").decode("utf-8", "replace"))
                    if tag == b"OMOD" and field == b"EDID" and len(omod_samples) < 5:
                        omod_samples.append(value.rstrip(b"\0").decode("utf-8", "replace"))
                        break
            pos = record_end
        if pos != end:
            raise ParseError("Unconsumed bytes")

    walk(0, len(blob))
    return {
        "sha256": hashlib.sha256(blob).hexdigest(),
        "size_bytes": len(blob),
        "masters": masters,
        "record_counts": dict(sorted(counts.items())),
        "record_count_total": sum(counts.values()),
        "sample_omod_editor_ids": omod_samples,
        "warning": "Record inventory only; not a compatibility or gameplay test.",
    }


def load_plugin(path: Path) -> bytes:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            matches = [name for name in archive.namelist()
                       if name.lower().endswith((".esm", ".esp"))]
            if len(matches) != 1:
                raise ParseError("ZIP must contain exactly one ESM or ESP")
            return archive.read(matches[0])
    return path.read_bytes()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect_bytes(load_plugin(args.input)),
                        indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
