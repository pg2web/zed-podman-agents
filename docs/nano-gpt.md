# nano-gpt

If `pi-nano-gpt-provider` is in your plugin list, the build does two extra
things for it (and nothing otherwise):

* **Patch**: upstream re-downloads its model catalog whenever the cached copy
  is older than 5 minutes, and does so while a session is being created. Over
  ACP that makes Zed give up on the new thread (`incoming_transport_closed`)
  or report "Authentication required". `patch-nano-gpt-provider.py` makes the
  provider use the cached catalog whenever there is one.
* **Catalog from your key**: the image carries no model list, only a
  one-model stub. When a pi agent starts in a project whose catalog is still
  the stub, `nano-catalog.py` downloads the list for the project's key
  (`auth.json` first, else `NANOGPT_API_KEY`) and stores it. With no key the
  stub stays and the next start tries again.

Set `NANOGPT_API_KEY` in the *Pi (podman)* agent's `env` in Zed.

## Refreshing the model list

The list only changes when you refresh it. To re-fetch it (for example after
changing the key), delete
`<project>/.podman/home/.pi/agent/models-store.json` and start a new pi
thread. The stub is not restored; `nano-catalog.py` writes the new list.

`pi update --models --force` does not do this: the `pi` wrapper skips baked
plugins for management subcommands.
