#!/usr/bin/env python3
"""Single executable entry point for the viewer and its local server."""

import sys

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
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, str(exc), "ChatGPT 聊天记录查看器", 0x10)
            else:
                print("启动失败：" + str(exc), file=sys.stderr)
            raise SystemExit(1)