#!/usr/bin/env python3
"""Check whether the designated CV still matches its recorded source manifest."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


EXIT_CURRENT = 0
EXIT_STALE = 1
EXIT_INVALID = 2


def parse_front_matter(path: Path) -> dict[str, str]:
    """Parse the deliberately simple scalar YAML front matter used by the manifest."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read manifest {path}: {exc}") from exc

    if not lines or lines[0].strip() != "---":
        raise ValueError("manifest must start with YAML front matter ('---')")

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid manifest field: {line!r}")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key:
            raise ValueError(f"invalid manifest field: {line!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
    else:
        raise ValueError("manifest front matter is not closed")
    return fields


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(manifest_path: Path) -> tuple[int, str]:
    try:
        manifest = parse_front_matter(manifest_path)
        source_name = manifest["source_path"]
        expected_hash = manifest["sha256"].lower()
        expected_size = int(manifest["size_bytes"])
    except (KeyError, ValueError) as exc:
        return EXIT_INVALID, f"INVALID manifest: {exc}"

    source = Path(source_name)
    if not source.is_absolute():
        # Relative paths are relative to the folder that holds profile/.
        source = manifest_path.resolve().parent.parent / source
    if not source.is_file():
        return EXIT_STALE, f"STALE: CV source is missing: {source}"

    actual_size = source.stat().st_size
    actual_hash = sha256_file(source)
    problems: list[str] = []
    if actual_size != expected_size:
        problems.append(f"size {actual_size} bytes (expected {expected_size})")
    if actual_hash != expected_hash:
        problems.append(f"sha256 {actual_hash} (expected {expected_hash})")
    if problems:
        return EXIT_STALE, "STALE: CV source changed: " + "; ".join(problems)
    return EXIT_CURRENT, f"CURRENT: CV source matches manifest: {source}"


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "profile" / "current-cv.md",
        help="path to the CV source manifest (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    code, message = check(args.manifest)
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
