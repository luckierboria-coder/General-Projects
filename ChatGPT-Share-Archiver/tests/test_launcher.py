"""Regression tests for PyInstaller onefile launcher background server lifetime."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import launch_ui


class LauncherEnvironmentTests(unittest.TestCase):
    def test_frozen_server_starts_with_independent_extraction(self):
        with patch.object(launch_ui.sys, "frozen", True, create=True), \
             patch.dict(os.environ, {"_PYI_APPLICATION_HOME_DIR": r"C:\\Temp\\_MEI12345"}), \
             patch("launch_ui.is_our_server", side_effect=[False, True]), \
             patch("launch_ui.local_proxy", return_value=None), \
             patch("launch_ui.socket.socket"), \
             patch("launch_ui.webbrowser.open"), \
             patch("launch_ui.print", create=True), \
             patch("launch_ui.subprocess.Popen") as popen:
            launch_ui.main()
            args, kwargs = popen.call_args
            self.assertEqual(args[0][:2], [sys.executable, "--serve"])
            self.assertEqual(kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
            self.assertEqual(kwargs["env"]["_PYI_APPLICATION_HOME_DIR"], r"C:\\Temp\\_MEI12345")
            self.assertTrue(kwargs["close_fds"])

    def test_source_launch_does_not_reset_pyinstaller_environment(self):
        with patch.object(launch_ui.sys, "frozen", False, create=True), \
             patch("launch_ui.is_our_server", side_effect=[False, True]), \
             patch("launch_ui.local_proxy", return_value=None), \
             patch("launch_ui.socket.socket"), \
             patch("launch_ui.webbrowser.open"), \
             patch("launch_ui.print", create=True), \
             patch("launch_ui.subprocess.Popen") as popen:
            launch_ui.main()
            args, kwargs = popen.call_args
            self.assertEqual(args[0][1], str(Path(launch_ui.__file__).with_name("ui_server.py")))
            self.assertIsNone(kwargs["env"])


if __name__ == "__main__":
    unittest.main()
