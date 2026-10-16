# Commands

| | |
|---|---|
| `zpa init [dir]` | opt in and start the container |
| `zpa status [dir]` | container, state, image freshness, port forwarding, running sessions |
| `zpa ls` | all zpa containers |
| `zpa shell` | shell in the current project's container |
| `zpa stop [dir]` | stop (state kept) |
| `zpa rm [--state] [dir]` | remove the container (`--state`: also `.podman/`, after a prompt) |
| `zpa upgrade [dir]` | recreate containers whose image or network setup is outdated |

`zpa acp <kind>` and `zpa-shell` are what Zed runs; you don't call them by
hand except for testing (see [adding-agents.md](adding-agents.md)).

## Updating agent versions

Versions are pinned in `Containerfile` (`PI_VERSION`, `PI_ACP_REF`,
`CLAUDE_CODE_VERSION`, `CLAUDE_ACP_VERSION`) and in `agents.conf` for the
other agents. Edit them or pass them as environment variables:

```bash
CLAUDE_ACP_VERSION=0.90.0 ./install.sh && zpa upgrade
```

`zpa upgrade` recreates the containers on the new image and kills the agents
and terminals running in them. Project state in `.podman/` is not touched.

## Uninstall

```bash
./uninstall.sh            # keeps containers, the image and project state
./uninstall.sh --purge    # also removes all zpa containers and the image
```

Project `.podman/` folders (sessions, logins) are never deleted by the
uninstaller; remove them yourself.
