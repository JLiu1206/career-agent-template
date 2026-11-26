#!/usr/bin/env python3
"""Block word-for-word reuse between a draft and your earlier applications.

Usage:  python3 scripts/check-reuse.py <draft> [--root DIR ...] [--profile profile/profile.md] [--n 8]

By default it compares against applications/ (what you have sent or drafted)
and style/exemplars/ (your past writing, which drafts are modelled on).

Exit codes:
  0  CLEAR  no run of 8 consecutive words matches any earlier application
  1  BLOCK  at least one run matches; the runs and files are listed
  2  ERROR  a file could not be read, so the check cannot say CLEAR

Reusing a story across different organisations is fine. Copying the same
sentences is what this catches. Your name, address, contact lines and
sign-off are ignored, because every letter shares them.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_N = 8
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".markdown", ".txt"}
SIGN_OFF_RE = re.compile(
    r"^\s*(?:kind|best|warm|many)\s+regards\b|^\s*yours\s+(?:sincerely|faithfully)\b",
    re.IGNORECASE,
)
CONTACT_RE = re.compile(
    r"(?:\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|https?://\S+|www\.\S+|linkedin\.com/\S+|\+?\d[\d\s().-]{7,})",
    re.IGNORECASE,
)
CONTACT_LABEL_RE = re.compile(r"\b(?:email|e-mail|phone|tel|telephone|mobile|linkedin)\s*:\s*", re.IGNORECASE)
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

JUNK_NAMES = {".ds_store", ".localized", "thumbs.db", "desktop.ini", ".gitkeep"}
# Records of prompts, deadlines and mail, not earlier submissions.
METADATA_NAMES = {"tracker.md", "inbox-queue.md", "story-usage.jsonl", "readme.md"}


class ArtifactExtractionError(RuntimeError):
    """A supported file could not be read reliably."""


def front_matter(path: Path) -> dict[str, str]:
    """Read simple `key: value` YAML front matter; missing file or block gives {}."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key.strip()] = value
    return fields


def word_tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text.replace("’", "'"))]


class Boilerplate:
    """Name and address lines taken from the student's own profile."""

    def __init__(self, profile: Path) -> None:
        fields = front_matter(profile)
        self.name = set(word_tokens(fields.get("name", "")))
        self.address = {t for t in word_tokens(fields.get("address", "")) if not t.isdigit()}

    def strip(self, text: str) -> str:
        kept: list[str] = []
        in_signature = False
        for line in text.replace("’", "'").splitlines():
            stripped = line.strip()
            residual = CONTACT_LABEL_RE.sub("", CONTACT_RE.sub("", stripped))
            residual = re.sub(r"^[\s|,;•]+|[\s|,;•]+$", "", residual)
            line_tokens = word_tokens(residual)
            nonnumeric = {t for t in line_tokens if not t.isdigit()}
            is_name_only = bool(self.name) and bool(line_tokens) and set(line_tokens) <= self.name and len(line_tokens) <= len(self.name)
            is_address = bool(POSTCODE_RE.search(residual)) or (
                bool(self.address) and bool(nonnumeric) and nonnumeric <= self.address and len(line_tokens) <= 5
            )
            if SIGN_OFF_RE.search(stripped):
                in_signature = True
                continue
            if in_signature or not line_tokens or is_name_only or is_address:
                continue
            kept.append(residual)
        return "\n".join(kept)


def ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def extract_pdf(path: Path) -> str:
    try:
        result = subprocess.run(["pdftotext", str(path), "-"], text=True, capture_output=True, check=False)
    except OSError as exc:
        raise ArtifactExtractionError(
            f"cannot read PDF {path}: pdftotext is not installed. Install it (macOS: brew install poppler), "
            "or save the PDF's text as a .txt file and move the PDF out of that folder."
        ) from exc
    if result.returncode != 0:
        raise ArtifactExtractionError(f"cannot extract PDF {path}: {result.stderr.strip() or result.returncode}")
    if not result.stdout.strip():
        raise ArtifactExtractionError(f"PDF contains no extractable text: {path} (save its text as a .txt file instead)")
    return result.stdout


