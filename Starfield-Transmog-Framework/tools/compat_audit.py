#!/usr/bin/env python3
"""Read-only audit of a Starfield Transmog ESM against an optional current master.

Not a plugin writer, xEdit replacement, or proof of in-game compatibility.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import json
import mmap
from pathlib import Path
import struct
import zipfile
import zlib

HEADER_SIZE = 24
COMPRESSED = 0x00040000
RELEVANT_TAGS = frozenset({b"TES4", b"ARMO", b"ARMA", b"OMOD", b"COBJ"})
WATCH_FIELDS = frozenset({
    "OBTS", "OBTF", "OBTE", "APPR", "INRD", "DAMA", "BFCB",
    "BFCE", "REFL", "FNAM", "DATA", "KSIZ", "KWDA",
})


class AuditError(ValueError):
    """The file is malformed or does not match the expected plugin structure."""


@contextmanager
def input_bytes(path: Path):
    """Map installed ESMs without copying them; extract local single-plugin ZIPs."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            candidates = [
                f for f in archive.namelist()
                if f.lower().endswith((".esm", ".esp")) and not f.endswith("/")
            ]
            if len(candidates) != 1:
                raise AuditError("ZIP must have exactly one .esm/.esp")
            if archive.getinfo(candidates[0]).file_size > 100 * 1024 * 1024:
                raise AuditError("Archived plugin exceeds 100 MiB safety limit")
            yield archive.read(candidates[0])
    else:
        with path.open("rb") as f:
            if f.seek(0, 2) < HEADER_SIZE:
                raise AuditError("Empty or truncated plugin")
            f.seek(0)
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as blob:
                yield blob


def iter_records(blob, tags=RELEVANT_TAGS, form_ids=None):
    """Read 24-byte headers/groups; decompress only requested records."""
    pos, end = 0, len(blob)
    if end < HEADER_SIZE or bytes(blob[:4]) != b"TES4":
        raise AuditError("Missing TES4 header")
    group_ends = [end]
    while pos < end:
        while len(group_ends) > 1 and pos == group_ends[-1]:
            group_ends.pop()
        if pos + HEADER_SIZE > group_ends[-1]:
            raise AuditError(f"Invalid record boundary at 0x{pos:08X}")
        tag, size = struct.unpack_from("<4sI", blob, pos)
        if tag == b"GRUP":
            if size < HEADER_SIZE or pos + size > group_ends[-1]:
                raise AuditError(f"Invalid GRUP size at 0x{pos:08X}")
            group_ends.append(pos + size)
            pos += HEADER_SIZE
            continue
        next_pos = pos + HEADER_SIZE + size
        if next_pos > group_ends[-1]:
            raise AuditError(f"Invalid {tag!r} size at 0x{pos:08X}")
        flags = struct.unpack_from("<I", blob, pos + 8)[0]
        form_id = struct.unpack_from("<I", blob, pos + 12)[0]
        if tag in tags and (form_ids is None or form_id in form_ids or tag == b"TES4"):
            payload = bytes(blob[pos + HEADER_SIZE:next_pos])
            if flags & COMPRESSED:
                if len(payload) < 4:
                    raise AuditError("Compressed record too short")
                expected = struct.unpack_from("<I", payload)[0]
                try:
                    payload = zlib.decompress(payload[4:])
                except zlib.error as exc:
                    raise AuditError("Corrupted compressed record") from exc
                if len(payload) != expected:
                    raise AuditError("Compressed record size mismatch")
            yield tag, form_id, payload
        pos = next_pos
    while len(group_ends) > 1 and pos == group_ends[-1]:
        group_ends.pop()
    if pos != end or len(group_ends) != 1:
        raise AuditError("Unclosed record group")


def subrecords(payload):
    """Decode plain Bethesda subrecords, including XXXX extended sizes."""
    pos, end = 0, len(payload)
    extended = None
    while pos + 6 <= end:
        tag, size = struct.unpack_from("<4sH", payload, pos)
        pos += 6
        if tag == b"XXXX":
            if size != 4 or pos + 4 > end:
                raise AuditError("Bad XXXX length")
            extended = struct.unpack_from("<I", payload, pos)[0]
            pos += 4
            continue
        if extended is not None:
            size, extended = extended, None
        if pos + size > end:
            raise AuditError("Subrecord overruns payload")
        yield tag.decode("ascii", "replace"), bytes(payload[pos:pos + size])
        pos += size
    if pos != end or extended is not None:
        raise AuditError("Truncated subrecord")


def form_ref(value):
    if len(value) != 4:
        raise AuditError("Unexpected non-4-byte FormID reference")
    return struct.unpack("<I", value)[0]


def edid(fields):
    return next((
        value.rstrip(b"\0").decode("utf-8", "replace")
        for tag, value in fields if tag == "EDID"
    ), "")


def model_pairs(fields):
    """Read adjacent INDX/MODL index-to-ARMA links."""
    pairs = []
    for i, (tag, value) in enumerate(fields):
        if tag == "INDX":
            if len(value) != 2 or i + 1 >= len(fields) or fields[i + 1][0] != "MODL":
                raise AuditError("Unpaired or invalid ARMO INDX/MODL")
            pairs.append((struct.unpack("<H", value)[0], form_ref(fields[i + 1][1])))
    return pairs


