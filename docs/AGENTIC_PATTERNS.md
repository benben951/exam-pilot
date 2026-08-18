# Agentic Patterns We Can Reuse

Last updated: 2026-05-19

This note maps recent agent repositories to ExamPilot ideas we can actually use.

## 1. Karpathy-style skills

Repo signals:

- `forrestchang/andrej-karpathy-skills`
- behavior rules, `SKILL.md`, `CLAUDE.md`, Cursor rule, top-level guidance

What to borrow:

- think before coding;
- search source-of-truth docs before inventing;
- keep changes surgical;
- ask for proof or examples before long answers.

ExamPilot use:

- make study skills compact and enforceable;
- require source-backed answers;
- keep “do first attempt yourself” as the default rule.

## 2. Hermes Agent

Repo signals:

- `NousResearch/hermes-agent`
- persistent agent setup;
- skills system;
- memory;
- MCP integration;
- parallel subagents;
- many terminal backends.

What to borrow:

- long-running worker model;
- task decomposition into subagents;
- skill loading as procedural memory;
- remote and local execution options.

ExamPilot use:

- background jobs for OCR, card generation, and weekly reviews;
- separate workers for parsing, tagging, and quiz generation;
- future support for remote execution if the local machine is busy.

## 3. Claude-Mem

Repo signals:

- `thedotmack/claude-mem`
- lifecycle hooks;
- SQLite;
- FTS / hybrid search;
- 3-layer retrieval: search -> timeline -> full detail;
- progressive disclosure;
- context injection.

What to borrow:

- compact index first, full detail only on demand;
- memory should be searchable and time-aware;
- context should be injected only when relevant.

ExamPilot use:

- `materials/search` as the first pass;
- `materials/detail` only after click;
- session memory for study decisions, weak points, and OCR failures;
- lightweight observation log instead of dumping huge raw notes.

## 4. Multica

Repo signals:

- `multica-ai/multica`
- managed agents platform;
- board, issues, task queue;
- daemon/runtime separation;
- progress tracking;
- skill compounding over time.

What to borrow:

- agent work should be visible on a board;
- tasks need statuses, owners, and handoffs;
- runtime should be separate from UI;
- reusable skills should compound.

ExamPilot use:

- OCR backlog board;
- weekly review tasks with status;
- future “parse / review / quiz / export” queues;
- one place to see what the system is doing now.

## 5. Voicebox

Repo signals:

- `jamiepine/voicebox`
- local-first voice studio;
- dictation;
- speech output;
- MCP-aware agent voice;
- API-first integration.

What to borrow:

- voice as input, not just output;
- local-first privacy;
- one voice stack for dictation + assistant replies;
- agent can speak back useful summaries.

ExamPilot use:

- dictation for quick错题/诊断录入;
- spoken weekly review summaries;
- mobile-friendly capture later.

## Practical Priority for ExamPilot

1. `Claude-Mem` retrieval shape.
2. `Hermes` long-running worker + skills.
3. `Multica` task board + orchestration.
4. `Karpathy` behavior rules.
5. `Voicebox` only if we really want audio input/output.

## What Not To Copy Blindly

- big orchestration before the data is clean;
- complex multi-agent chains before we have stable retrieval;
- voice features before the text pipeline is reliable;
- skills that are only slogans and have no tests or runnable checklist.
