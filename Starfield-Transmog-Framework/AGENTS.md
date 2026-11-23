# Agent instructions — Starfield Transmog Framework

## Scope and current state
This is a subproject within General-Projects. Follow the root AGENTS.md and do not modify sibling projects. M0 has only a read-only ESM inspector, tests, and architecture notes. Do not imply an ESM build or in-game compatibility has been proven.

## Entry points
- `tools/esm_inspect.py`: inspect local .esm/.esp or single-plugin ZIP, without writing records.
- `tests/test_esm_inspect.py`: synthetic records tests, no proprietary inputs.
- `reference/source-structure.json`: verified inventory of user-provided Transmog v1.
- `docs/ROADMAP.md`: milestone gates.
- `../../.github/workflows/test-starfield-transmog.yml`: repository-root workflow for this subproject.

## Commands
Run from this directory:
```sh
python -m unittest discover -s tests -v
python tools/esm_inspect.py /private/path/to/Transmog.zip
```

## Rules
- Never commit Starfield.esm, DLC ESMs, original xoxTransmog.esm, BA2/NIF/mesh/texture assets, local saves, user-specific paths, or derivative files without distribution permission.
- Do not claim that a new appearance works without SF1Edit error review **and** in-game testing.
- Protect quality/X-Tech and legendary slots. Track original ARMO/ARMA and OMOD overwrites in the current game.
- Treat DLC records and Zone79/VCO compatibility as work to verify, not as implemented features.
- Prefer standalone compatibility plugins and explicit dependency checks.
- Keep Python inspection scripts read-only. Update tests and documentation alongside changes.
