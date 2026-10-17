#!/usr/bin/env python3
"""Single executable entry point for the viewer and its local server."""

import sys
import os
from pathlib import Path

from launch_ui import main as launch_ui
from ui_server import main as serve_ui


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        sys.argv.pop(1)
        serve_ui()
    else:
        try:
            launch_ui()
        except Exception as exc:
            if os.environ.get("CHATGPT_ARCHIVER_NO_BROWSER") == "1":
                # CI/no-browser mode must not block on a modal Windows dialog.
                Path(sys.executable).with_name("archiver-startup-error.txt").write_text(str(exc), encoding="utf-8")
            elif sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, str(exc), "ChatGPT 聊天记录查看器", 0x10)
            elif sys.stderr is not None:
                print("启动失败：" + str(exc), file=sys.stderr)
            raise SystemExit(1)