def extract_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            members = [
                name
                for name in archive.namelist()
                if name == "word/document.xml"
                or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
                or name in {"word/footnotes.xml", "word/endnotes.xml"}
            ]
            if "word/document.xml" not in members:
                raise KeyError("word/document.xml")
            documents = [archive.read(name) for name in sorted(members)]
        text = " ".join(
            node.text or ""
            for document in documents
            for node in ET.fromstring(document).iter()
            if node.tag.endswith("}t")
        )
    except (ET.ParseError, KeyError, OSError, zipfile.BadZipFile) as exc:
        raise ArtifactExtractionError(f"cannot extract DOCX {path}: {exc}") from exc
    if not text.strip():
        raise ArtifactExtractionError(f"DOCX contains no extractable text: {path}")
    return text


def extract_text(path: Path) -> str | None:
    """Text of a supported file, or None for a type this script cannot read."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return extract_pdf(path)
        if suffix == ".docx":
            return extract_docx(path)
        if suffix in TEXT_SUFFIXES or not suffix:
            return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ArtifactExtractionError(f"cannot read {path}: {exc}") from exc
    return None


def candidate_files(root: Path, draft: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.rglob("*")):
        name = path.name.lower()
        if not path.is_file() or path.resolve() == draft or name in JUNK_NAMES or name.startswith("._"):
            continue
        if name in METADATA_NAMES:
            continue
        out.append(path)
    return out


def check(draft: Path, roots: list[Path], profile: Path, n: int) -> tuple[dict[tuple[str, ...], list[Path]], list[Path]]:
    """Return (matching runs -> files, files that could not be read)."""
    boilerplate = Boilerplate(profile)
    draft_text = extract_text(draft)
    if draft_text is None:
        raise ArtifactExtractionError(f"unsupported draft type: {draft} (use .md, .txt or .docx)")
    draft_grams = ngrams(word_tokens(boilerplate.strip(draft_text)), n)
    matches: dict[tuple[str, ...], list[Path]] = defaultdict(list)
    skipped: list[Path] = []
    candidates = sorted({c for root in roots for c in candidate_files(root, draft.resolve())})
    for candidate in candidates:
        text = extract_text(candidate)
        if text is None:
            skipped.append(candidate)
            continue
        for gram in draft_grams & ngrams(word_tokens(boilerplate.strip(text)), n):
            matches[gram].append(candidate)
    return matches, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block word-for-word reuse of earlier applications.")
    parser.add_argument("draft", type=Path)
    parser.add_argument("--root", type=Path, action="append", help="folder of earlier writing; repeatable (default: applications/ and style/exemplars/)")
    parser.add_argument("--profile", type=Path, default=ROOT / "profile" / "profile.md", help="profile with your name and address")
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="consecutive words that count as reuse (default: %(default)s)")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n must be at least 1")
    if not args.draft.is_file():
        parser.error(f"draft is not a readable file: {args.draft}")

    roots = args.root or [ROOT / "applications", ROOT / "style" / "exemplars"]
    where = ", ".join(str(r) for r in roots)
    try:
        matches, skipped = check(args.draft, roots, args.profile, args.n)
    except ArtifactExtractionError as exc:
        print(f"ERROR: reuse check failed closed: {exc}", file=sys.stderr)
        return 2

    if matches:
        print(f"BLOCK: found {len(matches)} matching {args.n}-word run(s) under {where}")
        for gram, paths in sorted(matches.items()):
            print(f"  {' '.join(gram)!r}")
            for path in paths:
                print(f"    {path}")
        if skipped:
            print(f"  (also could not read: {', '.join(str(p) for p in skipped)})")
        return 1
    if skipped:
        print("ERROR: reuse check failed closed: these files could not be read, so CLEAR cannot be given:", file=sys.stderr)
        for path in skipped:
            print(f"  {path}", file=sys.stderr)
        print("Save each one's text as a .txt or .md file, or move it out of that folder.", file=sys.stderr)
        return 2
    print(f"CLEAR: no {args.n}-word reuse matches under {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
