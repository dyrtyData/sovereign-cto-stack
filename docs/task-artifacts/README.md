# Task artifacts (hard copies)

Hard copies of the HumanLayer / RPI planning artifacts for each task that touched this repo —
research, design discussion, structure outline, the originating Linear ticket, and the PR
description/walkthrough. They are the durable "why" behind the commits.

## Why these are tracked (NOT gitignored)

`repomix` / `gitingest` (and similar repo-flatteners) **skip gitignored paths**. We want this
planning context flattened into an LLM's working set alongside the code, so these files are
deliberately **committed and tracked** — never added to `.gitignore`.

## Layout — one folder per task

```
docs/task-artifacts/<task-slug>/
├── 00-ticket.md              # originating Linear ticket
├── 01-research-questions.md
├── 02-research.md
├── 03-design-discussion.md
├── 04-structure-outline.md   # (NN-… if a task has multiple outlines)
├── 05-pr-description.md       # the merged PR's description (if any)
└── *.html                     # any inline previews/walkthroughs
```

`<task-slug>` matches the HumanLayer task name (e.g. the Linear branch slug).

## Adding a new task's artifacts (do this per task, after merge)

1. Copy the task's `.humanlayer/tasks/<task>/` files into a new `docs/task-artifacts/<task-slug>/`,
   renaming `ticket.md` → `00-ticket.md` and keeping the `NN-` numbering.
2. **Strip anything non-public first** — this repo is public (AGENTS.md rule 8): run `gitleaks`
   and grep for real keys/tokens/passwords/emails/absolute local paths. Reference key *formats*
   (e.g. `sk_test_…`) are fine; real values are not.
3. Commit on `main` (the tracked decision record); the pre-commit gitleaks hook is the backstop.
