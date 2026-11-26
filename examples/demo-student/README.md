# Demo student (fictional)

Ellis Varga is a **fictional** final-year MEng Mechanical Engineering student,
made up for demos. Every person, firm and research group here is invented,
except Arup. `orgs/arup.md` is a real `org-researcher` output from Arup's
public pages, kept as an example of what research looks like. It also
shows why the AI-policy check exists: Arup asks applicants not to use AI
writing tools.

This folder is what `/career-setup` would have produced from the documents in
`inbox/`. Load it with `python3 scripts/load-demo.py`, then try:

```
/apply 200-word answer to "Why do you want to join Corrin Rail's graduate scheme?" for Corrin Rail
```

`demo-props/planted-reuse-draft.md` copies one sentence from an earlier
application on purpose, to show the reuse check blocking it:

```
python3 scripts/check-reuse.py examples/demo-student/demo-props/planted-reuse-draft.md
```
