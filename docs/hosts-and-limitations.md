# Hosts and limitations

## Requirements

Linux, rootless podman, python3 and a **native** Zed. `install.sh` checks all
of that first and lists everything that is missing before it builds anything
(`./install.sh --check` only checks).

## Flatpak Zed

Not supported. A Flatpak Zed is sandboxed away from podman and from
`~/.local/bin`, and keeps its settings under `~/.var/app/...` instead of
`~/.config/zed/`. Install the native build:
`curl -f https://zed.dev/install.sh | sh`.

## Toolbox and distrobox

Run `install.sh` from a host terminal, not from inside a toolbox or
distrobox. Podman inside one is a separate instance with its own storage, so
the image it builds is not visible to the host's podman.

## Hosts with a symlinked `/home` (Fedora Silverblue, Kinoite)

Silverblue is not required. This section only matters on hosts where `/home`
is a symlink to `/var/home`: a project's real path is `/var/home/you/proj`
while Zed refers to it as `/home/you/proj`. zpa mounts the project at both
paths in the container, so every absolute path Zed sends (cwd, file
reads/writes, diffs, terminal commands) resolves.

No `rpm-ostree` layering is needed there: rootless podman, `python3`,
`flock` and `systemctl --user` are in the base image.

## Docker

Not supported. zpa relies on rootless podman features: `--userns=keep-id`
for file ownership, and pasta's port auto-forwarding.

## Limitations

* Zed starts custom agent servers in the first worktree root; that directory
  is the project. zpa refuses `/`, `$HOME` and its ancestors (`ZPA_FORCE=1`).
* Multi-root workspaces: only the first worktree is mounted.
* The container can reach the internet, and nothing on the host's loopback
  (see [ports.md](ports.md) for the other direction).
* `/home` symlinks are handled. A project reached through some *other*
  symlink (for example `~/work` → `/mnt/work`) is mounted only at its real
  path; if Zed refers to it by the symlinked path, open the project at its
  real path instead.
