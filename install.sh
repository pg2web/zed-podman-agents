#!/usr/bin/env bash
# Build the zed-agents image, install zpa, and register it in Zed.
#
#   ./install.sh [--no-zed] [--autostart] [--check]
#
#   --no-zed         don't edit ~/.config/zed/settings.json (prints the snippet)
#   --autostart      enable podman-restart.service so containers come back after reboot
#   --check          only run the preflight checks, change nothing
#
# Agents: ~/.config/zpa/agents.conf if it exists, else agents.conf from this
# directory (pi, claude, opencode). See docs/adding-agents.md.
# pi plugins to bake into the image: ~/.config/zpa/pi-plugins.conf if it exists,
# else pi-plugins.conf from this directory (none by default).
# Versions: PI_VERSION, PI_ACP_REF, CLAUDE_CODE_VERSION, CLAUDE_ACP_VERSION
# override the Containerfile defaults. Re-running rebuilds the image; then run
# `zpa upgrade` to move existing project containers onto it.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/zpa"
ZED_SETTINGS="${ZED_SETTINGS:-${XDG_CONFIG_HOME:-$HOME/.config}/zed/settings.json}"
IMAGE="${ZPA_IMAGE:-localhost/zed-agents:latest}"

PLUGINS="${XDG_CONFIG_HOME:-$HOME/.config}/zpa/pi-plugins.conf"
AGENTS="${XDG_CONFIG_HOME:-$HOME/.config}/zpa/agents.conf"
[[ -f "$AGENTS" ]] || AGENTS="$SRC/agents.conf"

zed=1 autostart=0 check=0
for a in "$@"; do
  case "$a" in
    --no-zed) zed=0 ;;
    --autostart) autostart=1 ;;
    --check) check=1 ;;
    *) sed -n '2,/^set -e/{/^#/s/^# \{0,1\}//p}' "$0"; exit 2 ;;
  esac
done

# Preflight: report every problem at once, before anything is built or changed.
problems=() warnings=()
[[ "$(uname -s)" == Linux ]] || problems+=("zpa needs Linux with rootless podman (this is $(uname -s))")
((BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 3))) ||
  problems+=("bash >= 4.3 is required (this is $BASH_VERSION)")
((EUID != 0)) || problems+=("run as your normal user, not root: zpa uses rootless podman")
if [[ -e /run/.containerenv || -e /.dockerenv || -n "${TOOLBOX_PATH:-}" || -n "${DISTROBOX_ENTER_PATH:-}" ]]; then
  problems+=("this shell is inside a container (toolbox/distrobox?): run install.sh from a host terminal")
fi
for c in podman python3 flock setsid sha256sum realpath; do
  command -v "$c" >/dev/null || problems+=("'$c' not found: install it with your distribution's package manager")
done
if command -v podman >/dev/null && ((EUID != 0)); then
  if rootless="$(podman info -f '{{.Host.Security.Rootless}}' 2>&1)"; then
    [[ "$rootless" == true ]] || problems+=("podman is not running rootless")
  else
    problems+=("'podman info' failed: ${rootless##*$'\n'}")
  fi
fi
if ((zed)) && [[ ! -f "$ZED_SETTINGS" ]]; then
  if [[ -d "$HOME/.var/app/dev.zed.Zed" ]]; then
    problems+=("only a Flatpak Zed was found; it is sandboxed away from podman. Install the native build (curl -f https://zed.dev/install.sh | sh), or use --no-zed")
  else
    warnings+=("$ZED_SETTINGS does not exist yet and will be created; is Zed installed? (--no-zed skips this)")
  fi
fi
for w in "${warnings[@]}"; do echo "warning: $w" >&2; done
if ((${#problems[@]})); then
  echo "install.sh: cannot install:" >&2
  for p in "${problems[@]}"; do echo "  - $p" >&2; done
  exit 1
fi
if ((check)); then echo "preflight ok"; exit 0; fi

echo "== building $IMAGE"
build_args=()
trap 'rm -f "$SRC/pi-plugins.local.conf" "$SRC/agents.local.conf"' EXIT
if [[ -f "$PLUGINS" ]]; then
  echo "   pi plugins from $PLUGINS"
  cp "$PLUGINS" "$SRC/pi-plugins.local.conf"
  build_args+=(--build-arg PI_PLUGINS_CONF=pi-plugins.local.conf)
fi
if [[ "$AGENTS" != "$SRC/agents.conf" ]]; then
  echo "   agents from $AGENTS"
  cp "$AGENTS" "$SRC/agents.local.conf"
  build_args+=(--build-arg AGENTS_CONF=agents.local.conf)
fi
for v in PI_VERSION PI_ACP_REF CLAUDE_CODE_VERSION CLAUDE_ACP_VERSION; do
  [[ -n "${!v:-}" ]] && build_args+=(--build-arg "$v=${!v}")
done
podman build -t "$IMAGE" "${build_args[@]}" -f "$SRC/Containerfile" "$SRC"

echo "== installing zpa to $BIN"
mkdir -p "$BIN" "$DATA"
install -m755 "$SRC/zpa" "$BIN/zpa"
ln -sfn zpa "$BIN/zpa-shell"
install -m755 "$SRC/zed-settings.py" "$DATA/zed-settings.py"
install -m644 "$AGENTS" "$DATA/agents.conf"

if ((zed)); then
  echo "== registering in Zed ($ZED_SETTINGS)"
  python3 "$DATA/zed-settings.py" install "$ZED_SETTINGS" "$BIN/zpa" "$DATA" "$DATA/agents.conf"
else
  echo "== add to $ZED_SETTINGS:"
  python3 "$DATA/zed-settings.py" snippet "$BIN/zpa" "$DATA/agents.conf"
fi

if ((autostart)); then
  systemctl --user enable --now podman-restart.service
fi

cur="$(podman image inspect -f '{{.Id}}' "$IMAGE")"
outdated=0
while read -r img; do
  [[ "${cur#sha256:}" == "${img#sha256:}"* ]] || outdated=$((outdated + 1))
done < <(podman ps -a --filter label=zpa.project --format '{{.ImageID}}')

cat <<EOF

== done
Restart Zed's agents (or Zed). In a project, start a thread with one of the
"(podman)" agents: that creates <project>/.podman/ and the container.
Zed terminals in such projects then open inside the container.
EOF
((outdated > 0)) && echo "$outdated existing container(s) use an older image: run 'zpa upgrade'."
case ":$PATH:" in *":$BIN:"*) ;; *) echo "note: $BIN is not on PATH (only needed for running zpa by hand)";; esac
