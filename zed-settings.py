#!/usr/bin/env python3
"""Add/remove zpa entries in Zed's settings.json (JSONC) without rewriting it.

Only the touched values are edited in place; comments, ordering and
formatting elsewhere are preserved.

  zed-settings.py install   SETTINGS ZPA_BIN STATE_DIR AGENTS_CONF
  zed-settings.py uninstall SETTINGS STATE_DIR
  zed-settings.py env       SETTINGS STATE_DIR   # NAME=VALUE\0 of every zpa agent's env
  zed-settings.py snippet   ZPA_BIN AGENTS_CONF  # print the settings to add by hand

The Zed agent names written are recorded in STATE_DIR/zed-agents.json, so an
agent dropped from agents.conf is removed on the next install, and uninstall
removes exactly what was added.
"""
import json
import pathlib
import shutil
import sys
import time

# used when STATE_DIR/zed-agents.json is missing (installs before agents.conf)
DEFAULT_AGENTS = ["Claude (podman)", "Pi (podman)"]


def read_agents(conf):
    """{Zed name: kind} from agents.conf (kind | Zed name | command | packages)."""
    agents = {}
    for line in pathlib.Path(conf).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 3 or not cols[0] or not cols[1]:
            raise ValueError(f"{conf}: bad line: {line!r}")
        agents[cols[1]] = cols[0]
    return agents


def registered(state):
    f = state / "zed-agents.json"
    return json.loads(f.read_text()) if f.exists() else DEFAULT_AGENTS


class Node:
    def __init__(self, kind, start, end, members=None):
        self.kind, self.start, self.end = kind, start, end
        self.members = members or []  # objects: (key, key_start, Node)


class Parser:
    def __init__(self, text):
        self.t, self.i = text, 0

    def ws(self):
        t = self.t
        while self.i < len(t):
            if t[self.i] in " \t\r\n":
                self.i += 1
            elif t.startswith("//", self.i):
                j = t.find("\n", self.i)
                self.i = len(t) if j < 0 else j
            elif t.startswith("/*", self.i):
                j = t.find("*/", self.i + 2)
                if j < 0:
                    raise ValueError("unterminated comment")
                self.i = j + 2
            else:
                break

    def string(self):
        start, t = self.i, self.t
        self.i += 1
        while t[self.i] != '"':
            self.i += 2 if t[self.i] == "\\" else 1
        self.i += 1
        return json.loads(t[start:self.i])

    def expect(self, c):
        self.ws()
        if self.t[self.i] != c:
            raise ValueError(f"expected {c!r} at offset {self.i}")
        self.i += 1

    def value(self):
        self.ws()
        t, start = self.t, self.i
        c = t[self.i]
        if c == "{":
            self.i += 1
            members = []
            while True:
                self.ws()
                if t[self.i] == "}":
                    break
                key_start = self.i
                key = self.string()
                self.expect(":")
                members.append((key, key_start, self.value()))
                self.ws()
                if t[self.i] == ",":
                    self.i += 1
            self.i += 1
            return Node("object", start, self.i, members)
        if c == "[":
            self.i += 1
            while True:
                self.ws()
                if t[self.i] == "]":
                    break
                self.value()
                self.ws()
                if t[self.i] == ",":
                    self.i += 1
            self.i += 1
            return Node("array", start, self.i)
        if c == '"':
            self.string()
            return Node("string", start, self.i)
        while self.i < len(t) and t[self.i] not in ",]} \t\r\n/":
            self.i += 1
        if self.i == start:
            raise ValueError(f"unexpected {c!r} at offset {start}")
        return Node("literal", start, self.i)


class Settings:
    def __init__(self, text):
        self.text = text if text.strip() else "{\n}\n"
        self.root()

    def root(self):
        p = Parser(self.text)
        node = p.value()
        p.ws()
        if node.kind != "object" or p.i != len(self.text):
            raise ValueError("settings.json is not a single JSON object")
        return node

    def get(self, path):
        node = self.root()
        for key in path:
            if node.kind != "object":
                return None
            node = next((v for k, _, v in node.members if k == key), None)
            if node is None:
                return None
        return node

    def raw(self, path):
        node = self.get(path)
        return None if node is None else self.text[node.start:node.end]

    def value(self, path):
        raw = self.raw(path)
        return None if raw is None else json.loads(raw)

    def set_raw(self, path, raw):
        node = self.get(path)
        if node is not None:
            self.text = self.text[:node.start] + raw + self.text[node.end:]
            return
        parent = self.get(path[:-1])
        if parent is None:
            self.set(path[:-1], {})
            parent = self.get(path[:-1])
        if parent.kind != "object":
            raise ValueError(f"{'.'.join(path[:-1])} is not an object")
        # append after the last member, keeping its trailing comma if any
        member = f"\n{'  ' * len(path)}{json.dumps(path[-1])}: {raw}"
        if parent.members:
            p = Parser(self.text)
            p.i = at = parent.members[-1][2].end
            p.ws()
            if self.text[p.i] == ",":
                at, member = p.i + 1, member + ","
            else:
                member = "," + member
        else:
            at = parent.start + 1
            member += "\n" + "  " * (len(path) - 1)
        self.text = self.text[:at] + member + self.text[at:]

    def set(self, path, value):
        lines = json.dumps(value, indent=2).split("\n")
        indent = "  " * len(path)
        self.set_raw(path, "\n".join([lines[0]] + [indent + l for l in lines[1:]]))

    def delete(self, path):
        parent = self.get(path[:-1])
        if parent is None or parent.kind != "object":
            return
        t = self.text
        for key, key_start, node in parent.members:
            if key != path[-1]:
                continue
            start, end = key_start, node.end
            p = Parser(t)
            p.i = end
            p.ws()
            if p.i < len(t) and t[p.i] == ",":
                end = p.i + 1
            else:
                j = start - 1
                while j > parent.start and t[j] in " \t\r\n":
                    j -= 1
                if t[j] == ",":
                    start = j
            # drop the now-empty line
            ls = t.rfind("\n", 0, start)
            if t[ls + 1:start].strip() == "":
                start = ls if ls >= 0 else start
            self.text = t[:start] + t[end:]
            return


