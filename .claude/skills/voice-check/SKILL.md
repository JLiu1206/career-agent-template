---
name: voice-check
description: Make application text sound like the student who is sending it, using their own past writing as the guide, and remove stock phrasing that makes answers sound generic. Never changes a fact, number or name. Use after drafting any application text, or when the student asks to make a draft sound more like them.
---

# Voice check

The goal is an answer that sounds like this particular student on a good
day. It's not about hiding how the draft was made. The student reads and
edits every draft before sending it.

## Inputs

- The draft.
- The raw text of the student's own writing samples. The writer passes the
  two exemplars it chose. If you're run on your own, use the two most
  recent files in `style/exemplars/`.
- The `## Genre exemptions` section of `style/style-profile.md`, if present.

## Order of authority

1. **The student's own samples.** If they write in a way that the list below
   calls a tell, they keep it. Examples: em dashes, a three-part list,
   "passionate".
2. **The genre exemptions.**
3. **The list of tells below.**

## Steps

1. **Read the samples. Note:**
   - typical sentence length and how much it varies
   - British or American spelling
   - contractions or none
   - how they open and close
   - how they state results (numbers first, or story first)
   - any recurring habits
2. **Read the draft against those notes.** Mark the sentences that don't
   sound like the samples.
3. **Mark every tell from the list below**, unless step 1 shows the student
   uses it.
4. **Rewrite only the marked sentences.** Keep:
   - every fact, number, name, date, rank and title exactly as it was
   - the meaning
   - the word limit
5. **Read the result once more against the samples.**

## Tells to remove

1. **Stock openers.** For example "I am thrilled to apply", "I have always
   been passionate about", "From a young age". Start with something
   specific instead.
2. **Inflated words.** For example delve, leverage, tapestry, pivotal,
   testament, foster, showcase, underscore, vibrant, meticulous, seamless,
   "navigate the landscape". Use the plain word.
3. **Padding about importance.** For example "plays a crucial role", "in
   today's fast-paced world".
4. **Trailing -ing commentary.** For example "..., demonstrating my ability
   to lead", "..., highlighting my commitment". Either show it or cut it.
5. **"It's not just X, it's Y"** and similar set-ups.
6. **Lists of three that the student's samples don't use.**
7. **Em dashes, if the samples use none.**
8. **Vague attributions.** For example "experts say", "it is widely
   recognised".
9. **Praise that would fit any organisation.** For example "innovative
   culture", "commitment to excellence". Swap in a specific detail from
   `orgs/<slug>.md`, or cut it.
10. **Summary closers that restate the answer.** For example "Overall, this
    experience taught me...". End on something concrete.
11. **Stacked hedges.** For example "may potentially help to".
12. **Every sentence the same length and shape.** Vary it the way the
    samples do.
13. **Headings, bold or bullet points** in what should be prose.

## Genre exemptions (always allowed)

- Confident first-person claims that carry a concrete, sourced figure.
  Cover letters and statements are meant to sell.
- Conventional openings and closings: "Dear ...", "Kind regards",
  "Yours sincerely".
- Formal register where the samples are formal.

## Never

- Never change a fact, number, grade, rank, title, name or date.
- Never add a claim, example or detail that wasn't in the draft.
- Never describe this pass as a way to get past AI detection. Some
  employers ask applicants not to use AI tools, and the student is
  responsible for checking each employer's policy.

## Output

Return the revised text and a short list of what changed and why. When
called by the writer, save the revised text over the draft file.
