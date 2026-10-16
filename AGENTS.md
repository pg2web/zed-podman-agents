# zpa — Zed Podman Agents

Runs ACP agents (pi, Claude Code, opencode; list in `agents.conf`), and Zed's
terminals, inside one rootless podman container per project.

`README.md` is the short introduction; the full user documentation is in
`docs/` (how it works, commands, logins, ports, plugins, hosts, troubleshooting). This file is what an agent working on the repo needs
on top of that.

---

## 1. Layout

| File | Role |
|------|------|
| `zpa` | Host CLI, installed as `~/.local/bin/zpa` (+ `zpa-shell` symlink). Zed entry points: `zpa acp <kind>`, `zpa-shell`. |
| `zpa-exec` | In-container helper (`/usr/local/bin/zpa-exec`): `run <id> <cmd>`, `kill <id>`, `agent <kind>`, `agents`, `setup`. |
| `agents.conf` | The agents: `kind \| Zed name \| ACP command \| npm packages`. Read by the Containerfile (installs packages), `zpa-exec agent`, host `zpa` (rejects unknown kinds, via the copy in `~/.local/share/zpa/`) and `zed-settings.py`. `~/.config/zpa/agents.conf` replaces it when present. User guide: `docs/adding-agents.md`. |
| `zpa-pi` | In-container `pi` wrapper: adds `-e <dir>` for every baked plugin; `zpa-pi bake` runs at image build. |
| `Containerfile` | Image `localhost/zed-agents:latest` (node 22, pi, claude-code, claude-agent-acp, pi-acp at a pinned ref, plus the npm packages in `agents.conf`). |
| `pi-plugins.conf` | Default list of pi plugins baked into the image: none. `install.sh` uses `~/.config/zpa/pi-plugins.conf` instead when it exists. |
| `patch-nano-gpt-provider.py` | Build-time patch of the baked nano-gpt provider (see §4); a no-op when that provider is not in the plugin list. |
| `nano-gpt-models.seed.json` | One-model stub catalog (`checkedAt: 1`), copied into each project at `zpa-exec setup` (see §4); dropped from the image when the provider is not baked. |
| `nano-catalog.py` | Run by `zpa-exec agent pi`: replaces the stub with the catalog for the project's key. Mirrors the provider's `mapNanoGptModel`. |
| `install.sh` / `uninstall.sh` / `zed-settings.py` | Preflight checks, build image, install `zpa`, edit `~/.config/zed/settings.json`. The Zed agent names written are recorded in `~/.local/share/zpa/zed-agents.json` so dropped agents get removed. |

## 2. Model

* One container per **project path** (`zpa-<dir>-<sha256(path)[0:8]>`), shared
  by all agents and terminals. Two containers only means two project folders.
* `<project>/.podman/container` is the opt-in marker; `<project>/.podman/home`
  is the container's `HOME` (`/home/node`): agent sessions, logins, pi state.
  `.podman/lock` serializes create/start.
* Opt-in is automatic: the first `zpa acp` in a folder with no
  `.podman/container` (in it or an ancestor) makes that folder a project
  (`zpa init [dir]` does the same by hand). Only `/` and `$HOME` are refused.
  This was briefly made explicit and then reverted: Zed is a GUI and a
  required CLI step was unwanted. `zpa-shell` never opts a folder
  in; outside a project it runs the host shell.
* Mounts: the project at its own host path (and its `/home/...` alias when
  `/home` is a symlink, as on Fedora Silverblue), plus `.podman/home`. Nothing from
  the host home is mounted, so host `~/.claude` / `~/.pi` (skills, commands,
  logins) are not visible in the container. Project-level `.claude/` and
  `.pi/` are.
* `zpa acp <kind>` = check kind → `find_project` → `ensure` (create/start under flock) →
  `env_flags` → `watch_session` → `exec podman exec -i … zpa-exec run <id>
  zpa-exec agent <kind>`. zpa is a plain stdio pipe: slash commands and
  everything else the adapters emit reach Zed unchanged.
* `podman exec` does not kill the in-container process when its client dies,
  so a detached host watcher calls `zpa-exec kill <id>` once the Zed-side
  process is gone. Session records live in `/tmp/zpa-sessions` in the container.

## 3. Working on it

* Any Linux with rootless podman will do; Fedora Silverblue is only the
  maintainer's machine. **`pi`, `claude` and the other agents are not needed on
  the host** (and the point is to keep them off it): test through the
  containers (`zpa acp …`, `zpa shell`, `podman exec <name> …`).
* Script-only change to `zpa`: `install -m755 zpa ~/.local/bin/zpa`.
  Anything in the image (`zpa-exec`, `zpa-pi`, `Containerfile`, plugins, patch,
  seed): `./install.sh --no-zed && zpa upgrade`. `--no-zed` leaves the
  user's Zed settings alone; `zpa upgrade` recreates containers and kills the
  agents/terminals attached to them.