def load(path):
    p = pathlib.Path(path)
    return p, Settings(p.read_text() if p.exists() else "")


def save(p, s):
    s.root()  # still parses
    if p.exists():
        backup = p.with_name(f"{p.name}.zpa-{time.strftime('%Y%m%d-%H%M%S')}.bak")
        shutil.copy2(p, backup)
        print(f"backup: {backup}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s.text)
    print(f"patched: {p}")


def install(settings, zpa_bin, state_dir, agents_conf):
    agents = read_agents(agents_conf)
    p, s = load(settings)
    state = pathlib.Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)

    for name in registered(state):
        if name not in agents:
            s.delete(["agent_servers", name])
    for name, kind in agents.items():
        base = ["agent_servers", name]
        s.set(base + ["type"], "custom")
        s.set(base + ["command"], zpa_bin)
        s.set(base + ["args"], ["acp", kind])
        # keep env / default_config_options set in Zed's GUI
        if s.get(base + ["env"]) is None:
            s.set(base + ["env"], {})

    shell_bin = str(pathlib.Path(zpa_bin).with_name("zpa-shell"))
    prev = s.raw(["terminal", "shell"])
    saved = state / "prev-terminal-shell.jsonc"
    if prev is not None and "zpa-shell" not in prev and not saved.exists():
        saved.write_text(prev)
    s.set(["terminal", "shell"], {"with_arguments": {"program": shell_bin, "args": []}})
    save(p, s)
    (state / "zed-agents.json").write_text(json.dumps(list(agents)) + "\n")


def uninstall(settings, state_dir):
    p, s = load(settings)
    if not p.exists():
        return
    state = pathlib.Path(state_dir)
    for name in registered(state):
        s.delete(["agent_servers", name])
    shell = s.raw(["terminal", "shell"])
    saved = state / "prev-terminal-shell.jsonc"
    if shell is not None and "zpa-shell" in shell:
        prev = saved.read_text() if saved.exists() else None
        if prev:
            s.set_raw(["terminal", "shell"], prev)
        else:
            s.delete(["terminal", "shell"])
    saved.unlink(missing_ok=True)
    (state / "zed-agents.json").unlink(missing_ok=True)
    save(p, s)


def agent_env(settings, state_dir):
    """Merged `env` of every zpa agent in settings.json: NAME=VALUE, NUL-terminated.

    Agents are taken in the order zpa registered them; the first value of a
    name wins (a differing later one is reported on stderr).
    """
    p = pathlib.Path(settings)
    if not p.exists():
        return
    s = Settings(p.read_text())
    seen = {}
    for name in registered(pathlib.Path(state_dir)):
        env = s.get(["agent_servers", name, "env"])
        if env is None or env.kind != "object":
            continue
        for key, _, node in env.members:
            if node.kind != "string":
                continue
            value = json.loads(s.text[node.start:node.end])
            if key in seen and seen[key] != value:
                print(f"zpa: {key} differs between agents; using the first", file=sys.stderr)
            seen.setdefault(key, value)
    for key, value in seen.items():
        sys.stdout.write(f"{key}={value}\0")


def snippet(zpa_bin, agents_conf):
    servers = {
        name: {"type": "custom", "command": zpa_bin, "args": ["acp", kind], "env": {}}
        for name, kind in read_agents(agents_conf).items()
    }
    shell = str(pathlib.Path(zpa_bin).with_name("zpa-shell"))
    print(json.dumps({
        "agent_servers": servers,
        "terminal": {"shell": {"with_arguments": {"program": shell, "args": []}}},
    }, indent=2))


if __name__ == "__main__":
    a = sys.argv[1:]
    try:
        if a[:1] == ["install"] and len(a) == 5:
            install(a[1], a[2], a[3], a[4])
        elif a[:1] == ["uninstall"] and len(a) == 3:
            uninstall(a[1], a[2])
        elif a[:1] == ["env"] and len(a) == 3:
            agent_env(a[1], a[2])
        elif a[:1] == ["snippet"] and len(a) == 3:
            snippet(a[1], a[2])
        else:
            sys.exit(__doc__)
    except (ValueError, IndexError, OSError) as e:
        sys.exit(f"zed-settings: cannot edit {a[1]}: {e}")
