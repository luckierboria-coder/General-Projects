"""Windows CI: check detached --serve survives onefile launcher cleanup.

Does not require Internet access, private ChatGPT data, or a browser session.
The workflow is responsible for stopping the server after this test.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener


BASE = "http://127.0.0.1:8791"
EXE = Path(__file__).resolve().parents[1] / "dist" / "ChatGPT-Share-Archiver.exe"


def request(opener, path, **kwargs):
    with opener.open(Request(BASE + path, **kwargs), timeout=4) as response:
        return response.read().decode("utf-8")


def main():
    if sys.platform != "win32":
        raise RuntimeError("This smoke test must be run on the Windows runner")
    if not EXE.is_file():
        raise RuntimeError(f"Executable missing: {EXE}")
    opener = build_opener(ProxyHandler({}))
    print("Launching PyInstaller onefile EXE", flush=True)
    with subprocess.Popen([str(EXE)], cwd=EXE.parent, env={**os.environ, "CHATGPT_ARCHIVER_NO_BROWSER": "1"},
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as launcher:
        try:
            launcher.wait(timeout=60)
        except subprocess.TimeoutExpired as exc:
            launcher.kill()
            raise RuntimeError("Launcher did not exit; cannot verify independent server") from exc
        if launcher.returncode:
            diagnostic = EXE.with_name("archiver-startup-error.txt")
            detail = diagnostic.read_text(encoding="utf-8") if diagnostic.exists() else "no diagnostic"
            raise RuntimeError(f"EXE launcher returned {launcher.returncode}: {detail}")
    # The launcher is now gone. Its own _MEI folder should be cleaned up,
    # but the detached server must still own a separate extraction directory.
    time.sleep(4)
    for attempt in range(20):
        try:
            health = json.loads(request(opener, "/health"))
            if health.get("ok") and health.get("app") == "chatgpt-share-ui":
                break
            raise RuntimeError(f"Unexpected health payload: {health}")
        except (URLError, TimeoutError):
            if attempt == 19:
                raise RuntimeError("Server vanished when launcher exited")
            time.sleep(0.5)
    page = request(opener, "/")
    token_match = re.search(r"const token = '([^']+)';", page)
    if not token_match:
        raise RuntimeError("Missing CSRF token in UI HTML")
    body = json.dumps({"url": "https://example.invalid"}).encode("utf-8")
    try:
        request(opener, "/api/load", method="POST", data=body, headers={
            "Content-Type": "application/json",
            "X-Local-Token": token_match.group(1)
        })
    except HTTPError as exc:
        message = json.loads(exc.read().decode("utf-8"))
        if exc.code != 400 or "error" not in message:
            raise RuntimeError(f"Unexpected /api/load result: {exc.code} {message}") from exc
    else:
        raise RuntimeError("Invalid URL was incorrectly accepted")
    print("PASS: onefile launcher exited, independent server survived, POST API worked", flush=True)


if __name__ == "__main__":
    main()
