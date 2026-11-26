"""Tests for the deterministic helper scripts. Run: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
HAS_PDFTOTEXT = shutil.which("pdftotext") is not None


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def path_without_pdftotext() -> str:
    """The current PATH minus every directory that holds pdftotext."""
    entries = os.environ.get("PATH", "").split(os.pathsep)
    return os.pathsep.join(e for e in entries if e and not (Path(e) / "pdftotext").exists())


def write_pdf(path: Path, text: str) -> None:
    """Write the smallest valid text PDF needed to exercise pdftotext."""
    stream = f"BT\n/F1 12 Tf\n72 720 Td\n({text}) Tj\nET\n".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    content.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:]))
    content.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(content)


def write_docx(path: Path, text: str, *, header_text: str | None = None, core_xml: str | None = None) -> None:
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    document = (
        f'<?xml version="1.0" encoding="UTF-8"?><w:document {ns}>'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)
        if header_text is not None:
            archive.writestr(
                "word/header1.xml",
                f'<?xml version="1.0" encoding="UTF-8"?><w:hdr {ns}><w:p><w:r><w:t>{header_text}</w:t></w:r></w:p></w:hdr>',
            )
        if core_xml is not None:
            archive.writestr("docProps/core.xml", core_xml)


STALE = load_module("check_profile_staleness", "check-profile-staleness.py")
SLUG = load_module("resolve_slug", "resolve-slug.py")

FICTIONAL_PROFILE = (
    "---\n"
    'name: "Sam Rivers"\n'
    'address: "12 Example Road, London, SW7 2AZ"\n'
    "fictional: true\n"
    "---\n\n# Profile\n"
)


class ProfileStalenessTests(unittest.TestCase):
    def write_manifest(self, directory: Path, source: Path | str, digest: str, size: int) -> Path:
        manifest = directory / "current-cv.md"
        manifest.write_text(
            f'---\nsource_path: "{source}"\nsha256: "{digest}"\nsize_bytes: {size}\n---\n',
            encoding="utf-8",
        )
        return manifest

    def test_current_cv_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "cv.pdf"
            source.write_bytes(b"current CV bytes")
            manifest = self.write_manifest(directory, source, hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_size)
            code, message = STALE.check(manifest)
            self.assertEqual(code, 0)
            self.assertIn("CURRENT", message)

    def test_changed_cv_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "cv.pdf"
            source.write_bytes(b"old CV")
            manifest = self.write_manifest(directory, source, hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_size)
            source.write_bytes(b"new CV with different content")
            code, message = STALE.check(manifest)
            self.assertEqual(code, 1)
            self.assertIn("STALE", message)
            self.assertIn("sha256", message)


    def test_relative_source_path_resolves_from_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "profile").mkdir()
            (repo / "inbox").mkdir()
            source = repo / "inbox" / "cv.docx"
            source.write_bytes(b"demo CV bytes")
            manifest = self.write_manifest(
                repo / "profile", "inbox/cv.docx", hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_size
            )
            code, message = STALE.check(manifest)
            self.assertEqual(code, 0, message)
            self.assertIn("CURRENT", message)


class ReuseTests(unittest.TestCase):
    def run_paths(
        self, draft: Path, root: Path, profile: Path | None = None, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        profile = profile if profile is not None else root.parent / "no-profile.md"
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "check-reuse.py"), str(draft), "--root", str(root), "--profile", str(profile)],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def workspace(self) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        org_dir = directory / "applications" / "2027" / "some-org"
        org_dir.mkdir(parents=True)
        return directory, org_dir

    def run_check(
        self,
        draft_text: str,
        prior_text: str | None = None,
        *,
        draft_in_root: bool = False,
        profile_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        directory, org_dir = self.workspace()
        draft = (org_dir / "draft.md") if draft_in_root else (directory / "draft.md")
        draft.write_text(draft_text, encoding="utf-8")
        if prior_text is not None:
            (org_dir / "prior.md").write_text(prior_text, encoding="utf-8")
        profile = None
        if profile_text is not None:
            profile = directory / "profile.md"
            profile.write_text(profile_text, encoding="utf-8")
        return self.run_paths(draft, directory / "applications", profile)

    # Ported from the original suite.

    def test_copied_eight_gram_blocks(self) -> None:
        phrase = "I built a model to analyse the market dynamics"
        result = self.run_check(phrase + " for this role.", "Earlier, " + phrase + " under pressure.")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("BLOCK", result.stdout)

    def test_case_and_punctuation_are_normalized(self) -> None:
        result = self.run_check(
            "I BUILT, a model: to analyse the market dynamics!",
            "I built a model to analyse the market dynamics yesterday.",
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_meaningful_uk_text_is_not_treated_as_boilerplate(self) -> None:
        phrase = "I want to work on UK rail projects every day"
        result = self.run_check(phrase, "Earlier, " + phrase + " with my team.")
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_mixed_contact_and_substantive_prose_still_blocks(self) -> None:
        phrase = "I built a robust model for bridge load analysis under pressure"
        result = self.run_check("email@example.com " + phrase, "LinkedIn: https://linkedin.com/in/someone " + phrase)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_draft_under_root_is_excluded_from_its_own_comparison(self) -> None:
        result = self.run_check("one two three four five six seven eight", draft_in_root=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_unrelated_draft_is_clear(self) -> None:
        result = self.run_check(
            "I studied heat exchanger fouling through plant data.",
            "My software project improved transcription latency under load.",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("CLEAR", result.stdout)

    def test_metadata_files_are_not_compared(self) -> None:
        directory, org_dir = self.workspace()
        phrase = "I built a model to analyse the market dynamics"
        draft = directory / "draft.md"
        draft.write_text(phrase, encoding="utf-8")
        (org_dir.parent / "tracker.md").write_text(phrase, encoding="utf-8")
        (org_dir.parent / "story-usage.jsonl").write_text(phrase, encoding="utf-8")
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAS_PDFTOTEXT, "pdftotext not installed")
    def test_pdf_artifact_is_scanned(self) -> None:
        directory, org_dir = self.workspace()
        phrase = "I built a model to analyse the market dynamics"
        draft = directory / "draft.md"
        draft.write_text(phrase, encoding="utf-8")
        write_pdf(org_dir / "prior.pdf", phrase)
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    @unittest.skipUnless(HAS_PDFTOTEXT, "pdftotext not installed")
    def test_empty_pdf_fails_closed(self) -> None:
        directory, org_dir = self.workspace()
        draft = directory / "draft.md"
        draft.write_text("A clear draft with enough ordinary words to check safely.", encoding="utf-8")
        write_pdf(org_dir / "image-only.pdf", "")
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("no extractable text", result.stderr)
        self.assertNotIn("CLEAR", result.stdout)

    def test_docx_artifact_is_scanned(self) -> None:
        directory, org_dir = self.workspace()
        phrase = "I built a model to analyse the market dynamics"
        draft = directory / "draft.md"
        draft.write_text(phrase, encoding="utf-8")
        write_docx(org_dir / "prior.docx", phrase)
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_docx_header_text_is_scanned(self) -> None:
        directory, org_dir = self.workspace()
        phrase = "I built a model to analyse the market dynamics"
        draft = directory / "draft.md"
        draft.write_text(phrase, encoding="utf-8")
        write_docx(org_dir / "prior.docx", "unrelated body text", header_text=phrase)
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_empty_docx_fails_closed(self) -> None:
        directory, org_dir = self.workspace()
        draft = directory / "draft.md"
        draft.write_text("A clear draft with enough ordinary words to check safely.", encoding="utf-8")
        write_docx(org_dir / "empty.docx", "")
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("no extractable text", result.stderr)
        self.assertNotIn("CLEAR", result.stdout)

    def test_corrupt_supported_artifact_fails_closed(self) -> None:
        directory, org_dir = self.workspace()
        draft = directory / "draft.md"
        draft.write_text("A clear draft with enough ordinary words to check safely.", encoding="utf-8")
        (org_dir / "corrupt.docx").write_bytes(b"not a docx")
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("CLEAR", result.stdout)

    # Profile-driven boilerplate (replaces the original hard-coded name and address).

    def test_profile_header_and_signoff_do_not_block(self) -> None:
        header = "Sam Rivers\n12 Example Road\nLondon SW7 2AZ\nsam.rivers@example.ac.uk\n"
        result = self.run_check(
            header + "Dear Hiring Manager,\nI enjoy designing bridges.\nKind regards,\nSam Rivers\n",
            header + "Dear Hiring Manager,\nI enjoy building robots.\nKind regards,\nSam Rivers\n",
            profile_text=FICTIONAL_PROFILE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CLEAR", result.stdout)

    def test_profile_header_with_substantive_shared_run_blocks(self) -> None:
        header = "Sam Rivers\n12 Example Road\nLondon SW7 2AZ\n"
        phrase = "I designed a footbridge model that cut steel use by a third"
        result = self.run_check(header + phrase, header + "Earlier, " + phrase + ".", profile_text=FICTIONAL_PROFILE)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_substantive_identity_line_still_blocks(self) -> None:
        phrase = "Sam Rivers developed a robust model for bridge load analysis"
        result = self.run_check(phrase, "Earlier, " + phrase + " under pressure.", profile_text=FICTIONAL_PROFILE)
        self.assertEqual(result.returncode, 1, result.stdout)

    # New behaviour for the template.

    def test_multiple_roots_are_scanned(self) -> None:
        directory, org_dir = self.workspace()
        exemplars = directory / "style" / "exemplars"
        exemplars.mkdir(parents=True)
        phrase = "I rewrote the bearing checks so they ran overnight"
        draft = directory / "draft.md"
        draft.write_text(phrase, encoding="utf-8")
        (exemplars / "2025-11-01__cover-letter__internship__x.md").write_text("---\ntype: cover-letter\n---\n" + phrase, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "check-reuse.py"), str(draft), "--root", str(exemplars),
             "--root", str(directory / "applications"), "--profile", str(directory / "none.md")],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_default_roots_include_exemplars(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        shutil.copytree(SCRIPTS, repo / "scripts")
        (repo / "applications").mkdir()
        (repo / "style" / "exemplars").mkdir(parents=True)
        phrase = "I rewrote the bearing checks so they ran overnight"
        (repo / "style" / "exemplars" / "old.md").write_text(phrase, encoding="utf-8")
        (repo / "style" / "exemplars" / ".gitkeep").write_text("", encoding="utf-8")
        draft = repo / "draft.md"
        draft.write_text(phrase, encoding="utf-8")
        result = subprocess.run([sys.executable, str(repo / "scripts" / "check-reuse.py"), str(draft)],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_unreadable_pdf_exits_2_with_advice(self) -> None:
        directory, org_dir = self.workspace()
        draft = directory / "draft.md"
        draft.write_text("A clear draft with enough ordinary words to check safely.", encoding="utf-8")
        write_pdf(org_dir / "submitted.pdf", "some submitted text that cannot be read here")
        env = dict(os.environ, PATH=path_without_pdftotext())
        result = self.run_paths(draft, directory / "applications", env=env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("pdftotext", result.stderr)
        self.assertIn(".txt", result.stderr)
        self.assertNotIn("CLEAR", result.stdout)

    def test_unsupported_file_in_root_exits_2(self) -> None:
        directory, org_dir = self.workspace()
        draft = directory / "draft.md"
        draft.write_text("A clear draft with enough ordinary words to check safely.", encoding="utf-8")
        (org_dir / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("screenshot.png", result.stdout + result.stderr)
        self.assertNotIn("CLEAR", result.stdout)

    def test_ds_store_ignored(self) -> None:
        directory, org_dir = self.workspace()
        draft = directory / "draft.md"
        draft.write_text("A clear draft with enough ordinary words to check safely.", encoding="utf-8")
        (org_dir / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1\x00\xff")
        result = self.run_paths(draft, directory / "applications")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_curly_quotes_and_accents_normalise(self) -> None:
        accented = "my naïve first model of the plant was wrong"
        result = self.run_check(accented, "Earlier, " + accented + " again.")
        self.assertEqual(result.returncode, 1, result.stdout)
        curly = self.run_check(
            "I don’t think the first plant model was quite right",
            "Back then I don't think the first plant model was quite right either.",
        )
        self.assertEqual(curly.returncode, 1, curly.stdout)


class ExtractDocsTests(unittest.TestCase):
    CORE = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dcterms:created xsi:type="dcterms:W3CDTF">2025-10-01T10:00:00Z</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">2025-10-03T09:30:00Z</dcterms:modified>'
        "</cp:coreProperties>"
    )

    def run_extract(self, inbox: Path, out: Path, env: dict[str, str] | None = None):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "extract-docs.py"), str(inbox), "--out", str(out)],
            text=True, capture_output=True, check=False, env=env,
        )
        manifest = out / "manifest.json"
        entries = {e["file"]: e for e in json.loads(manifest.read_text())} if manifest.exists() else {}
        return result, entries

    def dirs(self) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        inbox = Path(temporary.name) / "inbox"
        inbox.mkdir()
        return inbox, Path(temporary.name) / ".setup"

    def test_docx_core_dates_extracted(self) -> None:
        inbox, out = self.dirs()
        write_docx(inbox / "letter.docx", "I want to build better bridges", core_xml=self.CORE)
        result, entries = self.run_extract(inbox, out)
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = entries["letter.docx"]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["date_source"], "docx-core")
        self.assertEqual(entry["created"], "2025-10-01T10:00:00Z")
        self.assertEqual(entry["modified"], "2025-10-03T09:30:00Z")
        self.assertEqual(entry["words"], 6)
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertIn("better bridges", (out / "letter.txt").read_text())

    def test_txt_and_md_read(self) -> None:
        inbox, out = self.dirs()
        (inbox / "notes.md").write_text("Why I chose engineering, in five words.", encoding="utf-8")
        (inbox / "README.md").write_text("Drop your CV here.", encoding="utf-8")
        result, entries = self.run_extract(inbox, out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(entries["notes.md"]["status"], "ok")
        self.assertEqual(entries["notes.md"]["date_source"], "file-mtime")
        self.assertNotIn("README.md", entries)

    def test_pdf_without_pdftotext_is_flagged_not_fatal(self) -> None:
        inbox, out = self.dirs()
        write_pdf(inbox / "cv.pdf", "Sam Rivers curriculum vitae")
        env = dict(os.environ, PATH=path_without_pdftotext())
        result, entries = self.run_extract(inbox, out, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(entries["cv.pdf"]["status"], "needs-read-tool")

    def test_unsupported_file_listed(self) -> None:
        inbox, out = self.dirs()
        (inbox / "photo.jpg").write_bytes(b"\xff\xd8\xff")
        result, entries = self.run_extract(inbox, out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(entries["photo.jpg"]["status"], "unsupported")

    def test_empty_inbox_exits_2(self) -> None:
        inbox, out = self.dirs()
        (inbox / "README.md").write_text("Drop your CV here.", encoding="utf-8")
        result, _ = self.run_extract(inbox, out)
        self.assertEqual(result.returncode, 2)
        self.assertIn("inbox", result.stderr)


class LoadDemoTests(unittest.TestCase):
    def repo_copy(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name) / "repo"
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", ".superpowers", "examples", "__pycache__"))
        demo = repo / "examples" / "demo-student"
        (demo / "profile").mkdir(parents=True)
        (demo / "profile" / "profile.md").write_text(FICTIONAL_PROFILE, encoding="utf-8")
        (demo / "applications" / "2027" / "arup").mkdir(parents=True)
        (demo / "applications" / "2027" / "tracker.md").write_text("| org |\n", encoding="utf-8")
        (demo / "orgs").mkdir()
        (demo / "orgs" / "_registry.md").write_text("| `arup` | Arup | employer | engineering | |\n", encoding="utf-8")
        (demo / "inbox").mkdir()
        (demo / "inbox" / "cv.docx").write_bytes(b"fake")
        (demo / "scope.txt").write_text("Summer internships and graduate schemes in engineering.", encoding="utf-8")
        return repo

    def run_loader(self, repo: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(repo / "scripts" / "load-demo.py")], text=True, capture_output=True, check=False)

    def test_load_demo_refuses_when_profile_has_files(self) -> None:
        repo = self.repo_copy()
        (repo / "profile" / "profile.md").write_text("my real profile", encoding="utf-8")
        result = self.run_loader(repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing: profile/ already has files", result.stderr)
        self.assertEqual((repo / "profile" / "profile.md").read_text(), "my real profile")

    def test_load_demo_refuses_when_inbox_has_files(self) -> None:
        repo = self.repo_copy()
        (repo / "inbox" / "my-cv.pdf").write_bytes(b"mine")
        result = self.run_loader(repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("inbox/", result.stderr)

    def test_load_demo_copies_and_sets_cycle(self) -> None:
        repo = self.repo_copy()
        result = self.run_loader(repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((repo / "profile" / "profile.md").exists())
        self.assertTrue((repo / "inbox" / "cv.docx").exists())
        self.assertIn("arup", (repo / "orgs" / "_registry.md").read_text())
        claude_md = (repo / "CLAUDE.md").read_text()
        self.assertIn("**Active cycle:** `2027`", claude_md)
        self.assertIn("Summer internships and graduate schemes in engineering.", claude_md)
        self.assertNotIn("not set (run /career-setup)", claude_md)


class SlugTests(unittest.TestCase):
    def registry(self, rows: list[str]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "_registry.md"
        path.write_text(
            "| slug | display name | kind | sector | aliases |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
            encoding="utf-8",
        )
        return path

    def test_research_group_slug(self) -> None:
        verdict, slug, _ = SLUG.resolve("Dr Vantmoor's Lab", self.registry([]))
        self.assertEqual((verdict, slug), ("CREATE", "dr-vantmoors-lab"))

    def test_legal_suffix_stripped(self) -> None:
        self.assertEqual(SLUG.resolve("Arup Group Ltd", self.registry([]))[:2], ("CREATE", "arup"))
        reg = self.registry(["| `arup` | Arup | employer | engineering | Arup Group |"])
        self.assertEqual(SLUG.resolve("Arup Group Ltd", reg)[:2], ("MATCH", "arup"))

    def test_alias_matches(self) -> None:
        reg = self.registry(["| `rolls-royce` | Rolls-Royce | employer | aerospace | RR, Rolls Royce plc |"])
        self.assertEqual(SLUG.resolve("Rolls Royce", reg)[:2], ("MATCH", "rolls-royce"))

    def test_near_match_asks(self) -> None:
        reg = self.registry(["| `arup` | Arup | employer | engineering | |"])
        verdict, _, near = SLUG.resolve("Arup Associates", reg)
        self.assertEqual(verdict, "ASK")
        self.assertEqual(near, ["arup"])

    def test_short_alias_no_false_near_match(self) -> None:
        reg = self.registry(["| `arm` | Arm | employer | technology | ARM |"])
        self.assertEqual(SLUG.resolve("Pharmaron", reg)[0], "CREATE")

    def test_cli_exit_codes(self) -> None:
        reg = self.registry(["| `arup` | Arup | employer | engineering | |"])
        run = lambda name: subprocess.run(
            [sys.executable, str(SCRIPTS / "resolve-slug.py"), name, "--registry", str(reg)],
            text=True, capture_output=True, check=False,
        )
        match, ask = run("Arup"), run("Arup Associates")
        self.assertEqual((match.returncode, match.stdout.strip()), (0, "MATCH arup"))
        self.assertEqual(ask.returncode, 2)
        self.assertTrue(ask.stdout.startswith("ASK "), ask.stdout)


if __name__ == "__main__":
    unittest.main()
