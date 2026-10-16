# Adding an agent

zpa can run any agent that speaks **ACP over stdio** (JSON-RPC, one message per
line on stdin/stdout). The agents live in one table, `agents.conf`. Adding one
is a line in that table and a rebuild.

## 1. Find the agent's ACP command

Pi, Claude Code and opencode are already in the image; this is for any other
agent. Check its docs for "ACP" or "Agent Client Protocol". There are two
cases:

* **The agent speaks ACP itself**, usually through a subcommand (opencode:
  `opencode acp`). Install the agent; its command is the ACP command.
* **It needs an adapter**, a separate program that translates between ACP and
  the agent (Claude Code is driven through `claude-agent-acp`). Install the
  agent *and* the adapter; the adapter's command is the ACP command.

Either way, both the agent and any adapter must end up in the image: list
their npm packages in step 2, or see "Agents that aren't on npm" at the end.

## 2. Add a line to your agents.conf

Don't edit the repo's `agents.conf`. Copy it once and edit the copy, which then
replaces it:

```bash
mkdir -p ~/.config/zpa
cp agents.conf ~/.config/zpa/agents.conf
```

Each line has four columns separated by `|`:

```
# kind     | Zed name           | ACP command        | npm packages to install
opencode   | opencode (podman)  | opencode acp       | opencode-ai@1.19.0
```

* **kind**: short id (`a-z`, `0-9`, `-`). Zed runs `zpa acp <kind>`.
* **Zed name**: the name shown in Zed's agent menu.
* **ACP command**: run in the project's container, in the project folder.
  Words are split on spaces (no quoting). Leading `VAR=value` words set
  environment variables, for example `FOO=1 my-agent --acp`.
* **npm packages**: installed with `npm install -g` when the image is built.
  Pin a version (`pkg@1.2.3`) so rebuilds are reproducible. Use `-` if
  nothing needs installing.

To remove an agent, delete its line. The next install also removes it from Zed.

## 3. Rebuild

```bash
./install.sh && zpa upgrade
```

`install.sh` builds the image with your list, and adds every agent to
`agent_servers` in Zed's settings (any `env` you set there is kept).
`zpa upgrade` moves existing project containers to the new image; that stops
agents and terminals running in them.

Restart Zed's agents (or Zed) and start a new thread with the new agent.

## 4. Logins and API keys

The container's `HOME` is `<project>/.podman/home`. Whatever the agent saves in
`~` (logins, sessions, settings) ends up there, separately for each project.
Nothing from your host home is visible.

* **API key**: put it in the agent's `env` in Zed's settings, for example
  `"env": { "OPENAI_API_KEY": "sk-..." }`. It reaches the agent on the next
  thread.
* **Interactive login**: open a Zed terminal in the project (it runs inside
  the container) and run the agent's login command, e.g. `opencode auth login`.

## 5. Test it by hand

From a project folder, send `initialize` and `session/new`, and keep stdin
open (agents exit when stdin closes):

```bash
cd ~/some-project
( printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientCapabilities":{}}}' \
  "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"session/new\",\"params\":{\"cwd\":\"$PWD\",\"mcpServers\":[]}}"
  sleep 20 ) | zpa acp opencode
```

You should see two replies, `"id":1` and `"id":2` (with a `sessionId`).
Problems:

* `unknown agent '…'`: the kind is not in the installed list; re-run
  `./install.sh`.
* `zpa-exec: unknown agent`: the image is older than your list; re-run
  `./install.sh && zpa upgrade`.
* `exec: …: not found`: the command or its package is wrong. Check inside the
  container with `zpa shell`, then `which <command>`.

## Things that break agents in Zed

* **Network calls while creating a session.** Zed gives up on a slow
  `session/new` (the thread shows `incoming_transport_closed`). If the agent
  fetches something there (model lists, updates), make it use a cache or turn
  it off.
* **Anything else on stdout.** Only protocol messages may go to stdout; logs
  must go to stderr. A banner or update notice on stdout breaks the
  connection.
* **Self-updates.** The image is read-only for the agent user. Turn off
  auto-update and bump the pinned version instead.
* **State outside `$HOME`.** Anything written elsewhere (except the project)
  is lost when the container is recreated.

## Agents that aren't on npm

The packages column only handles npm. For anything else (a Go or Rust binary,
a Python tool, a git checkout), add a `RUN` step to the `Containerfile`, the
way `pi-acp` is installed there, and put `-` in the packages column.
