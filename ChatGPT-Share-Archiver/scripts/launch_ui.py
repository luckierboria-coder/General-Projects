#!/usr/bin/env python3
"""Start the local ChatGPT share viewer and open it in the default browser."""

from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser


HOST = "127.0.0.1"
PORT = 8791
URL = f"http://{HOST}:{PORT}/"
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def is_our_server():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL + "health", timeout=2) as response:
            health = json.load(response)
            return health.get("app") == "chatgpt-share-ui" and Path(health.get("app_root", "")).resolve() == APP_ROOT
    except Exception:
        return False


def local_proxy():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
            address = winreg.QueryValueEx(key, "ProxyServer")[0]
        if enabled and isinstance(address, str):
            address = address.split(";")[0].split("=")[-1]
            host, port = address.rsplit(":", 1)
            with socket.create_connection((host, int(port)), timeout=1):
                return "http://" + address
    except (ImportError, OSError, ValueError):
        pass
    return None


def server_environment():
    """Onefile background server must unpack independently of short-lived launcher.

    PyInstaller >= 6.9 treats a subprocess of sys.executable as a worker by
    default. Reusing the launcher's _MEI directory breaks when the launcher
    exits and its temporary files (including base_library.zip) are deleted.
    """
    if getattr(sys, "frozen", False):
        return {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
    return None


def main():
    if not is_our_server():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind((HOST, PORT))
        except OSError as exc:
            raise RuntimeError(f"本机端口 {PORT} 已被其他程序占用。") from exc
        command = ([sys.executable, "--serve"] if getattr(sys, "frozen", False)
                   else [sys.executable, str(Path(__file__).with_name("ui_server.py"))]) + [
                   "--host", HOST, "--port", str(PORT),
                   "--archive-dir", str(APP_ROOT / "chat_archives")]
        proxy = local_proxy()
        if proxy:
            command.extend(["--proxy", proxy])
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(command, cwd=APP_ROOT, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags, close_fds=True, env=server_environment())
        for _ in range(150):
            if is_our_server():
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("界面未能启动。请确认 Chrome 或 Edge 可用，并检查端口 8791。")
    webbrowser.open(URL)
    print("聊天记录界面已打开：" + URL)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("启动失败：" + str(exc), file=sys.stderr)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), "ChatGPT 聊天记录查看器", 0x10)
        raise SystemExit(1)