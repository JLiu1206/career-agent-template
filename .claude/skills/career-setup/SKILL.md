---
name: career-setup
description: First-time setup for the career agent. Reads the student's CV and past applications from inbox/, builds their profile, story bank and voice samples, and asks them to approve each file before writing it. Use when the student runs /career-setup, says they are new, or profile/profile.md does not exist. Also use to refresh the profile after the CV changes.
---

# Career setup

You turn a student's CV and past writing into the files every draft is built
from:

- `profile/` (facts with sources)
- `style/` (their own writing as voice samples)
- an empty tracker

Run this in the main conversation. The student answers questions as you go.
Aim to take about 10 to 15 minutes of their time:

- Batch your questions. Never ask document by document.
- Show summaries, not whole files.

Read `CLAUDE.md` first. Its sourcing and privacy rules apply to everything
here.

## 0. Before you start

Tell the student, in three short lines:

- what happens next
- that nothing goes into `profile/` or `style/` until they approve it
- to keep their copy of this repo private, because it will hold their CV

If `profile/profile.md` already exists, you are in **update mode**:

- Never overwrite a file.
- For each file, show what you would add or change, and write only the
  parts they approve.
- Leave existing `resolutions.md` entries alone.

## 1. Check the tools

Run `python3 --version`. On Windows, try `python --version` or
`py --version`, and use whichever works for every script below. Then run
`pdftotext -v`. If it's missing that's fine: PDFs get read with the Read
tool instead.

## 2. Get the documents

If `inbox/` holds nothing but `README.md`, ask the student to choose one:

- Drag their CV and any past cover letters, application answers or
  statements into the `inbox/` folder, then say "done".
- Paste their CV text into the chat. On their say-so, save it as
  `inbox/cv-pasted.md`.

Then run:

```
python3 scripts/extract-docs.py inbox --out .setup
```

Read `.setup/manifest.json`. Then:

- For each `ok` entry, read `.setup/<text_file>`.
- For each `needs-read-tool` entry (usually a PDF), read the original file
  in `inbox/` with the Read tool.
- Tell the student which `unsupported` files you skipped.

## 3. Sort the documents

Work out which file is the CV. If there are several, ask which is current.

Classify every other document:

- **The student's own writing.** Record its `type`, `role_type` and the
  organisation it was for. The types are:
  - `cover-letter`
  - `application-answer`
  - `statement`
  - `interview-prep`
  - `cold-email`
- **Not their writing.** It goes to `style/quarantine/` and never becomes a
  voice sample:
  - pasted chatbot output (look for "Here's an improved version",
    "Certainly!", or a sudden change of voice)
  - blank templates
  - someone else's CV or letter
  - the other side's text, such as a job description, a case brief or
    assessment instructions
- **Restricted.** An organisation's own assessment material (a case study
  they set, test questions) is marked `restricted: <slug>`. It can only
  be used for that organisation.

**Dates** come from the manifest's `created` field (the date the document was
written), never from a date printed in the text. Where `date_source` is
`file-mtime`, the date is a guess. Say so in the exemplar's front matter.

## 4. Ask once

Ask these together, in one round:

1. What are you applying for in this cycle? Choose role types (internship,
   graduate scheme, placement, research) and sectors in your own words.
   This becomes "What counts as an application" in `CLAUDE.md`.
2. What should the cycle be called? Suggest the year the roles start, for
   example `2027`.
3. Is anything on the CV out of date or wrong?
4. Any conflicts you found between documents. For example, a grade or a
   result stated differently in two places: ask which is right.
5. In a sentence or two, what draws you to the roles you're applying for?
   This goes in Motivations and interests as `[src: student, <date>]`.

Record the answers to 3 and 4 in `resolutions.md` as
`[src: student, <YYYY-MM-DD>]`.

## 5. Build the proposals

Write drafts to `.setup/proposals/`, not to `profile/` or `style/`.

### `profile.md`

Start with this front matter. `check-reuse.py` reads `name` and `address`
so that letterheads don't count as reuse.

```yaml
---
name: "<full name as on the CV>"
address: "<address line as on the CV, or blank>"
updated: <YYYY-MM-DD>
---
```

