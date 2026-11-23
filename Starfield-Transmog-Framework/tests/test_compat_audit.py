"""Synthetic, license-clean fixtures for the M1 read-only compatibility auditor."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from compat_audit import (
    AuditError, audit, iter_records, model_pairs, sequence_difference,
    subrecords, unmapped_fields,
)


def f(tag, value):
    return tag + struct.pack("<H", len(value)) + value


def r(tag, formid, content=b"", flags=0):
    return struct.pack("<4sIIIII", tag, len(content), flags, formid, 0, 0) + content


def g(contents):
    return struct.pack("<4sI4sIII", b"GRUP", len(contents) + 24, b"ARMO", 0, 0, 0) + contents


def armor(formid=0x00123456, defense=10, morphs=None):
    morphs = morphs or [(0, 0x00001234)]
    content = f(b"EDID", b"Sample_Suit\0") + f(b"DATA", struct.pack("<I", defense))
    for index, ref in morphs:
        content += f(b"INDX", struct.pack("<H", index)) + f(b"MODL", struct.pack("<I", ref))
    return r(b"ARMO", formid, content)


def source():
    header = r(b"TES4", 0, f(b"MAST", b"Starfield.esm\0"))
    ar = armor(morphs=[(0, 0x00001234), (2, 0x01000823)])
    arma = r(b"ARMA", 0x01000823, f(b"EDID", b"TransmogAddon\0"))
    omod = r(b"OMOD", 0x01000824, f(b"EDID", b"TestMod\0"))
    cobj = r(b"COBJ", 0x01000825, f(b"CNAM", struct.pack("<I", 0x01000824)))
    return header + g(ar + arma + omod + cobj)


class CompatibilityAuditTests(unittest.TestCase):
    def test_source_inventory(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "original.esm"
            p.write_bytes(source())
            data = audit(p)
            self.assertEqual(data["source"]["overridden_base_game_armor_count"], 1)
            self.assertEqual(data["source"]["model_index_links_total"], 2)
            self.assertEqual(data["source"]["missing_new_addon_references"], [])
            self.assertEqual(data["source"]["missing_new_omod_recipe_references"], [])
            self.assertIsNone(data["current_master_comparison"])

    def test_master_diff_without_false_model_flags(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path) / "original.esm"
            base = Path(path) / "Starfield.esm"
            p.write_bytes(source())
            base.write_bytes(r(b"TES4", 0) + g(armor(defense=15)))
            comparison = audit(p, base)["current_master_comparison"]
            self.assertEqual(comparison["matched_base_game_armors"], 1)
            self.assertEqual(comparison["armor_overrides_with_non_model_differences"], 1)
            self.assertEqual(
                comparison["potentially_stale_armor_records"][0]["different_non_model_subrecords"],
                ["DATA"],
            )

    def test_models_alone_do_not_raise_stale_alarm(self):
        with tempfile.TemporaryDirectory() as path:
            p, base = Path(path) / "original.esm", Path(path) / "Starfield.esm"
            p.write_bytes(source())
            base.write_bytes(r(b"TES4", 0) + g(armor()))
            result = audit(p, base)
            self.assertEqual(
                result["current_master_comparison"]["armor_overrides_with_non_model_differences"],
                0,
            )

    def test_form_ref_checks(self):
        fields = [
            ("INDX", struct.pack("<H", 0)),
            ("MODL", struct.pack("<I", 0x01000823)),
        ]
        self.assertEqual(model_pairs(fields), [(0, 0x01000823)])
        self.assertEqual(
            unmapped_fields(fields + [("DATA", b"X")]),
            (("DATA", b"X"),),
        )
        with self.assertRaises(AuditError):
            model_pairs([("INDX", b"\0\0")])

    def test_group_and_truncation_checks(self):
        self.assertEqual(len(list(iter_records(source()))), 5)
        with self.assertRaises(AuditError):
            list(iter_records(source()[:-2]))

    def test_subrecord_difference(self):
        self.assertEqual(
            sequence_difference([("DATA", b"a"), ("KSIZ", b"x")], [("DATA", b"b")]),
            ["DATA", "KSIZ"],
        )
        self.assertEqual(
            tuple(subrecords(f(b"EDID", b"value\0"))),
            (("EDID", b"value\0"),),
        )


if __name__ == "__main__":
    unittest.main()
