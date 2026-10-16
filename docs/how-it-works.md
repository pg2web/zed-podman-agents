# How it works

zpa runs one rootless podman container per project. Zed's agents and terminals
for that project all run in it.

```
project/
  .podman/
    container    # container name (zpa-<dir>-<hash>): the opt-in marker
    home/        # the container's HOME (/home/node): .claude/, .claude.json, .pi/, shell history
    lock         # serializes container creation
    .gitignore   # "*"
```

## Opting in

Start a thread with one of the "(podman)" agents in a project, or run
`zpa init` in it. Either creates `.podman/` and the container. The whole
folder Zed has open becomes the project and is mounted read-write, so open the
project folder itself rather than a broad parent such as `~/Documents`.

zpa refuses `/`, `$HOME` and the ancestors of `$HOME` (`ZPA_FORCE=1` overrides
that).

Opt out with `zpa rm --state`, or `zpa rm` and delete `.podman/`.

## The container

```
podman run -d --init --restart=always --userns=keep-id:uid=1000,gid=1000 \
  --security-opt label=disable --network pasta:… \
  -v $P:$P:rslave -v $P/.podman/home:/home/node … sleep infinity
```

It lives until you remove it. zpa starts it when it is stopped (after a
reboot, unless `install.sh --autostart` already brought it back).

## Mounts

Only the project is mounted, at its own host path. ACP messages carry absolute
paths (cwd, files, diffs, terminal commands) that must mean the same thing to
Zed and to the agent.

Agent state goes to `HOME`, which is `.podman/home`. Nothing from your host
home is visible, and nothing is written outside the project. Files are owned
by your host user (`--userns=keep-id`).

## Agents

`zpa acp <kind>` ensures the container exists and runs, then starts
`podman exec -i … zpa-exec agent <kind>` with stdio attached to Zed. The
command run is the kind's line in `agents.conf` (baked into the image as
`/opt/zpa/agents.conf`). Agents and adapters are in the image; nothing is
downloaded or mounted at runtime.

zpa is a plain stdio pipe, so slash commands and everything else the adapters
send reach Zed unchanged.

## Environment

The environment is forwarded at each agent or terminal start
(`podman exec -e NAME`), so values never appear in `ps` or `podman inspect`.
Everything is forwarded except host-session variables (`PATH`, `HOME`,
`XDG_*`, `DBUS_*`, `ZED_*`, `WAYLAND_*`, `SSH_*`, `LANG`/`LC_*`, …; the full
list is at the top of `zpa`). Keys you add in an agent's `env` in Zed arrive on
the next agent start. Tune with `ZPA_ENV_DENY='REGEX'` and
`ZPA_ENV_ALLOW='REGEX'`.

See [logins-and-keys.md](logins-and-keys.md) for how keys reach terminals.

## Terminals

`zpa-shell` walks up from the terminal's directory to a `.podman/container`.
If it finds one it runs `bash -l` (or `bash <args>` for tasks and agent
commands) in the container; otherwise it runs your host shell. If the
container can't be started it prints an error rather than falling back to the
host.

## Cleanup

`podman exec` doesn't stop the in-container process when its client is killed.
So every agent and shell runs under `zpa-exec run <id>`, and a detached host
watcher calls `zpa-exec kill <id>` when the Zed-side process is gone.

## Copied or moved projects

The container's `zpa.project` label must match the project path. If it
doesn't (you copied the folder, or moved it), zpa creates a new container for
the new path. State in `.podman/home` is reused.

If `.podman/` itself was replaced while a container was running (for example
trashed and recreated), the container would still hold the old directory, so
zpa notices the changed device/inode and recreates the container.
