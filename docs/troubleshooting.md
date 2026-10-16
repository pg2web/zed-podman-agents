# Troubleshooting

First look at: `zpa status` in the project, and Zed's log
(`~/.local/share/zed/logs/Zed.log`, where agent stderr appears as
`agent stderr:`).

## "Loading…" never finishes

An old zpa that kept the lock file open blocked every later start. The current
version closes it for the container processes. If you still see it, check
`lslocks | grep .podman/lock`: a `conmon` process holding it means an old
container; `zpa rm` and start again.

## `incoming_transport_closed` or "Authentication required" on a new pi thread

With the nano-gpt provider the model list was fetched during session creation
and timed out, or the catalog was empty. See [nano-gpt.md](nano-gpt.md). A
quick check: the project's
`.podman/home/.pi/agent/models-store.json` should list models. Delete it and
start a new thread to rebuild it (needs the key).

## "Resource not found: <session id>" for a Claude thread

Zed is reopening a thread that has no saved session. This happens when the
thread never received a message, or `.podman/` was deleted. Open a new thread
(+ in the agent panel) and send a message; reloading works from then on, even
if the reply was "Authentication required".

## The terminal opened on the host, not in the container

`zpa-shell` runs in the container only when it finds a `.podman/container`
from the terminal's directory upwards. In a folder with no project it runs your
host shell. Start an agent thread in the project (or `zpa init`) first.

## A server in the container isn't reachable from the host

It must listen on `0.0.0.0`, not `127.0.0.1`. See [ports.md](ports.md).
Containers older than the port feature need `zpa upgrade`.

## Keys changed but the agent uses the old one

The agent process reads its environment at start. Start a new thread, or
`zpa stop` the project so everything restarts. A key in
`.podman/home/.pi/agent/auth.json` wins over the `env` key.

## The model list is out of date

See "Refreshing the model list" in [nano-gpt.md](nano-gpt.md).
