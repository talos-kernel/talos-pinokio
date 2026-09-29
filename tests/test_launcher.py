import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import launcher


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="talos-launcher-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        for name, value in (("ROOT", self.root), ("APP", self.app),
                            ("MARKER", self.app / ".pinokio-installed.json")):
            context = patch.object(launcher, name, value)
            context.start()
            self.addCleanup(context.stop)

    def installed(self):
        (self.app / ".venv/bin").mkdir(parents=True)
        (self.app / ".venv/bin/python").touch()
        launcher.MARKER.write_text(json.dumps(launcher.RELEASE))

    def test_environment_does_not_inherit_secrets_or_policy(self):
        with patch.dict(launcher.os.environ, {
            "HOME": "/tmp/operator", "PATH": "/usr/bin", "TALOS_ALLOW_ALL": "1",
            "OPENAI_API_KEY": "inert-test-value", "ANTHROPIC_API_KEY": "inert-test-value",
            "TALOS_REASONER": "other-provider", "PYTHONPATH": "/tmp/untrusted",
        }, clear=True):
            env = launcher.clean_environment()
        self.assertEqual(env["HOME"], "/tmp/operator")
        self.assertEqual(env["TALOS_SECRETS_ENV"], str(self.app / "talos.env"))
        self.assertFalse(set(env) & {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TALOS_ALLOW_ALL", "TALOS_REASONER", "PYTHONPATH"})

    def test_existing_directory_is_never_overwritten(self):
        self.app.mkdir()
        note = self.app / "keep.txt"
        note.write_text("keep")
        with self.assertRaisesRegex(RuntimeError, "Nothing was overwritten"):
            launcher.install()
        self.assertEqual(note.read_text(), "keep")

    def test_existing_symlink_is_refused(self):
        self.app.symlink_to(self.root / "missing-target")
        with self.assertRaises(RuntimeError):
            launcher.install()

    def test_commands_reject_linked_app_directory(self):
        self.installed()
        saved = self.root / "other-installation"
        self.app.rename(saved)
        self.app.symlink_to(saved)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            launcher.command("doctor")
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            launcher.install()

    def test_repeat_install_preserves_all_data(self):
        self.installed()
        state = self.app / "state.txt"
        state.write_text("configuration and history")
        before = {str(p): p.read_bytes() for p in self.app.rglob("*") if p.is_file()}
        with patch.object(launcher.urllib.request, "urlopen") as request:
            launcher.install()
            request.assert_not_called()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.app.rglob("*") if p.is_file()})

    def test_different_version_cannot_auto_upgrade(self):
        self.installed()
        launcher.MARKER.write_text('{"version":"another-version"}')
        with self.assertRaisesRegex(RuntimeError, "Automatic core upgrades"):
            launcher.install()

    def test_missing_python_fails_closed(self):
        self.installed()
        (self.app / ".venv/bin/python").unlink()
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            launcher.install()

    def test_hash_mismatch_never_executes(self):
        with patch.object(launcher.urllib.request, "urlopen", return_value=io.BytesIO(b"wrong installer")), patch.object(launcher.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                launcher.install()
            run.assert_not_called()
        self.assertFalse(self.app.exists())
        self.assertFalse((self.root / ".installing").exists())

    def test_failed_install_cannot_create_success_marker(self):
        data = b"inert installer fixture"
        release = dict(launcher.RELEASE, installer_sha256=hashlib.sha256(data).hexdigest())
        with patch.object(launcher, "RELEASE", release), patch.object(launcher.urllib.request, "urlopen", return_value=io.BytesIO(data)), patch.object(launcher.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "installer")):
            with self.assertRaises(subprocess.CalledProcessError):
                launcher.install()
        self.assertFalse(launcher.MARKER.exists())
        self.assertFalse((self.root / ".installing").exists())

    def test_concurrent_install_is_refused(self):
        (self.root / ".installing").touch()
        with patch.object(launcher.urllib.request, "urlopen") as request:
            with self.assertRaises(FileExistsError):
                launcher.install()
            request.assert_not_called()
        self.assertTrue((self.root / ".installing").exists())

    def test_command_requires_installation(self):
        with self.assertRaisesRegex(RuntimeError, "Install Talos first"):
            launcher.command("chat")

    def test_unknown_command_is_refused(self):
        self.installed()
        with self.assertRaises(ValueError):
            launcher.command("chat; arbitrary-command")

    def test_interactive_actions_require_both_ttys(self):
        self.installed()
        for action in ("setup", "chat"):
            for stdin, stdout in ((False, True), (True, False), (False, False)):
                with self.subTest(action=action, stdin=stdin, stdout=stdout), patch.object(launcher.sys.stdin, "isatty", return_value=stdin), patch.object(launcher.sys.stdout, "isatty", return_value=stdout), patch.object(launcher.os, "execve") as execute:
                    with self.assertRaisesRegex(RuntimeError, "interactive terminal"):
                        launcher.command(action)
                    execute.assert_not_called()

    def test_setup_uses_isolated_config_and_real_cli(self):
        self.installed()
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), patch.object(launcher.sys.stdout, "isatty", return_value=True), patch.object(launcher.os, "chdir") as cd, patch.object(launcher.os, "execve") as execute:
            launcher.command("setup")
        cd.assert_called_once_with(self.app)
        args = execute.call_args.args
        self.assertEqual(args[1][1:], ["-m", "talos", "setup", "terminal", "--out", str(self.app / "talos.env")])
        self.assertEqual(args[2]["TALOS_SECRETS_ENV"], str(self.app / "talos.env"))

    def test_noninteractive_diagnostics_are_allowed(self):
        self.installed()
        for action in ("doctor", "status", "verify"):
            with self.subTest(action=action), patch.object(launcher.os, "chdir"), patch.object(launcher.os, "execve") as execute:
                launcher.command(action)
                self.assertEqual(execute.call_args.args[1][-1], action)

    def test_unsupported_platform_is_refused(self):
        with patch.object(launcher.sys, "platform", "win32"):
            with self.assertRaisesRegex(RuntimeError, "macOS and Linux"):
                launcher.main()

    def test_main_validates_argument_count(self):
        with patch.object(launcher.sys, "argv", ["launcher.py"]):
            with self.assertRaises(ValueError):
                launcher.main()


if __name__ == "__main__":
    unittest.main()
