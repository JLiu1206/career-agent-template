# Career agent template

Write applications for internships, graduate schemes, industrial placements
and research positions. It works from your own facts and in your own voice,
inside Claude Code.

You drop in your CV and some past applications. It builds a profile in which
every fact has a source, and it learns how you write. Then you ask for an
answer:

```
/apply 250-word answer to "Why do you want to join our graduate scheme?" for <organisation>
```

It researches the organisation, drafts using only facts from your profile,
matches your voice using two of your own past documents, and checks you
haven't copied sentences from an earlier application. Then it shows you the
draft with a source for every claim.

## Before you start

- **Claude Code**, signed in. See [the Claude Code docs](https://code.claude.com/docs).
- **Python 3.** Check with `python3 --version`. On Windows, use `python` or
  `py` wherever this README says `python3`.
- **Optional:** `pdftotext` (macOS: `brew install poppler`). Without it,
  PDFs are still read, just by Claude instead of a script.

## Quickstart

1. **Get your own copy.** Pick one:
   - **npx** (macOS, Windows, Linux; needs Node 18+ and git):
     `npx github:JLiu1206/create-career-agent my-career-agent`
   - **Homebrew** (macOS, Linux):
     `brew install jliu1206/tap/career-agent`, then `career-agent my-career-agent`
   - **GitHub:** click **Use this template**, choose **Private**, and clone
     your copy.

   The npx and Homebrew installers start a fresh git history with no link
   back to this repo, so your CV can't be pushed here by accident.
2. **Add your documents.** `cd my-career-agent`, then put your CV and any
   past cover letters, application answers or statements into `inbox/`.
3. **Start Claude Code:** `claude`
4. **Set up:** type `/career-setup` and answer its questions. It takes about
   10 to 15 minutes. Nothing is saved to your profile until you approve it.
5. **Draft something real**, for example:
   - `/apply 250-word answer to "Why this scheme?" for <organisation>`
   - `/apply cover letter for the <organisation> summer internship`
   - `/apply cold email to the Vantmoor Lab asking about a summer UROP`

## Try it without your CV

```
python3 scripts/load-demo.py
claude
```

This loads a fictional demo student. Then try:
`/apply 200-word answer to "Why do you want to join Corrin Rail's graduate scheme?" for Corrin Rail`

The loader refuses to run if `profile/` or `inbox/` already holds your own
files.

## How it works

```
inbox/ (your CV + past writing)
   │  /career-setup  (you approve every file)
   ▼
profile/  facts, each with [src: file]      style/  your own writing as voice samples
story bank, strengths and gaps              voice rules + genre exemptions
   │
   │  /apply "<question>" for <organisation>
   ▼
org-researcher ──► orgs/<org>.md       (what they do, process, what they look for, sources)
application-writer
   1. loads your profile, the org file and exactly two of your own documents
   2. drafts using only facts that have a source
   3. voice pass: make it sound like your samples
   4. word limit
   5. reuse check: no 8 words in a row copied from your earlier writing
   6. returns the draft + a source for every claim
   ▼
you approve ──► applications/<cycle>/tracker.md
```

Four things keep it trustworthy:

1. **Facts live in files.** Every claim in a draft maps to a line in your
   profile. If it can't, it's cut. If you ask it to add something that isn't
   there, it asks whether it's true and records your answer first.
2. **Your voice, from your writing.** Drafts are matched to two of your own
   past documents, chosen by document type, role type and date.
3. **You own your profile.** Agents propose changes to `profile/` and
   `style/`. They never apply them without your approval.
4. **A deterministic reuse check.** `scripts/check-reuse.py` blocks any run
   of 8 consecutive words copied from an earlier application or from your
   past writing in `style/exemplars/`. Reusing a
   good story for different organisations is fine.

## What's in the repo

| Path | What |
|---|---|
| `.claude/skills/career-setup/` | `/career-setup`: builds your profile and voice samples |
| `.claude/skills/apply/` | `/apply`: one application from request to tracker row |
| `.claude/agents/application-writer.md` | drafts from your files |
| `.claude/agents/org-researcher.md` | researches employers and research groups, citing sources |
| `.claude/skills/voice-check/` | the voice pass |
| `scripts/` | slug resolver, reuse check, CV staleness check, document extractor, demo loader |
| `CLAUDE.md` | the rules every agent follows |
| `examples/demo-student/` | a fictional student, fully set up |

## Your data

- Everything stays in plain files in your copy of the repo. Edit them
  whenever something is wrong.
- When Claude reads a file, its contents are sent to Claude, just like
  pasting it into a chat.
- **Keep your copy private.** `inbox/` is git-ignored, but `profile/` and
  `applications/` are not, so that you get version history.
- Research searches only for organisations, never for you.

## Employer AI policies

Some employers ask applicants not to use AI tools for written answers.
The researcher looks for each organisation's policy, and `/apply` tells you
before drafting if one asks for no AI. Still check yourself before you use
a draft. Treat every draft as a
starting point: read it aloud, change what doesn't sound like you, and only
send what you would say in an interview.

## Troubleshooting

| Problem | Fix |
|---|---|
| `/career-setup` isn't recognised | Make sure you started `claude` inside the repo folder. Restart Claude Code if you just cloned it. |
| `python3: command not found` | On Windows, use `python` or `py`. Otherwise, install Python 3. |
| A PDF wasn't read | Install `pdftotext`, or let setup read it with the Read tool (it does this automatically). |
| The reuse check says ERROR | A file in `applications/` couldn't be read. Save its text as `.md` or `.txt`, or move it out. |
| "CV changed since setup" | Run `/career-setup` again. It shows what would change and asks first. |
| Drafts don't sound like you | Add more of your own past writing to `inbox/` and run `/career-setup` again, or edit `style/style-profile.md` directly. |

## Not included (yet)

- Syncing application emails into the tracker.
- CV writing.
- Psychometric test or assessment prep. This one is deliberate: the agent
  never builds a persona for you.

## Credits

Built by Jayden Liu for Claude Builders Club at Imperial College London. It
is adapted from the career agent the author uses for their own
applications. For a stronger general-purpose voice pass, see the
open-source `humanizer` skill for Claude Code.

MIT licence. See `LICENSE`.