Then add sections:

- Education
- Experience
- Projects
- Skills
- Activities and leadership
- Awards
- **Motivations and interests**: the student's own stated reasons and
  interests, quoted or closely paraphrased from their documents (for
  example "wants to work on bridges rather than just study them"), each
  with `[src:]`. Add their answer to question 5 in step 4. "Why us?"
  answers are built from this section, so don't leave it empty.

Write one fact per bullet, each ending `[src: inbox/<file>]`. Copy grades,
ranks, dates and titles exactly. Never round them.

### `story-bank.md`

Five to ten stories taken only from the student's own documents. Each
story is a `## <n>. \`<story-id>\`` heading followed by:

- a one-line summary
- **Situation / Action / Result**, as the documents tell it, with `[src:]`
- **Shows:** the competencies it shows (for example teamwork,
  leadership, problem solving, resilience, communication, technical depth)
- **Wear:** 0

Don't fill a missing result with a guess. Write "result not recorded"
instead.

### `strengths-gaps.md`

A frank, specific read of:

- where the profile is strong for the role types they named
- where it is thin
- what would close each gap

Label it as Claude's assessment for the student to correct.

### `resolutions.md`

The answers from step 4, dated.

### Exemplars

One file per own-writing document in `style/exemplars/`, named
`<authored>__<type>__<role_type>__<org>.md`. Use the front matter in
`CLAUDE.md`, then the document's text exactly as written. Don't fix
typos. Also write `style/exemplar-index.md` as a table of them.

### `style-profile.md`

Cover:

- a voice summary (5 lines)
- structure by document type
- diction: spelling variety, contractions, sentence length
- signature moves, quoted from the exemplars
- things they never do

End with a `## Genre exemptions` section listing patterns that are correct
for them and that the voice pass must keep. Examples: a tricolon they
really use, confident claims with figures, their usual sign-off.

### Quarantine notes

For each excluded document, write a one-paragraph reason, to go to
`style/quarantine/<name>.md`.

### No past writing at all

This is common in first year. Ask the student to write about 150 words, in
the chat, answering "Why did you choose your degree?". Save it as an
exemplar with:

- `type: statement`
- `role_type: other`
- `date_source: student`
- `source: "written during setup"`

Tell them drafts will get closer to their voice once real applications are
saved.

## 6. Approve, then write

Show one short summary per file:

- `profile.md`: number of facts, and the three most important
- `story-bank.md`: the story ids with their one-liners
- `strengths-gaps.md`: the two headline points
- exemplars: the count, plus anything quarantined and why
- `style-profile.md`: the 5-line voice summary

Ask once: approve all, or name what to change. Make the changes they ask
for. Then write the approved files into `profile/` and `style/`.

## 7. Finish the wiring

1. Write `profile/current-cv.md` from the CV's manifest entry:

   ```yaml
   ---
   source_path: "inbox/<cv file name>"
   sha256: "<sha256 from manifest>"
   size_bytes: <size_bytes from manifest>
   recorded: <YYYY-MM-DD>
   ---
   ```

   Then run `python3 scripts/check-profile-staleness.py`. It must print
   `CURRENT`.
2. In `CLAUDE.md`:
   - replace the `**Active cycle:**` value with the cycle name
   - replace the line under `## What counts as an application` with their
     answer
3. Create `applications/<cycle>/tracker.md` with a title, the stages line
   from `CLAUDE.md`, and the table header row.
4. Create an empty `applications/<cycle>/story-usage.jsonl`.
5. If they have past submissions for this cycle, save each one's text as
   `applications/<cycle>/<slug>/submitted-<type>.md` so the reuse check can
   see it. Resolve each slug with `scripts/resolve-slug.py` and add the
   registry rows.

## 8. Hand over

Finish in four lines:

- what was built (counts)
- where to correct things (`profile/` and `style/` are theirs to edit)
- a reminder to keep the repo private
- the exact first command to try, fitted to what they said they're
  applying for, for example:
  `/apply 250-word answer to "Why do you want to join our graduate scheme?" for <organisation>`
