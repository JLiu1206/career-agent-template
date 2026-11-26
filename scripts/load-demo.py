#!/usr/bin/env python3
"""Load the fictional demo student so you can try /apply without your own CV.

Usage:  python3 scripts/load-demo.py

Copies examples/demo-student/ into profile/, style/, orgs/, applications/,
prep/ and inbox/, and sets the active cycle in CLAUDE.md. It refuses (exit 2)
if profile/ or inbox/ already holds your own files, so it can never overwrite
your data. To go back to a clean copy afterwards, clone the template again.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo-student"
FOLDERS = ["profile", "style", "orgs", "applications", "prep", "inbox"]
PLACEHOLDERS = {"readme.md", ".gitkeep", ".ds_store"}


def own_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return [p for p in folder.rglob("*") if p.is_file() and p.name.lower() not in PLACEHOLDERS]


def main() -> int:
    if not DEMO.is_dir():
        print(f"ERROR: demo folder not found: {DEMO}", file=sys.stderr)
        return 2
    for name in ("profile", "inbox"):
        if own_files(ROOT / name):
            print(
                f"refusing: {name}/ already has files. The demo would mix with your own data.\n"
                f"Move your files out of {name}/ first, or try the demo in a fresh clone.",
                file=sys.stderr,
            )
            return 2

    cycles = [p.name for p in (DEMO / "applications").iterdir() if p.is_dir()]
    if len(cycles) != 1:
        print(f"ERROR: expected one cycle folder in {DEMO / 'applications'}, found {cycles}", file=sys.stderr)
        return 2
    cycle = cycles[0]

    for name in FOLDERS:
        source = DEMO / name
        if source.is_dir():
            shutil.copytree(source, ROOT / name, dirs_exist_ok=True)

    claude_md = ROOT / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8")
    text = re.sub(r"\*\*Active cycle:\*\* `[^`]*`", f"**Active cycle:** `{cycle}`", text, count=1)
    scope_file = DEMO / "scope.txt"
    if scope_file.exists():
        scope = scope_file.read_text(encoding="utf-8").strip()
        text = re.sub(
            r"(## What counts as an application\n\n).*?(\n\n)",
            lambda m: m.group(1) + scope + m.group(2),
            text,
            count=1,
            flags=re.DOTALL,
        )
    claude_md.write_text(text, encoding="utf-8")
    print(f"Loaded the demo student (fictional). Active cycle: {cycle}.")
    print('Next: run `claude` here and try  /apply 200-word answer to "Why do you want to join Corrin Rail\'s graduate scheme?" for Corrin Rail')
    return 0


if __name__ == "__main__":
    sys.exit(main())
