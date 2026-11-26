---
name: apply
description: Draft application text for one organisation (a form answer, cover letter, personal or research statement, interview prep, or a cold email to an academic) from the student's own facts and voice, then register it in the tracker once they approve. Use when the student runs /apply or asks for help with a specific application.
argument-hint: <what to write> for <organisation> [role] [word limit]
---

# Apply

You run one application from request to registered draft. The work goes to
two subagents:

- **`org-researcher`** finds out about the organisation.
- **`application-writer`** drafts from the student's files.

You talk to the student and you write the tracker. Read `CLAUDE.md` first.

## 1. Check setup

- If `profile/profile.md` doesn't exist, or the `**Active cycle:**` line in
  `CLAUDE.md` still says `not set`, stop. Tell the student to run
  `/career-setup`, or `python3 scripts/load-demo.py` to try the demo
  student.
- Run `python3 scripts/check-profile-staleness.py`. If it says `STALE`, tell
  the student their CV has changed since setup. Offer to update the profile
  first (`/career-setup` in update mode). If they want to go ahead anyway,
  note it in your final message.

## 2. Pin down the request

From the student's message, work out:

| Item | Required? |
|---|---|
| the organisation | required |
| the role | as named by the organisation |
| `role_type` | one of `internship`, `graduate-scheme`, `placement`, `research`, `other` |
| document type | one of `cover-letter`, `application-answer`, `statement`, `interview-prep`, `cold-email` |
| **the exact question or prompt** | required for answers and statements |
| **the word or character limit** | if there is one |
| deadline | optional |
| job text | optional, but offer: "Paste the job description if you have it; it helps." |

If the exact question or the limit is missing, ask for both together, in
one message. Don't guess a question's wording: a near-miss answer reads as
generic. Character limits: convert at about 6 characters per word, then
check characters at the end.

## 3. Resolve the organisation

Run `python3 scripts/resolve-slug.py "<organisation>"`.

- **`MATCH <slug>`**: use it.
- **`CREATE <slug>`**: add a row to `orgs/_registry.md` (slug in backticks,
  display name, kind, sector, aliases). Mention it in one line.
- **`ASK`**: ask the student whether it is the same organisation as the
  one it resembles. Use the existing slug if yes. Otherwise create the new
  one.

## 4. Research if needed

Dispatch `org-researcher` if either is true:

- `orgs/<slug>.md` doesn't exist
- its `researched:` date is more than 60 days old

Give it the slug, display name, kind, role, role type and any job text.
Tell the student it takes a minute or two. While it runs, say in one line
what the writer will do next.

## 4b. Check the organisation's AI policy

Read the `## AI tools policy` section of `orgs/<slug>.md`. If the
organisation asks applicants not to use AI tools for their application:

1. Quote the policy and its source to the student before drafting anything.
2. Recommend not submitting AI-drafted text to this organisation. Offer
   `interview-prep` instead: notes from their own story bank to practise
   from, not text to submit.
3. Draft submitted text only if the student explicitly says to go ahead
   after reading the policy. Note their decision in the tracker row's notes.

## 5. Draft

Dispatch `application-writer` with:

- the slug and display name
- the role and `role_type`
- the document type
- the exact question
- the limit
- the job text
- the active cycle

## 6. Show the student

From the writer's return block, show:

1. The draft text in full.
2. `WORDS`, `REUSE` and `EXEMPLARS`, one line each.
3. The source map. Each claim and where it came from, so they can see
   nothing was invented.
4. `MISSING FACTS`, if any. For each one, ask whether it's true.
   - If yes: propose an entry for `profile/resolutions.md` with
     `[src: student, <YYYY-MM-DD>]`. Write it once they approve, then send
     the writer a revision brief that uses it.
   - If no, or they're unsure: it stays out.

If `REUSE` is `ERROR`, show what the script printed and say the draft is not
cleared yet.

## 7. Revisions

For any change the student asks for, either:

- send a revision brief to `application-writer`, or
- for a small wording change, edit the draft yourself and re-run
  `python3 scripts/check-reuse.py <draft>`.

**A new claim follows the sourcing rules either way.** If the student asks
you to add something that isn't in their profile (for example "say I led a
team of 20"), don't add it. Ask whether it's true. If it is, propose
recording it in `resolutions.md` first, then use it.

## 8. Register

Ask: "Add this to your tracker?" On yes:

1. **The tracker row.** If `applications/<cycle>/tracker.md` already has a
   row for this organisation and role, update its documents and stage.
   Otherwise append the writer's `TRACKER ROW`. If the file doesn't exist,
   create it with the header from `CLAUDE.md`.
2. **The story-usage lines.** Append each `STORY USAGE` line to
   `applications/<cycle>/story-usage.jsonl`. Append only: never rewrite or
   reorder the file.
3. **Wear counts.** Increase the `Wear:` count in `profile/story-bank.md` for
   each story used. Show the change and write it only with the student's
   approval, since `profile/` is theirs.

## 9. Close

End with three short reminders:

- Read it aloud and change anything that doesn't sound like you. You're the
  one sending it.
- Check whether this employer allows AI help with written answers.
- When you submit, save the final text as
  `applications/<cycle>/<slug>/submitted-<type>.md`. Future reuse checks
  will then compare against what you actually sent.
