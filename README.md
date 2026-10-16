# zed-podman-agents (zpa)

Run AI coding agents in [Zed](https://zed.dev) inside a rootless podman
container, one container per project.

The agent can only touch the project folder. Nothing from your home directory
is mounted, so your SSH keys, dotfiles and other projects stay out of its
reach. Zed's terminals open in the same container, so you and the agent see
the same tools and files.

**Agents included:** pi, Claude Code and opencode. Adding
another ACP agent is one line in a config file
([how](docs/adding-agents.md)).

## Requirements

* Linux with **rootless podman**
* python3
* **native Zed** (not the Flatpak build)

## Install

```bash
git clone https://github.com/pg2web/zed-podman-agents
cd zed-podman-agents
./install.sh
```

It checks the requirements first, builds the container image (a few
minutes), installs `~/.local/bin/zpa`, and registers the agents and the
terminal in Zed's settings (with a backup of your settings file).
`./install.sh --check` only checks; `--no-zed` leaves Zed's settings alone and
prints the snippet instead.

## Use

1. Open a **project folder** in Zed.
2. In the agent panel, start a thread with **Pi (podman)**,
   **Claude (podman)** or **opencode (podman)**.
3. The first thread creates the container and a `.podman/` folder in the
   project. That folder holds the agents' sessions and logins.
4. Terminals you open in that project now run in the container too.

Keys and logins: set them in the agent's `env` in Zed's settings, or log in
from a terminal. Anything you set for one agent is also available in the
project's terminals. Details: [docs/logins-and-keys.md](docs/logins-and-keys.md).

A server you start in the container is reachable from the host on
`localhost`, with no port configuration
([docs/ports.md](docs/ports.md)).

## Commands

```bash
zpa status      # this project's container
zpa ls          # all zpa containers
zpa stop        # stop it (state is kept)
zpa rm          # remove the container
zpa upgrade     # move containers to a rebuilt image
```

## Documentation

* [How it works](docs/how-it-works.md): containers, mounts, environment, terminals
* [Commands, updating, uninstall](docs/commands.md)
* [Logins and keys](docs/logins-and-keys.md)
* [Ports](docs/ports.md)
* [Adding another agent](docs/adding-agents.md)
* [pi plugins](docs/pi-plugins.md) and [nano-gpt](docs/nano-gpt.md)
* [Hosts and limitations](docs/hosts-and-limitations.md)
* [Troubleshooting](docs/troubleshooting.md)
* [Known issues](docs/known-issues.md)

Working on the project itself: [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE)
