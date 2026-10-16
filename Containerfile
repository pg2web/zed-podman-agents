# zed-agents — one image for the ACP agents in agents.conf and Zed terminals.
# Built by install.sh:  podman build -t localhost/zed-agents:latest .
# Bump a version with:  PI_VERSION=x.y.z ./install.sh   (then `zpa upgrade`)
FROM docker.io/library/node:22-bookworm-slim

ARG PI_VERSION=1.1.0
ARG PI_ACP_REF=5ec3b616e7ef70753eeea1224d5d01578a8d2c5f
ARG CLAUDE_CODE_VERSION=2.1.296
ARG CLAUDE_ACP_VERSION=0.89.1
# plugin list to bake; install.sh points this at the user's own list if there is one
ARG PI_PLUGINS_CONF=pi-plugins.conf
# agent list; install.sh points this at ~/.config/zpa/agents.conf if there is one
ARG AGENTS_CONF=agents.conf

RUN apt-get update && apt-get install -y --no-install-recommends \
      git ripgrep fd-find fzf jq curl ca-certificates bash python3 procps less openssh-client \
 && ln -s /usr/bin/fdfind /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g \
      @earendil-works/pi-coding-agent@${PI_VERSION} \
      @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} \
      @agentclientprotocol/claude-agent-acp@${CLAUDE_ACP_VERSION} \
 && npm cache clean --force

# pi ACP adapter (not published to npm)
RUN git clone https://github.com/regadas/pi-acp /opt/pi-acp \
 && cd /opt/pi-acp && git checkout ${PI_ACP_REF} \
 && npm ci && npm run build && npm prune --omit=dev && npm cache clean --force

COPY zpa-exec zpa-pi /usr/local/bin/

# Extra agents from agents.conf: the npm packages column (`-` = none)
COPY ${AGENTS_CONF} /opt/zpa/agents.conf
RUN pkgs="$(awk -F'|' '/^[[:space:]]*(#|$)/ { next } $4 !~ /^[ \t]*-?[ \t]*$/ { print $4 }' /opt/zpa/agents.conf)" \
 && if [ -n "$pkgs" ]; then npm install -g $pkgs && npm cache clean --force; fi

# pi plugins from pi-plugins.conf, installed into the image. `pi` becomes a
# wrapper that loads them (-e) on top of the project's own `pi install`s.
COPY ${PI_PLUGINS_CONF} /opt/zpa/pi-plugins.conf
COPY patch-nano-gpt-provider.py /opt/zpa/patch-nano-gpt-provider.py
# Only used when pi-nano-gpt-provider is baked (otherwise removed below): a
# one-model stub catalog copied into each project at setup, and the script that
# replaces it with the account's real catalog (from its key) at agent start.
COPY nano-gpt-models.seed.json nano-catalog.py /opt/zpa/
RUN mv /usr/local/bin/pi /usr/local/bin/pi-real \
 && ln -s zpa-pi /usr/local/bin/pi \
 && zpa-pi bake /opt/zpa/pi-plugins.conf /opt/zpa/pi-plugins \
 && python3 /opt/zpa/patch-nano-gpt-provider.py \
 && { grep -q '^npm:pi-nano-gpt-provider|' /opt/zpa/pi-plugins/plugins.list \
      || rm -f /opt/zpa/nano-gpt-models.seed.json /opt/zpa/nano-catalog.py; } \
 && rm -rf /tmp/jiti \
 && npm cache clean --force

# Global npm dir is root-owned; updates happen by rebuilding the image.
ENV LANG=C.UTF-8 DISABLE_AUTOUPDATER=1

# uid 1000; the host user is mapped onto it with --userns=keep-id:uid=1000,gid=1000.
# HOME (/home/node) is bind-mounted from <project>/.podman/home at runtime.
USER node
WORKDIR /home/node
CMD ["sleep", "infinity"]
