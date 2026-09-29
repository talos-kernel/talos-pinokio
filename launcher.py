"""A small launcher around Talos' pinned, signed-release installer and real CLI."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
RELEASE = json.loads((ROOT / "release.json").read_text())
MARKER = APP / ".pinokio-installed.json"


def clean_environment():
    # Do not silently inherit another agent's credentials, policy or model routing.
    keys = ("HOME", "PATH", "LANG", "LC_ALL", "TERM", "TMPDIR", "USER", "LOGNAME",
            "SHELL", "SYSTEMROOT", "SSL_CERT_FILE", "SSL_CERT_DIR")
    env = {key:os.environ[key] for key in keys if key in os.environ}
    env.update({"PYTHONUNBUFFERED":"1", "PYTHONDONTWRITEBYTECODE":"1",
                "TALOS_SECRETS_ENV":str(APP / "talos.env")})
    return env


def install():
    if APP.is_symlink():
        raise RuntimeError("The app directory must not be a symlink. Nothing was changed.")
    if MARKER.exists():
        installed = json.loads(MARKER.read_text())
        if installed.get("version") != RELEASE["version"]:
            raise RuntimeError("Different version installed. Automatic core upgrades are not enabled.")
        if not (APP / ".venv/bin/python").is_file():
            raise RuntimeError("Installation is incomplete. Existing data was not changed.")
        print("Already installed. Configuration, history and workspace kept unchanged.")
        return
    if APP.exists() or APP.is_symlink():
        raise RuntimeError("An existing or incomplete app directory was found. Nothing was overwritten.")
    # Exclusive lock prevents simultaneous installs; no broad deletion/reset operation.
    with (ROOT / ".installing").open("x"):
        try:
            request = urllib.request.Request(RELEASE["installer_url"],headers={"User-Agent":"Talos-Pinokio"})
            with urllib.request.urlopen(request,timeout=45) as response:
                data = response.read(2_000_001)
            if hashlib.sha256(data).hexdigest() != RELEASE["installer_sha256"]:
                raise RuntimeError("Installer hash mismatch. Nothing was executed.")
            downloads = ROOT / ".downloads"
            downloads.mkdir(exist_ok=True)
            installer = downloads / "install.sh"
            installer.write_bytes(data)
            env = clean_environment()
            env.update({"TALOS_PREFIX":str(APP), "TALOS_BIN_DIR":str(ROOT / "bin"),
                        "TALOS_BASE":"https://talos-agent.ch", "NO_COLOR":"1"})
            subprocess.run(["bash",str(installer)],cwd=ROOT,env=env,check=True)
            # The upstream installer checks SHA-256 and Ed25519 before extraction,
            # installs hashed locks, and runs the full unit and adversarial suites.
            MARKER.write_text(json.dumps({"version":RELEASE["version"],
                                          "installer_sha256":RELEASE["installer_sha256"]})+"\n")
            print("Installation verified. Choose Set up, then Open chat. No agent was started.")
        finally:
            (ROOT / ".installing").unlink()


def command(action):
    if APP.is_symlink():
        raise RuntimeError("The app directory must not be a symlink. Nothing started.")
    if not MARKER.is_file():
        raise RuntimeError("Install Talos first.")
    commands = {"setup":["setup","terminal","--out",str(APP / "talos.env")],
                "chat":["chat"], "doctor":["doctor"], "status":["status"],
                "verify":["verify"]}
    if action not in commands:
        raise ValueError("Unknown launcher action")
    if action in {"setup","chat"} and not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("Set up and chat require an interactive terminal. Nothing started.")
    if action == "setup":
        print("Use an existing CLI login here. For API-key entry, run this setup in your system terminal; "
              "Pinokio can track even hidden input. See README.md.", flush=True)
    python = APP / ".venv/bin/python"
    os.chdir(APP)
    os.execve(str(python),[str(python),"-m","talos",*commands[action]],clean_environment())


def main():
    if sys.platform not in {"darwin","linux"}:
        raise RuntimeError("This launcher currently supports macOS and Linux only.")
    if len(sys.argv)!=2:
        raise ValueError("Choose install, setup, chat, doctor, status or verify")
    if sys.argv[1]=="install":
        install()
    else:
        command(sys.argv[1])


if __name__=="__main__":
    try:
        main()
    except (RuntimeError,ValueError,OSError,subprocess.CalledProcessError) as error:
        print(f"Stopped: {error}",file=sys.stderr)
        raise SystemExit(1)
