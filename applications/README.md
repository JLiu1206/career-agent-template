# applications

One folder per recruiting cycle (the active one is named in `CLAUDE.md`).
Inside each cycle folder:

- `tracker.md`: one row per application. `/apply` adds rows when you approve
  a draft. Edit it by hand whenever that's quicker.
- `story-usage.jsonl`: which story went to which organisation. It's
  append-only, and the reuse rules read it.
- `<org-slug>/`: drafts, plus anything you actually submitted. Save the text
  of submitted answers here as `.md` or `.txt` so the reuse check can
  compare future drafts against them.
