# Known issues

Open problems that are understood but not fixed yet. Workarounds where there
are any.

## The first pi thread in a project can wait up to ~13 s

With the nano-gpt provider baked, the first pi start in a project downloads the
model list before pi answers (`nano-catalog.py`). That normally takes about
1 s, but the download has a 10 s timeout, so a slow network delays the first
thread by up to that much. Later threads don't download anything.

Possible fixes: a shorter timeout, or downloading in the background and
starting the first thread with the one-model stub.

## Model list doesn't refresh on its own

The nano-gpt model list is fetched once per project and then served from the
cache. New models appear only after deleting
`<project>/.podman/home/.pi/agent/models-store.json` and starting a new pi
thread ([nano-gpt.md](nano-gpt.md)). A `zpa` command to refresh it would be
nicer.

## A new terminal sometimes opened on the host (not reproduced)

Once reported: right after starting a new Claude thread, the next terminal
opened on the host; closing it and opening another one landed in the
container. It could not be reproduced since. A terminal runs on the host
whenever no `.podman/container` is found from its directory upwards, so a
terminal started in a different directory, or before the project's
`.podman/` existed, would behave like this.

## "Resource not found" when reloading an empty Claude thread

Zed keeps reopening a thread that has no saved session (it never got a
message, or `.podman/` was deleted). This is how the Claude ACP adapter
behaves, also outside zpa. Workaround: open a new thread and send a message
([troubleshooting.md](troubleshooting.md)).

## Loopback-only servers are not forwarded

A server in the container that listens on `127.0.0.1` gets a host port, but
connections to it are reset. Servers must listen on `0.0.0.0`
([ports.md](ports.md)).

## Port clashes are silent

If two project containers (or the host) want the same port, the second one
doesn't get it and nothing says so.

## Claude credential files are untested

Copying a Claude Code `.credentials.json` into a project should work but was
not tested; an OAuth login copied to several places may sign the others out on
refresh ([logins-and-keys.md](logins-and-keys.md)).
