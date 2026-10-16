#!/usr/bin/env bash
# Remove zpa from Zed and ~/.local/bin.
#
#   ./uninstall.sh [--purge]
#
# By default containers, the image and every project's .podman/ are kept.
# --purge also removes all zpa containers and the image. Project .podman/
# dirs (agent sessions, logins) are never deleted here: rm -rf them yourself.
set -euo pipefail

BIN="$HOME/.local/bin"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/zpa"
ZED_SETTINGS="${ZED_SETTINGS:-${XDG_CONFIG_HOME:-$HOME/.config}/zed/settings.json}"
IMAGE="${ZPA_IMAGE:-localhost/zed-agents:latest}"
SRC="$(cd "$(dirname "$0")" && pwd)"

purge=0
case "${1:-}" in
  "") ;;
  --purge) purge=1 ;;
  *) sed -n '2,/^set -e/{/^#/s/^# \{0,1\}//p}' "$0"; exit 2 ;;
esac

if [[ -f "$ZED_SETTINGS" ]]; then
  echo "== removing zpa from $ZED_SETTINGS"
  helper="$DATA/zed-settings.py"
  [[ -f "$helper" ]] || helper="$SRC/zed-settings.py"
  python3 "$helper" uninstall "$ZED_SETTINGS" "$DATA"
fi

if command -v podman >/dev/null; then
  projects="$(podman ps -a --filter label=zpa.project --format '{{index .Labels "zpa.project"}}')"
  if ((purge)); then
    echo "== removing containers and image"
    podman ps -a --filter label=zpa.project --format '{{.Names}}' | xargs -r podman rm -f
    podman rmi "$IMAGE" 2>/dev/null || true
  elif [[ -n "$projects" ]]; then
    echo "== kept containers (zpa rm / podman rm -f), image $IMAGE (podman rmi)"
  fi
  if [[ -n "$projects" ]]; then
    echo "project state kept in:"
    sed 's|$|/.podman|; s|^|  |' <<<"$projects"
  fi
fi

rm -f "$BIN/zpa" "$BIN/zpa-shell"
rm -rf "$DATA"
echo "== done; restart Zed"