* A change to how containers are **created** (mounts, flags) only reaches
  existing containers when they are recreated (`zpa rm <dir>` then `zpa init
  <dir>`); `zpa upgrade` only recreates containers whose image is outdated.
* Recreating a container is safe (state is in `.podman/`). **Ask before
  deleting any project's `.podman/`** — it holds sessions and logins.
* Driving an agent by hand: send `initialize`, then `session/new`, and **keep
  stdin open** (`( printf …; sleep N ) | zpa acp pi`). Both adapters shut down
  on stdin EOF, so `printf … | zpa acp …` shows only the first reply.
* Don't run load tests against a container the user has live Zed threads in:
  pi processes share `.podman/home/.pi/agent`.
* Zed log: `~/.local/share/zed/logs/Zed.log` (adapter stderr appears as
  `agent stderr:`; pi-acp logs almost nothing).

## 4. Gotchas (each one was a real bug)

* **Never let a long-lived child inherit the lock fd.** `ensure` holds
  `.podman/lock` as a bash fd. `podman run` / `podman start` fork `conmon`,
  which lives as long as the container; if it inherits the fd it holds the
  flock forever and every later `zpa` call blocks in `ensure` (Zed shows
  "Loading…" forever). Every podman command run under the lock that can spawn
  conmon carries `{lock}>&-`. Check with `lslocks | grep .podman/lock` and
  `ls -l /proc/<conmon pid>/fd`.
* **The nano-gpt catalog cannot be fetched during `session/new`.** Upstream
  re-fetches the model list whenever `models-store.json` is older than 5
  minutes; on the ACP path that happens inside `session/new` and shows up in
  Zed as `incoming_transport_closed` or "Authentication required". An *empty*
  catalog is worse: pi has no model, never resolves the key, never fetches
  ("No models available"). So: `patch-nano-gpt-provider.py` makes the provider
  serve any cache; the image holds only a one-model stub (`checkedAt: 1`, not
  `0` — pi treats 0 as "no snapshot"); `nano-catalog.py` fills the real list
  from the project's key before pi starts. The image must never carry a
  catalog taken from someone's account. To refresh: delete
  `<project>/.podman/home/.pi/agent/models-store.json` and start a thread
  (`pi update --models --force` does nothing: the `pi` wrapper skips baked
  plugins for it). The patch script fails the build if its anchor is missing —
  re-check it when bumping the provider.
* **The `pi` wrapper skips baked plugins for management subcommands**
  (`install`, `update`, `list`, `auth`, `config`, `mcp`, …), so `pi auth check`
  and `pi list` don't see the baked provider. That is not a sign the provider
  is missing.
* **nano-gpt auth** is the `NANOGPT_API_KEY` env var set in the *Pi (podman)*
  agent `env` in Zed (or `/login nano-gpt` in a project terminal, which wins).
* **Terminal env**: `zpa shell` calls `export_agent_env`, which runs
  `zed-settings.py env` to merge the `env` of every registered agent in Zed's
  settings.json into the terminal (first agent wins; the process's own env wins
  over both; `ENV_DENY` still applies). This is deliberate: one container, so
  every agent's keys are visible in terminals. Agents themselves only get their
  own `env`.
* Don't pass `--network slirp4netns`; the rootless backend here is pasta.
  Containers are created with `NET_SPEC` (`pasta:-t,127.0.0.1/auto,-u,127.0.0.1/auto`),
  stored in the `zpa.net` label; `zpa upgrade` recreates containers whose label
  differs (it also takes a project dir, to scope it). Auto-forwarding opens
  host *loopback* ports as processes listen on `0.0.0.0` in the container;
  loopback-only listeners are not forwarded. Never use plain `-t auto`: it
  binds every host interface. A bridge/user network can't be combined with
  pasta, so a named network would cost the auto-forwarding.
* `--security-opt label=disable` is set, so never add `:z`/`:Z` to binds.

## 5. Zed settings

`install.sh` writes one entry per `agents.conf` line (command paths are
absolute in the real file); keys such as `NANOGPT_API_KEY` go in the agent's
`env`:

```jsonc
"agent_servers": {
  "Pi (podman)":       { "type": "custom", "command": "~/.local/bin/zpa", "args": ["acp", "pi"],       "env": {} },
  "Claude (podman)":   { "type": "custom", "command": "~/.local/bin/zpa", "args": ["acp", "claude"],   "env": {} },
  "opencode (podman)": { "type": "custom", "command": "~/.local/bin/zpa", "args": ["acp", "opencode"], "env": {} }
},
"terminal": { "shell": { "with_arguments": { "program": "~/.local/bin/zpa-shell", "args": [] } } }
```
