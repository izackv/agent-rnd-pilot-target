#!/usr/bin/env python3
"""Documentation-impact check (gates.md row "Documentation and traceability").

Fails when files under app/ changed between BASE and HEAD but nothing under docs/ changed,
unless the PR body (DOCS_CHECK_PR_BODY env) contains a line `docs-impact: none ...`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys


def changed(base: str, head: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    base = os.environ.get("DOCS_CHECK_BASE", "origin/main")
    head = os.environ.get("DOCS_CHECK_HEAD", "HEAD")
    body = os.environ.get("DOCS_CHECK_PR_BODY", "")
    files = changed(base, head)
    app_changed = [f for f in files if f.startswith("app/")]
    docs_changed = [f for f in files if f.startswith("docs/")]
    waiver = re.search(r"^\s*docs-impact:\s*none\b.*$", body, re.M | re.I)
    print(f"changed under app/: {len(app_changed)}, under docs/: {len(docs_changed)}")
    if app_changed and not docs_changed and not waiver:
        print(
            "FAIL: app/ changed without docs/ and no 'docs-impact: none <reason>' line in PR body"
        )
        return 1
    if waiver:
        print(f"docs waiver present: {waiver.group(0).strip()}")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
