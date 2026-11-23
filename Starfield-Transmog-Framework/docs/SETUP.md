# Windows setup

## M0
1. Install Python 3.12+, Git and any editor.
2. Keep downloaded Bethesda masters and \`Transmog-10692-v1-0-0-1721772898.zip\` **outside the repository**.
3. From \`General-Projects/Starfield-Transmog-Framework\` run:
   - \`py -3 -m unittest discover -s tests -v\`
   - \`py -3 tools/esm_inspect.py "<local path to downloaded Transmog ZIP>" --out out/source-inspection.json\`

## For in-game plugin development (M1/M2)
- Installed Starfield PC version and target DLC.
- Current SF1Edit/xEdit build, Starfield Creation Kit and a Mod Organizer 2 or Vortex test profile.
- A new/clean test save and a backed-up existing save.
- Later, pin and verify working Spriggit / Mutagen.Bethesda.Starfield versions before adding an ESM build job.
- GitHub-hosted runners do not have your installed Starfield masters or Creation Kit.

## CI
\`.github/workflows/test-starfield-transmog.yml\` is at **repository root**. It runs Python syntax/unit checks only. There is no playable ESM artifact at this milestone.
