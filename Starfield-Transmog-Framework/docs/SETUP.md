# Windows setup

## M0
1. Install Python 3.12+, Git and any editor.
2. Keep downloaded Bethesda masters and `Transmog-10692-v1-0-0-1721772898.zip` **outside the repository**.
3. From `General-Projects/Starfield-Transmog-Framework` run:
   - `py -3 -m unittest discover -s tests -v`
   - `py -3 tools/esm_inspect.py "<local path to downloaded Transmog ZIP>" --out out/source-inspection.json`

## For in-game plugin development (M1/M2)
- Installed Starfield PC version and target DLC.
- Current SF1Edit/xEdit build, Starfield Creation Kit and a Mod Organizer 2 or Vortex test profile.
- A new/clean test save and a backed-up existing save.
- Later, pin and verify working Spriggit / Mutagen.Bethesda.Starfield versions before adding an ESM build job.
- GitHub-hosted runners do not have your installed Starfield masters or Creation Kit.

## CI
`.github/workflows/test-starfield-transmog.yml` is at **repository root**. It runs Python syntax/unit checks only. There is no playable ESM artifact at this milestone.

## M1 test with installed game data

From \`Starfield-Transmog-Framework\`:

~~~powershell
py -3 tools/compat_audit.py "C:\MyMods\Transmog.zip" --current-master "D:\SteamLibrary\steamapps\common\Starfield\Data\Starfield.esm" --out out\current-master-diff.json
~~~

Do not commit \`out/\` reports or upload the installed master; the game data must remain on your PC. This audit only reports candidate differences. Review \`potentially_stale_armor_records\` in SF1Edit and confirm X-Tech, Skin, quality and legendary behavior in-game before writing a patch.

## Optional .NET 9 toolchain

Read \`docs/TOOLCHAIN.md\` for pinned dependency versions and compiler
smoke-test instructions. This toolchain does not require your installed
game files for CI dependency compilation, but a real serializer test or
ARMO field comparison still requires licensed 1.16.244 game master data.

