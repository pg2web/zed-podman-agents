# Ports

Containers use pasta with port auto-forwarding: whatever a process in the
container starts listening on (TCP or UDP) appears on the **host's loopback**
a moment later and disappears when the process stops.

Start a dev server or proxy in a Zed terminal, then open
`http://localhost:3000` (or point a client at `127.0.0.1:8888`) on the host.
There is no port list and no restart.

## Things to know

* Servers must listen on `0.0.0.0` (`--host 0.0.0.0`), not the default
  `127.0.0.1` many dev servers use: loopback-only listeners are not
  forwarded.
* Only the host's loopback is opened, so nothing is reachable from your
  network.
* If two projects (or the host) use the same port, the first one keeps it.
* The container sees clients with an internal source address, not the real
  one.
* Host services on `127.0.0.1` are not reachable from the container.
* Containers created before this feature get it on `zpa upgrade`;
  `zpa status` says which.

## Test containers that need the project's network

Start another container with `--network container:<zpa container name>`
(`zpa ls` shows the names). It then shares the project's `localhost`, so a
browser or test runner in it can reach the app at `localhost:<port>`, even if
the app listens on loopback only. It stops being valid if the project
container is recreated.
