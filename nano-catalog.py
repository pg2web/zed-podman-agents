#!/usr/bin/env python3
"""Fill pi's nano-gpt model catalog from the project's key (docs/nano-gpt.md).

Run by `zpa-exec agent pi` before pi starts. Does nothing when the catalog is
already real (checkedAt > 1) or there is no key; on any error the stub stays
and the next start retries. `mapped` mirrors mapNanoGptModel in the provider.
"""
import json
import os
import sys
import time
import urllib.request

STORE = os.path.expanduser("~/.pi/agent/models-store.json")
AUTH = os.path.expanduser("~/.pi/agent/auth.json")
BASE = "https://api.nano-gpt.com/api/v1"
DEFAULT_CONTEXT, DEFAULT_MAX = 128_000, 8192


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def pos(v):
    v = num(v)
    return v if v is not None and v > 0 else None


def nonneg(v):
    v = num(v)
    return v if v is not None and v >= 0 else None


def per_million(v, unit):
    v = num(v)
    if v is None:
        return None
    return v * 1000 if isinstance(unit, str) and "per_1k" in unit.lower() else v


def per_thousand(v):
    v = num(v)
    return None if v is None else v * 1000


def modalities(raw):
    arch = raw.get("architecture") or {}
    declared = arch.get("input_modalities")
    if isinstance(declared, list):
        kept = [m for m in declared if m in ("text", "image")]
        if kept:
            return kept
    return ["text", "image"] if (raw.get("capabilities") or {}).get("vision") is True else ["text"]


def mapped(raw):
    mid = raw.get("id")
    if not isinstance(mid, str) or not mid:
        return None
    pr = raw.get("pricing") or {}
    inp = nonneg(per_million(pr.get("prompt"), pr.get("unit"))) or 0
    out = nonneg(per_million(pr.get("completion"), pr.get("unit"))) or 0
    ctx = pos(raw.get("context_length")) or DEFAULT_CONTEXT
    cr = nonneg(per_thousand(pr.get("cacheReadInputPer1kTokens")))
    cw = nonneg(per_thousand(pr.get("cacheWriteInputPer1kTokens")))
    name = raw.get("name")
    return {
        "type": "chat",
        "id": mid,
        "name": name if isinstance(name, str) and name else mid,
        "reasoning": (raw.get("capabilities") or {}).get("reasoning") is True
        or mid.lower().endswith(":thinking"),
        "input": modalities(raw),
        "cost": {
            "input": inp,
            "output": out,
            "cacheRead": inp if cr is None else cr,
            "cacheWrite": inp if cw is None else cw,
        },
        "contextWindow": ctx,
        "maxTokens": min(pos(raw.get("max_output_tokens")) or DEFAULT_MAX, ctx),
        "provider": "nano-gpt",
        "api": "openai-completions",
        "baseUrl": BASE,
    }


def stored_key():
    try:
        with open(AUTH) as f:
            k = json.load(f).get("nano-gpt", {}).get("key")
        return k if isinstance(k, str) and k else None
    except (OSError, ValueError, AttributeError):
        return None


def main():
    try:
        with open(STORE) as f:
            if (json.load(f).get("nano-gpt", {}).get("checkedAt") or 0) > 1:
                return
    except (OSError, ValueError, AttributeError):
        pass
    key = stored_key() or os.environ.get("NANOGPT_API_KEY", "")
    if not key:
        return
    sort = (os.environ.get("NANOGPT_MODEL_SORT") or "favorites").strip().lower()
    url = f"{BASE}/models?detailed=true" + ("" if sort in ("none", "off") else f"&sort={sort}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            records = json.load(r).get("data")
    except Exception as e:  # network, HTTP, JSON: keep the stub, retry next start
        print(f"zpa: nano-gpt catalog not refreshed: {e}", file=sys.stderr)
        return
    models = [m for m in map(mapped, records if isinstance(records, list) else []) if m]
    if not models:
        return
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    tmp = f"{STORE}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump({"nano-gpt": {"models": models, "checkedAt": int(time.time() * 1000)}}, f, indent=2)
    os.replace(tmp, STORE)


if __name__ == "__main__":
    main()
