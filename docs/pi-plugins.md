# pi plugins

## Baked into the image (all projects)

None by default. List yours in `~/.config/zpa/pi-plugins.conf` (the format is
described in `pi-plugins.conf` in this repo), then:

```bash
./install.sh && zpa upgrade
```

`install.sh` runs `pi install` for each plugin at image build, into
`/opt/zpa/pi-plugins` (`zpa-pi bake`). In the image, `pi` is a wrapper
(`zpa-pi`) that adds `-e <dir>` for each baked plugin. They load for ACP
threads and for terminal `pi` alike, with no download or settings change at
runtime.

## Per project

Run `pi install <spec>` in a project terminal (or ask the agent). It is
stored in `.podman/home/.pi/agent` and survives `zpa upgrade`.
`pi install -l <spec>` writes to the repo's `.pi/settings.json` instead.

If a project installs a plugin that is also baked, the wrapper skips the
baked copy (matched by npm name or git repo).

Start a new thread after installing so the agent picks the plugin up.

Management subcommands (`pi install`, `update`, `list`, `auth`, `config`,
`mcp`, …) run without the baked plugins, so `pi list` does not show them.
That is not a sign they are missing.
