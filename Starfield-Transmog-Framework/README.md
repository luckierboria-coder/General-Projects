# Starfield Transmog Framework

Open-source development tools for a **Starfield** equipment appearance system using native Skin / OMOD records.

**Current stage: M0 (bootstrap and read-only analysis). Not yet a playable mod or a compiled ESM.**

## Goals

- Keep the actual equipped item's defense, weight, legendary effects, quality / X-Tech progression, and perks intact.
- Change visible spacesuit, helmet, and boost-pack appearances via native Skin/OMOD mechanisms.
- Expand to Shattered Space / Terran Armada, then separately to third-party models (especially Zone79).
- Preserve compatibility with VCO body morphs, meshes and equipment slots wherever possible.
- Develop a reproducible plugin build process; verify it before announcing downloadable ESM builds.

## Verified source inventory

The user-provided **Transmog 1.0.0** archive contains only `Data/xoxTransmog.esm`; no DLL, Papyrus script or bundled mesh. A read-only inspection found:

| Record | Count |
|---|---:|
| ARMO | 136 |
| ARMA | 305 |
| OMOD | 136 |
| COBJ | 136 |
| TES4 | 1 |

Only declared master: `Starfield.esm`. See [source-structure.json](reference/source-structure.json).

This demonstrates a pure-record architecture; it does **not** prove compatibility with current DLC/quality upgrades or arbitrary third-party clothes.

## Use locally

Requirements: Python 3.12 or newer. All Bethesda and third-party binaries stay **outside this public repository**.

```powershell
cd Starfield-Transmog-Framework
py -3 -m unittest discover -s tests -v
py -3 tools/esm_inspect.py "D:\Mods\Transmog-10692-v1-0-0-1721772898.zip" --out out\source-inspection.json
```

Read [setup](docs/SETUP.md), [architecture](docs/DESIGN.md) and [milestones](docs/ROADMAP.md).

## Build and attribution

GitHub Actions currently performs **static tests only**; no ESM compilation/serialization. An eventual build may use Mutagen.Bethesda.Starfield and/or Spriggit after proven Starfield record round-trip support.

The original [Spacesuit Transmogrification (Nexus 10692)](https://www.nexusmods.com/starfield/mods/10692) and its author's binaries are **not redistributed**. Obtain permissions before distributing modified original records/resources. A clean-room, original compatibility plugin is preferred.

Repository-wide [LICENSE](../LICENSE) applies to original source code here; it does not grant rights to third-party assets.

## M1 compatibility audit (implemented; read-only)

To audit the 2024 Transmog plugin without installed game files:

~~~powershell
py -3 tools/compat_audit.py "D:\Downloads\Transmog-10692-v1-0-0-1721772898.zip" --out out\source-audit.json
~~~

**To check outdated record overrides**, run locally against the \`Starfield.esm\` **from your current installation**:

~~~powershell
py -3 tools/compat_audit.py "D:\Downloads\Transmog-10692-v1-0-0-1721772898.zip" --current-master "C:\Program Files (x86)\Steam\steamapps\common\Starfield\Data\Starfield.esm" --out out\current-master-diff.json
~~~

The inspector checks 136 overridden ARMO records for byte-level non-model field changes, verifies the added ARMA links and COBJ→OMOD targets, and produces a local JSON report. This is **not an ESM patcher**; a master-file difference alone is not proof of the X-Tech issue. Review candidate fields in SF1Edit before editing. The plugin ZIP, installed master and report remain local (not in GitHub).

The user-supplied original contains **51 spacesuit, 44 helmet and 41 backpack overrides**, with 15,162 INDX/MODL model links (14,708 pointing at newly added local addons). No dangling local ARMA or OMOD recipe links were found.
