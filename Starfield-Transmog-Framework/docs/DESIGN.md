# Architecture decisions (M0)

- Input example: user-provided Transmog v1 (single `xoxTransmog.esm`; static ARMO/ARMA/OMOD/COBJ records).
- Objective: appearance-only change, preserving all equipped item statistics, legendary mods and post-2024 quality/X-Tech systems.
- Prefer original standalone compatibility plugin; do not silently replace or redistribute original author's ESM.
- Core data relationships: source item ARMO, displayed addon/model ARMA, skin OMOD, workbench COBJ and any material variants.
- New DLC assets must be inspected from user's installed master records; do not invent FormIDs or assume mesh compatibility.
- Third-party spacesuits and ordinary clothing are separate compatibility problems. VCO/Zone79 body slots, morph data, gender and footwear require testing.
- Current read-only parser is not an ESM writer, xEdit replacement, or evidence of playable functionality.
- Future option: Spriggit for text sources or Mutagen.Bethesda.Starfield for generated records, conditional on lossless round-trip validation.
