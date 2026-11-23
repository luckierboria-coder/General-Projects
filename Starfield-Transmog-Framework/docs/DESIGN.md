# Architecture decisions (M0)

- Input example: user-provided Transmog v1 (single `xoxTransmog.esm`; static ARMO/ARMA/OMOD/COBJ records).
- Objective: appearance-only change, preserving all equipped item statistics, legendary mods and post-2024 quality/X-Tech systems.
- Prefer original standalone compatibility plugin; do not silently replace or redistribute original author's ESM.
- Core data relationships: source item ARMO, displayed addon/model ARMA, skin OMOD, workbench COBJ and any material variants.
- New DLC assets must be inspected from user's installed master records; do not invent FormIDs or assume mesh compatibility.
- Third-party spacesuits and ordinary clothing are separate compatibility problems. VCO/Zone79 body slots, morph data, gender and footwear require testing.
- Current read-only parser is not an ESM writer, xEdit replacement, or evidence of playable functionality.
- Future option: Spriggit for text sources or Mutagen.Bethesda.Starfield for generated records, conditional on lossless round-trip validation.

## M1 evidence and constraint (2026-11-23)

Original uploaded plugin: 136 complete base-game ARMO overrides; 305 own ARMA additions; 136 OMODs; 136 COBJ recipes. 15,162 worn-model index links appear in those ARMO overrides, of which 14,708 reference 0x01 local addon FormIDs. Every such addon exists, and COBJ-created local OMOD targets resolve. The ESM's sole master is Starfield.esm.

\`compat_audit.py\` optionally compares the non-model payloads of these ARMO records against **the user's actually installed** Starfield.esm. It deliberately excludes the model-index pairs and flags all other divergent subrecord types for SF1Edit review. It does not attempt to interpret or merge opaque component data. Older complete record copies may shadow newer quality-related changes, but the root cause has not been established without comparing against installed masters and testing in-game.
