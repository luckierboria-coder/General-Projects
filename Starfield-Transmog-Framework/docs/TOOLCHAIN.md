# Build toolchain and 1.16.244 data provenance

Checked 2026-11-23.

## Version-pinned libraries

| Tool | Pinned version | Purpose |
|---|---|---|
| .NET SDK | 9.0.x | Build and run C# tools |
| Taosecurity.Starfield.BuildKit | 0.4.2 | ESM output and Bethesda-compatible master/ID metadata |
| Mutagen.Bethesda.Starfield | 0.54.4 (transitive, exact) | Starfield plugin read/write APIs |
| Spriggit.Yaml.Starfield | 0.41.0 | YAML translation; \`source/.spriggit\` |
| SF1Edit | 4.1.5+ compatible release | Validate records and conflicts |

BuildKit 0.4.2 pins Mutagen 0.54.4. **Do not add a second, different Mutagen version** to the same builder.

Useful primary sources:
- https://www.nuget.org/packages/Taosecurity.Starfield.BuildKit/0.4.2
- https://www.nuget.org/packages/Mutagen.Bethesda.Starfield/0.54.4
- https://www.nuget.org/packages/Spriggit.Yaml.Starfield/0.41.0
- https://mutagen-modding.github.io/Spriggit/spriggit-file/
- https://github.com/TES5Edit/TES5Edit/releases

## GitHub Actions

The repository-root workflow runs Python checks and compiles a C# BuildKit
probe on GitHub-hosted Ubuntu using .NET 9. This is **toolchain validation,
not production plugin output**. The CI never downloads paid Bethesda masters.
No game credentials, Steam secrets, mod author binaries, or user data are
required for these checks.

## Build locally with licensed installed game data

From this subproject:

~~~powershell
dotnet restore toolchain/BuildProbe/BuildProbe.csproj
dotnet run --project toolchain/BuildProbe/BuildProbe.csproj -- --check-deps
dotnet run --project toolchain/BuildProbe/BuildProbe.csproj -- --smoke "D:\SteamLibrary\steamapps\common\Starfield\Data" "out\smoke"
~~~

The smoke file is a disposable plugin with one new keyword, **not a transmog
mod**. A real compatibility plugin will require the reviewed 1.16.244 ARMO
base records and independent authoring logic.

## Why public 1.16.244 data cannot substitute for Starfield.esm

A public reference extracted from Starfield **1.16.244.0** lists 180 types
and approximately 3.83 million total records:
https://taosecurity.github.io/starfield-record-types/

It reports signatures, sample EditorIDs and type counts. It does **not**
publish full subrecord payloads for our 136 affected ARMO forms, and thus
cannot establish exactly which 2026 fields the 2024 Transmog plugin overwrote.
SteamDB's depot manifest identifies the version and file size but does not
deliver licensed game content: https://steamdb.info/depot/1716742/manifests/

A legitimate 1.16.244 installation, offline extracted source records with
sufficient field provenance, or a lawfully accessible matching game master is
required for the per-form comparison. Do not use untrusted/pirated ESM copies.

## License boundary

BuildKit, Mutagen and Spriggit are GPL-3.0. The C# probe is GPL-3.0-only.
Other independent source files remain subject to the repository's own terms,
subject to review before distributing a combined binary or derivative plugin.
No assets from the original Nexus Transmog mod are in this repository.
