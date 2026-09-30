# Talos for Pinokio

Run Talos in Pinokio's terminal. Bring your own model; keep control of what it can do.

[Open the Pinokio listing](https://pinokio.co/apps/github-com-talos-kernel-talos-pinokio)
· [Talos website](https://talos-agent.ch/#install)
· [Talos source](https://github.com/talos-kernel/Talos)

Talos is a self-hosted AI assistant with a deterministic permission kernel:
**the model proposes; it never decides.** It can help with files and terminal tasks,
ask before protected actions, and record what actually ran.

This is a separate launcher, not a fork or a replacement for an existing Talos installation.
It installs the pinned **0.20.0-alpha.rc.5** candidate, including reliable live identity
and skill refresh on Linux. This is an opt-in release, not the website's default.
Talos is still **alpha**.

## Requirements

- Pinokio 8.2 or newer, on macOS or Linux. Windows is not supported by this launcher.
- An internet connection for installation and any remote model provider you choose.
- Your own model access: a configured provider, a supported authenticated CLI, or a local Ollama server.
- On Linux: working `bubblewrap` (`bwrap`) with unprivileged user namespaces. Install it through
  your distribution's package manager before installing Talos. The launcher probes isolation
  first and refuses if the kernel blocks it; it never enables unconfined execution or changes
  kernel/AppArmor settings. Linux installation CI uses Ubuntu 22.04.

The launcher has no subscription or gateway surcharge. Your model provider's own charges
and subscription terms still apply. It does not download a model or start Ollama for you.

## Start

1. Open the [Talos listing](https://pinokio.co/apps/github-com-talos-kernel-talos-pinokio)
   and download the launcher in Pinokio. Alternatively, download this repository in Pinokio.
2. Choose **Install Talos**. Installation checks the release signature and dependency hashes,
   then runs Talos' unit and adversarial tests. This can take several minutes.
3. Choose **Set up** and complete the interactive terminal wizard. For an existing CLI login,
   select that CLI: no key is copied. If you need to enter an API key, run the setup command
   below in your operating system's terminal instead of entering it inside Pinokio.
4. Choose **Open chat**. Type a request in the terminal, for example:
   `Explain how approvals work before changing any files.`

The setup wizard and chat require an interactive terminal. There is no separate web dashboard.
Type `exit` (without a slash) or use Pinokio's Stop control when finished. Stopping a running task
may interrupt it; inspect **Status** and the event log before restarting an interrupted task.

### API-key setup outside Pinokio

Pinokio can observe terminal input, including input hidden by a password prompt. Do not assume
that a hidden entry is excluded from its input tracking. For API-key setup, open your system
terminal in this launcher's folder and run:

```sh
app/.venv/bin/python launcher.py setup
```

The key is stored only in the local `app/talos.env` file, with owner-only permissions. Keep
that file and all Pinokio logs private. Do not add it to the repository or attach it to issues.

## You do not have to approve every step

When Talos asks, you can allow a single action or grant the offered permission for the
current task. Task-scoped approval applies only within that task and its stated scope;
it is not a permanent unrestricted grant. Deny an action when you do not want it to run.
Requests outside the granted scope still need a decision. See the
[operator documentation](https://talos-agent.ch/docs/) for the exact controls.

## Installation boundary

- Talos code, its Python environment, configuration, workspace and event log live under `app/`.
- Python used to launch the installer lives in `.bootstrap/`. A wrapper lives in `bin/` here,
  not in your global command directory.
- The upstream installer is pinned to a source commit and SHA-256 in `release.json`.
  It verifies the downloaded Talos archive with SHA-256 and Ed25519 before extracting it.
- Runtime and test dependencies are installed from the release's hashed lockfiles.
  The temporary signature verifier is also pinned and hash-locked, with binary wheels
  required before any archive is extracted.
  Installation must pass
  the upstream unit and adversarial tests before this launcher's installed marker is written.
- It does not copy model keys, routing, Telegram credentials, or permissions from another
  Talos instance. Existing CLI logins may be used only if you select that provider.
- It does not enable a system service, autostart, public port, tunnel or LAN sharing.
  Pinokio itself has its own network and logging settings; keep sharing disabled.
- Chat text and tool output can appear in Pinokio's terminal logs. Review and redact logs
  before sharing them. Never paste secrets into ordinary chat.

## Data, retries and updates

Repeating installation after success leaves configuration and history unchanged. An existing
or incomplete `app/` without a completed installation marker is never overwritten: the
launcher stops and asks you to inspect it. An interrupted install can also leave `.installing`;
check that no installation is running before recovering it manually.

There is intentionally no destructive Reset button and no automatic Talos core upgrade.
Updating this launcher does not silently replace the pinned Talos installation. Back up the
entire `app/` directory before an intentional migration or removal. Removing the Pinokio app
can remove its local configuration, workspace and history.

**Diagnostics**, **Status**, and **Verify event log** use the real Talos CLI. A valid event-log
chain proves internal log consistency, not that a model's answer is true or an action harmless.

## Source and license

[Talos source](https://github.com/talos-kernel/Talos) · [Website](https://talos-agent.ch/)

MIT. No endorsement or verified-listing status from Pinokio is implied.

## Launcher checks

```sh
python3 -m unittest discover -s tests -v
node --test tests/menu.test.cjs
```

These checks cover the launcher boundary. They do not replace real installation, terminal,
provider, and approval-flow tests on each claimed platform.
