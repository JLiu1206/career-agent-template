# Career agent

This repo helps a student write applications for internships, graduate
schemes, industrial placements and research positions. It works from the
student's own facts and in the student's own voice.

Facts live in files. Agents and skills hold no personal facts in their
prompts. To correct something the system believes, edit the file.

**Active cycle:** `not set (run /career-setup)`

`<cycle>` in any path below means the active cycle above. `/career-setup` sets
it, and the student changes it here when a new recruiting year starts.

## What counts as an application

not set (run /career-setup)

Track only what is listed here. Anything else that looks like an application
in a draft request or an email (an insight day, a competition, a newsletter
sign-up) gets mentioned to the student, not added to the tracker.

## Who writes what

| Path | Written by |
|---|---|
| `profile/`, `style/` | **The student.** `/career-setup` writes them only after the student approves each file. Everything else proposes changes and never applies them. |
| `orgs/_registry.md`, `applications/<cycle>/tracker.md`, `applications/<cycle>/story-usage.jsonl` | The main session, through `/apply`, after the student approves. `story-usage.jsonl` is append-only. |
| `applications/<cycle>/<slug>/`, `prep/responses/` | `application-writer` |
| `orgs/<slug>.md`, `prep/questions/<slug>.md` | `org-researcher` |
| `inbox/` | The student. `/career-setup` may save CV text the student pastes into chat there, when they ask it to. |

Every other path is read-only to every agent.

## Rules for every agent and skill

**Sourcing**

1. Read `profile/resolutions.md` before `profile/profile.md`. It records
   decisions the student has made and overrides any source document.
2. Every personal claim in a draft must come from `profile/` (each fact
   carries `[src: <file>]`) or from `resolutions.md`.
3. A claim with no source is cut, not softened. If the answer needs it:
   - in the main session, ask the student whether it is true
   - in a subagent, list it under `MISSING FACTS`
4. If the student says a new fact is true, propose adding it to
   `profile/resolutions.md` with `[src: student, <YYYY-MM-DD>]`. Write it
   only after they approve, then use it.
5. Never upgrade, round or embellish a result, grade, title or placement.
   "Top 5%" stays "top 5%". A team result stays "we".
6. Never invent experiences, people, quotes, numbers or outcomes. A
   hypothetical question gets a hypothetical answer.
7. Exemplars in `style/exemplars/` are voice samples, not fact sources. A
   fact that appears only in an exemplar is not usable. Setup copies the
   facts and the student's own stated reasons out of their documents into
   `profile/`, with sources. After that they are usable.
8. An exemplar with `restricted: <slug>` in its front matter is an
   organisation's own assessment material. Use it only when drafting for
   that slug.
9. Document dates come from `python3 scripts/extract-docs.py`, never from a
   date printed inside a letter. Templates often carry an old date.

**Motivations**

"Why us?" and "why this role?" answers need the student's real reasons.
They live in the `## Motivations and interests` section of `profile.md`:
the student's own statements, each with a source. Never invent a reason. If
that section has nothing that fits, ask the student for one or two reasons
before writing the answer.

**Reviews**

The student reviews every draft. Don't start extra reviewer agents for
drafts unless the student asks, because it makes `/apply` much slower.

**Organisations**

- Resolve every organisation name with
  `python3 scripts/resolve-slug.py "<name>"`. Never resolve one by eye.
  - `MATCH <slug>`: use it.
  - `CREATE <slug>`: add a registry row and continue without asking.
  - `ASK`: the name resembles an existing organisation, so ask the student
    whether it is the same one.
- A research group is an organisation too. Give it a slug such as
  `vantmoor-lab`, with kind `research-group`.

**Before drafting**

- Run `python3 scripts/check-profile-staleness.py`. If it says `STALE`, the
  CV has changed since setup. Propose a profile update before using the
  profile.

**Reuse**

Reusing a good story across different organisations is fine and expected.
Two things are blocked:

- **Copied sentences.** Any run of 8 consecutive words that matches an
  earlier application under `applications/` or a past document in
  `style/exemplars/`. Check with
  `python3 scripts/check-reuse.py <draft>`:
  - exit 0 is CLEAR
  - exit 1 is BLOCK: rewrite the flagged sentences and run it again
  - exit 2 means a file could not be read, so the result is not clear;
    tell the student what it printed
- **The same story twice for one organisation in one cycle.** Check
  `applications/<cycle>/story-usage.jsonl` before choosing a story.

**Employer AI policies**

Some organisations ask applicants not to use AI tools. If `orgs/<slug>.md`
records such a policy, quote it to the student before drafting anything they
might submit, and recommend against it. Interview preparation is fine.

**Privacy**

`inbox/`, `profile/`, `style/`, `applications/` and `prep/responses/` hold
personal data:

- Never put the student's personal details into a web search or a URL.
- Research is about organisations only.
- Remind the student to keep their copy of this repo private.

**Out of scope**

Never do any of the following:

- submit applications
- send or draft emails in the student's mail
- sit or prepare answers for live assessments
- answer psychometric questionnaires
- build a persona to match what an employer says it wants

## Formats

**Exemplar front matter** (`style/exemplars/*.md`):

```yaml
---
authored: 2026-01-24        # the document's created date (extract-docs.py)
created: 2026-01-24
date_source: docx-core      # docx-core | pdfinfo | file-mtime | student
type: cover-letter          # cover-letter | application-answer | statement | interview-prep | cold-email
role_type: graduate-scheme  # internship | graduate-scheme | placement | research | other
org: corrin-rail            # registry slug, or general
words: 412
source: "inbox/Corrin Rail cover letter.docx"
# restricted: <slug>        # only for an organisation's own assessment material
---
```

**Tracker row** (`applications/<cycle>/tracker.md`):

`| org | role | role_type | deadline | stage | applied | documents | outcome | notes |`

Stages: `researching`, `drafting`, `applied`, `test`, `interview`,
`assessment-centre`, `offer`, `rejected`, `withdrawn`.

**Story usage** (`applications/<cycle>/story-usage.jsonl`, one JSON object per
line, append-only):

`{"story_id": "...", "org_slug": "...", "artifact": "...", "used_at": "<ISO 8601>"}`

**Windows:** where these files say `python3`, type `python` or `py`.
