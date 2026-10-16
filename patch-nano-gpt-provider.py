#!/usr/bin/env python3
# Build-time patch for the baked pi-nano-gpt-provider: serve the cached model
# catalog at any age instead of re-fetching it during session/new, which Zed
# times out on. Why, and how the catalog gets filled: docs/nano-gpt.md.
# A no-op when the provider is not baked; fails the build if the code it
# patches has changed.
import pathlib
import sys

SRC = pathlib.Path("/opt/zpa/pi-plugins/home/.pi/agent/npm/node_modules/"
                   "pi-nano-gpt-provider/src/nano-gpt-provider.ts")
OLD = "checkedAt !== undefined && Date.now() - checkedAt < CATALOG_TTL_MS && lastKnown.length > 0"
NEW = "lastKnown.length > 0 /* zpa: serve cache; refreshed out of band */"

if not SRC.exists():
    sys.exit(0)
code = SRC.read_text()
if code.count(OLD) != 1:
    sys.exit(f"patch-nano-gpt-provider: the expected code is not in {SRC}; "
             "the provider changed, re-check the patch")
SRC.write_text(code.replace(OLD, NEW))
print(f"patch-nano-gpt-provider: patched {SRC}")
