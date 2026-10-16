# Logins and keys

## Per agent

* **Claude**: set `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` in the
  agent's `env` in Zed, or run `claude` in a project terminal and `/login`
  (stored in `.podman/home/.claude`).
* **pi**: provider keys in the agent's `env`, or `pi` then `/login` in a
  terminal (stored in `.podman/home/.pi/agent`).
* **opencode**: works without a login on its free default models. Provider
  keys go in the agent's `env`, or run `opencode auth login` in a terminal
  (stored in `.podman/home/.local/share/opencode`).

## Keys in terminals

Every variable you set in the `env` of any zpa agent in Zed (Pi, Claude,
opencode, …) is also set in the project's Zed terminals. So `claude`, `pi`
and `opencode` there find their keys without a second copy.

* The settings are read at each terminal start, so a changed key applies to
  the next terminal you open.
* If two agents set the same name differently, the first one wins, with a
  warning.
* A variable already in the terminal's own environment (for example Zed's
  `terminal.env`) takes priority.
* Host-session names (`PATH`, `HOME`, …) are never forwarded.
* Commands an agent runs in a terminal see all of these keys too.
* A set `ANTHROPIC_API_KEY` makes `claude` use that key instead of a login
  saved in the project.

## Credential files

You can also drop credential files straight into a project; the agents read
them on the next thread:

* **pi**: `<project>/.podman/home/.pi/agent/auth.json`, one entry per
  provider, e.g. `{"nano-gpt": {"type": "api_key", "key": "sk-..."}}`. An
  entry here wins over the env key.
* **Claude**: `<project>/.podman/home/.claude/.credentials.json`, the file a
  Linux Claude Code login writes to `~/.claude/`. It holds an OAuth login
  rather than a static key: if the same login is copied to several places, a
  token refresh in one may sign the others out. For several projects prefer
  `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` in the agent's `env`.

Keep these files at mode 600. `.podman/` is git-ignored, so they are not
committed with the project.
