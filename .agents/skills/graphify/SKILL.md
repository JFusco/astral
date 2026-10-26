---
name: graphify
description: Use this repository's shared Graphify code map for current relationships in the maintained backend, frontend, tests, scripts, and root configuration; verify exact behavior in source and rationale in docs/.
---

# Graphify code map

Use Graphify 0.9.36 from the repository root. Keep the current
`.graphifyignore` corpus and shared `graphify-out/` artifacts. The code map
is separate from the Markdown documentation in `docs/`.

- For broad current-code questions, run `graphify query "<question>"`.
  Use `graphify explain "<symbol>"`, `graphify path "<from>" "<to>"`, or
  `graphify affected "<symbol>"` for focused relationships and impact.
- Follow returned file and line references into source. Confirm `INFERRED`
  and `AMBIGUOUS` relationships there. Inspect exact named files and commands
  directly; use `docs/` for rationale and history.
- After eligible code changes, pulls, or merges, run
  `PYTHONHASHSEED=0 graphify update .`. Native post-commit and post-checkout
  hooks refresh the graph in the background; review output before staging.
  Stage `graphify-out/` changes only from the primary checkout: community
  assignments depend on the checkout directory name, so a differently named
  linked worktree produces churn, not code changes.
- On a fresh clone, install dependencies and run `graphify hook install`.
  Verify with `graphify hook status`. Keep the existing code corpus and native
  Git hooks; no agent tool hooks are installed.
- Keep `graphify-out/memory/` empty. Optional query outcomes belong in
  ignored `graphify-out/local-memory/` via `--memory-dir`.

ASTRAL needs Graphify 0.9.36; the corpus has no SQL, so no parser extra is
required. Graph relationships are not broker, trading or verification evidence.
