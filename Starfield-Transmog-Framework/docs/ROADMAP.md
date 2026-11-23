# Milestones and release gates

## M0 — Initial project (complete)
- [x] Inspect uploaded original Transmog 1.0.0 archive and record counts.
- [x] Add independent read-only inspector and synthetic unit tests.
- [x] Configure repository-root GitHub Actions for static checks.
- [x] Implement read-only source link audit and optional current-master ARMO difference scanner (synthetic tests pass). 
- [ ] Run current-master scanner against a matching 2026 Starfield.esm (not available in CI) and verify in SF1Edit.

## M1 — Current-game compatibility (not started)
- [ ] Identify exact source of Skin vs quality/X-Tech upgrade incompatibility.
- [ ] Design independent patch, minimizing ARMO overrides.
- [ ] Verify original suit/helmet/pack transmog, upgrades, removal, and revert in-game.

## M2 — DLC equipment (not started)
- [ ] Inventory Shattered Space and Terran Armada ARMO/ARMA/OMOD records from installed data.
- [ ] Prototype one suit, helmet and pack per DLC, both appearance directions.
- [ ] Validate normal defense, legendary/quality changes, meshes and add-on index behavior.

## M3 — Third-party equipment (not started)
- [ ] Add Zone79 adapter (one spacesuit pilot first).
- [ ] Verify VCO mesh and morph behavior.
- [ ] Treat ordinary clothing/multi-slot outfits as a separate prototype.

## Build/release gates
- Serializer round-trip, conflict audit, license review, clean save and ongoing save testing.
- Never call the current static check a playable ESM build.