def unmapped_fields(fields):
    """Ignore complete model-index pairs only, retaining unrelated MODL fields."""
    output = []
    i = 0
    while i < len(fields):
        tag, value = fields[i]
        if tag == "INDX":
            if len(value) != 2 or i + 1 >= len(fields) or fields[i + 1][0] != "MODL":
                raise AuditError("Unpaired or invalid ARMO INDX/MODL")
            i += 2
            continue
        output.append((tag, value))
        i += 1
    return tuple(output)


def sequence_difference(left, right):
    """Return changed subrecord tags; these are candidates, not confirmed causes."""
    def index(fields):
        out = {}
        for tag, data in fields:
            out.setdefault(tag, []).append(data)
        return out
    a, b = index(left), index(right)
    return [tag for tag in sorted(a.keys() | b.keys()) if a.get(tag) != b.get(tag)]


def audit(source, current_master=None):
    with input_bytes(Path(source)) as blob:
        records = list(iter_records(blob))
    masters = []
    for tag, _fid, payload in records:
        if tag == b"TES4":
            masters = [
                v.rstrip(b"\0").decode("utf-8", "replace")
                for k, v in subrecords(payload) if k == "MAST"
            ]
            break
    if masters != ["Starfield.esm"]:
        raise AuditError("Expected Transmog structure with Starfield.esm as sole master")

    armors, addons, omods, crafting = {}, set(), set(), {}
    for tag, formid, payload in records:
        if tag == b"ARMO":
            if formid >> 24 != 0:
                raise AuditError(f"ARMO {formid:08X} is not a base-game override")
            if formid in armors:
                raise AuditError("Duplicate ARMO FormID")
            fields = tuple(subrecords(payload))
            armors[formid] = (edid(fields), fields, model_pairs(fields))
        elif tag == b"ARMA":
            addons.add(formid)
        elif tag == b"OMOD":
            omods.add(formid)
        elif tag == b"COBJ":
            fields = tuple(subrecords(payload))
            crafting[formid] = [
                form_ref(v) for k, v in fields if k == "CNAM"
            ]

    counts = Counter(tag.decode("ascii") for tag, _, _ in records)
    missing_addons = sorted({
        target for _, (_, _, pairs) in armors.items()
        for _, target in pairs if target >> 24 == 1 and target not in addons
    })
    missing_recipes = sorted({
        target for refs in crafting.values()
        for target in refs if target >> 24 == 1 and target not in omods
    })
    categories = Counter()
    for editor, _, _ in armors.values():
        name = editor.lower()
        category = "helmet" if "helmet" in name else "backpack" if "backpack" in name else "spacesuit"
        categories[category] += 1

    result = {
        "source": {
            "record_counts": dict(sorted(counts.items())),
            "overridden_base_game_armor_count": len(armors),
            "added_armor_addon_count": len(addons),
            "base_game_armor_categories": dict(sorted(categories.items())),
            "model_index_links_total": sum(len(pairs) for _, _, pairs in armors.values()),
            "model_index_links_to_new_addons": sum(
                target >> 24 == 1 for _, (_, _, pairs) in armors.items() for _, target in pairs
            ),
            "missing_new_addon_references": [f"{x:08X}" for x in missing_addons],
            "missing_new_omod_recipe_references": [f"{x:08X}" for x in missing_recipes],
            "notes": (
                "ARMO records are full overrides; non-model fields can become stale. "
                "The inventory alone does not establish an X-Tech root cause."
            ),
        },
        "current_master_comparison": None,
    }
    if current_master is None:
        result["next_step"] = (
            "Run with --current-master pointing to the installed Starfield.esm. "
            "Review divergent armor fields with SF1Edit before creating a patch."
        )
        return result

    with input_bytes(Path(current_master)) as base:
        base_records = {
            fid: tuple(subrecords(payload))
            for tag, fid, payload in iter_records(
                base, tags={b"ARMO"}, form_ids=set(armors)
            ) if tag == b"ARMO"
        }
    missing = sorted(set(armors) - set(base_records))
    changed_tags = Counter()
    details = []
    for fid, (editor, fields, pairs) in sorted(armors.items()):
        if fid not in base_records:
            continue
        current_fields = base_records[fid]
        diff = sequence_difference(
            unmapped_fields(fields), unmapped_fields(current_fields)
        )
        changed_tags.update(diff)
        details.append({
            "form_id": f"{fid:08X}",
            "editor_id": editor,
            "source_model_links": len(pairs),
            "current_model_links": len(model_pairs(current_fields)),
            "different_non_model_subrecords": diff,
            "watchlist_differences": [tag for tag in diff if tag in WATCH_FIELDS],
        })
    result["current_master_comparison"] = {
        "matched_base_game_armors": len(details),
        "missing_base_game_armors": [f"{x:08X}" for x in missing],
        "armor_overrides_with_non_model_differences": sum(
            bool(x["different_non_model_subrecords"]) for x in details
        ),
        "different_subrecord_tags_by_armor_count": dict(sorted(changed_tags.items())),
        "potentially_stale_armor_records": [
            x for x in details if x["different_non_model_subrecords"]
        ],
        "analysis_limit": (
            "Byte differences alone cannot establish gameplay impact. "
            "Localization, record order and opaque components can vary. "
            "Confirm differences in SF1Edit before any patch."
        ),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original Transmog ESM or local ZIP")
    parser.add_argument("--current-master", type=Path, help="Installed Starfield.esm (never upload)")
    parser.add_argument("--out", type=Path, help="Write local JSON report")
    args = parser.parse_args()
    result = json.dumps(
        audit(args.source, args.current_master), indent=2, ensure_ascii=False
    ) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
