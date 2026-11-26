#!/usr/bin/env python3
"""Extract text and dates from the documents in inbox/ for /career-setup.

Usage:  python3 scripts/extract-docs.py inbox [--out .setup]

Writes <out>/<name>.txt for every readable document, and <out>/manifest.json:
a list of {file, text_file, sha256, size_bytes, created, modified,
date_source, words, status}.

status:       ok | needs-read-tool (a PDF this script cannot read; open it
              with Claude's Read tool instead) | unsupported
date_source:  docx-core (dates stored inside the Word file) | pdfinfo |
              file-mtime (a fallback: when the file was last saved on this
              computer, which may not be when you wrote it)

Exit 0 when the inbox has at least one document, 2 when it is missing or empty.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
SKIP_NAMES = {"readme.md", ".ds_store", ".localized", "thumbs.db", "desktop.ini"}


def _load_reuse():
    spec = importlib.util.spec_from_file_location("check_reuse", HERE / "check-reuse.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REUSE = _load_reuse()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mtime_iso(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def docx_dates(path: Path) -> tuple[str | None, str | None]:
    try:
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("docProps/core.xml"))
    except (KeyError, OSError, ET.ParseError, zipfile.BadZipFile):
        return None, None
    found = {}
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in {"created", "modified"} and node.text:
            found[tag] = node.text.strip()
    return found.get("created"), found.get("modified")


def pdf_dates(path: Path) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(["pdfinfo", "-isodates", str(path)], text=True, capture_output=True, check=False)
    except OSError:
        return None, None
    fields = dict(re.findall(r"^(CreationDate|ModDate):\s*(.+)$", result.stdout, re.MULTILINE))
    return fields.get("CreationDate"), fields.get("ModDate")


def describe(path: Path) -> tuple[dict, str | None]:
    """Return (manifest entry without text_file, extracted text or None)."""
    suffix = path.suffix.lower()
    entry = {"file": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size}
    created = modified = None
    source = "file-mtime"
    text: str | None = None
    status = "ok"
    try:
        if suffix == ".docx":
            text = REUSE.extract_docx(path)
            created, modified = docx_dates(path)
            source = "docx-core" if (created or modified) else "file-mtime"
        elif suffix == ".pdf":
            created, modified = pdf_dates(path)
            source = "pdfinfo" if (created or modified) else "file-mtime"
            text = REUSE.extract_pdf(path)
        elif suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8")
        else:
            status = "unsupported"
    except (REUSE.ArtifactExtractionError, UnicodeDecodeError, OSError):
        status = "needs-read-tool"
        text = None
    if source == "file-mtime":
        created = modified = mtime_iso(path)
    entry.update(
        created=created,
        modified=modified,
        date_source=source,
        words=len(text.split()) if text else 0,
        status=status,
    )
    return entry, text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract text and dates from inbox documents.")
    parser.add_argument("inbox", type=Path)
    parser.add_argument("--out", type=Path, default=Path(".setup"))
    args = parser.parse_args(argv)

    files = []
    if args.inbox.is_dir():
        files = sorted(
            p for p in args.inbox.iterdir()
            if p.is_file() and p.name.lower() not in SKIP_NAMES and not p.name.startswith((".", "~$"))
        )
    if not files:
        print(f"ERROR: no documents found in inbox folder {args.inbox}. Put your CV and past applications there.", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    used_names: set[str] = set()
    for path in files:
        entry, text = describe(path)
        entry["text_file"] = None
        if text is not None:
            name = f"{path.stem}.txt"
            if name in used_names:
                name = f"{path.stem}-{path.suffix.lstrip('.').lower()}.txt"
            used_names.add(name)
            (args.out / name).write_text(text, encoding="utf-8")
            entry["text_file"] = name
        manifest.append(entry)
        print(f"{entry['status']:16} {entry['date_source']:10} {entry['words']:6} words  {path.name}")

    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {args.out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
