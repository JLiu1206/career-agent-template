#!/usr/bin/env python3
"""Resolve an organisation name to its slug in orgs/_registry.md.

Usage:  python3 scripts/resolve-slug.py "Arup Group Ltd" [--registry orgs/_registry.md]

Output and exit codes (the /apply skill relies on these):
  MATCH  <slug>                 known org (exact, normalised or alias); exit 0
  CREATE <slug>                 resembles nothing; add the row; exit 0
  ASK    <slug> | resembles: a  looks like an existing org; ask the student; exit 2

Why only near-matches interrupt: the one real hazard is two slugs for one
organisation, which silently breaks the reuse check. That can only happen
when a new name resembles an existing one.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "orgs" / "_registry.md"

# Trailing legal forms that never distinguish one organisation from another.
SUFFIXES = r"(?:\s*&?\s*(?:co|company|ltd|limited|llp|llc|inc|plc|group|holdings|international))+$"
# "securities", "partners" and "capital" are NOT stripped: they can be what
# distinguishes two different firms ("X Capital" vs "X Capital Partners").

ROW_RE = re.compile(r"\|\s*`([a-z0-9-]+)`\s*\|([^|]*)\|[^|]*\|[^|]*\|([^|]*)\|")


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[.’']", "", s)  # D.E. -> de, Vantmoor's -> vantmoors
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    previous = None
    while previous != s:  # strip stacked suffixes ("Group Ltd")
        previous = s
        s = re.sub(SUFFIXES, "", s).strip()
    return re.sub(r"\s+", "-", s) or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def words(s: str) -> list[str]:
    return [w for w in slugify(s).split("-") if w]


def registry(path: Path) -> dict[str, list[str]]:
    """Return {slug: [display name, aliases...]} from the markdown table."""
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if m:
            slug, display, aliases = m.group(1), m.group(2), m.group(3)
            names = [display.strip()] + [a.strip() for a in aliases.split(",")]
            out[slug] = [n for n in names if n]
    return out


def resembles(candidate: str, wanted: str) -> bool:
    c, w = norm(candidate), norm(wanted)
    if not c or not w:
        return False
    if len(c) < 5 or len(w) < 5:
        # Too short for substring or fuzzy matching ("arm" sits inside
        # "pharmaron"), so compare whole words only.
        cw, ww = words(candidate), words(wanted)
        shorter, longer = (cw, ww) if len(c) <= len(w) else (ww, cw)
        return bool(shorter) and all(token in longer for token in shorter)
    return c in w or w in c or difflib.SequenceMatcher(None, c, w).ratio() >= 0.80


def resolve(name: str, registry_path: Path = DEFAULT_REGISTRY) -> tuple[str, str, list[str]]:
    reg = registry(registry_path)
    want, wnorm = slugify(name), norm(name)
    for slug, names in reg.items():
        if want == slug or wnorm == norm(slug) or any(wnorm == norm(n) for n in names):
            return "MATCH", slug, []
    near = sorted({slug for slug, names in reg.items() if any(resembles(c, name) for c in [slug, *names])})
    if near:
        return "ASK", want, near
    return "CREATE", want, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve an organisation name to its registry slug.")
    parser.add_argument("name", nargs="+", help="organisation name")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)
    verdict, slug, near = resolve(" ".join(args.name), args.registry)
    if verdict == "ASK":
        print(f"ASK {slug} | resembles: {', '.join(near)}")
        return 2
    print(f"{verdict} {slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
