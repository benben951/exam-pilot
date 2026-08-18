# Open Source Radar

Last updated: 2026-05-24

This file records useful ideas from recent open-source agent projects and maps them to ExamPilot.

## tinyhumansai/openhuman

Source: https://github.com/tinyhumansai/openhuman

Core ideas:

- local-first Memory Tree;
- Obsidian-compatible Markdown vault;
- integrated data connectors;
- periodic sync;
- token compression before LLM calls;
- desktop-first agent UX.

What ExamPilot should borrow:

- build a study Memory Tree from notes, OCR extracts, records, and weekly reviews;
- export durable `.md` files that can be opened in Obsidian;
- compress noisy material into small source-grounded chunks;
- keep the user in control of memory editing.

Near-term implementation:

- add `memory/export` to write memory observations as Markdown;
- add a material summary tree: subject -> topic -> source -> evidence;
- add a compression pass for noisy OCR / training ads / table-of-contents pages.

Do not copy blindly:

- 118+ integrations are not needed now;
- OAuth and managed connector complexity would distract from exam prep;
- mascot / meeting features are nice, but not a study priority.

## CloakHQ/CloakBrowser

Source: https://github.com/CloakHQ/CloakBrowser

Core ideas:

- browser automation reliability;
- source-level browser modifications;
- fingerprint differences matter;
- SDK compatibility with Playwright-style automation.

What ExamPilot should borrow:

- respect that browser automation can be fragile;
- keep UI tests simple and deterministic;
- isolate browsing automation from core learning data;
- add clear safety boundaries for web automation.

Safety boundary:

- ExamPilot should not use anti-detection tooling to bypass websites, CAPTCHAs, or access controls.
- For study use, browser automation should only test our own local app or access pages the user is allowed to view.

Near-term implementation:

- write stable local Playwright-style smoke tests later;
- keep RAG and OCR independent of browser scraping whenever possible.

## alchaincyf/huashu-md-html

Source: https://github.com/alchaincyf/huashu-md-html

Core ideas:

- Markdown is source code;
- HTML is a build artifact;
- many input formats can be converted into clean Markdown;
- good typography matters;
- anti-AI-slop design rules.

What ExamPilot should borrow:

- make Markdown the canonical study format;
- generate beautiful HTML reports from weekly review / subject maps;
- keep source Markdown editable;
- avoid generic AI-looking design.

Near-term implementation:

- add `export_study_report.py` to turn wiki notes into HTML;
- create report templates for weekly review, 831 topic map, and mistake book;
- keep PDF/DOCX/PPTX conversion as a later pipeline.

## guyoung/boxagnts

Source: https://github.com/guyoung/boxagnts

Core ideas:

- out-of-the-box agent toolbox;
- Rust-based runtime;
- WebAssembly sandbox;
- task execution with safer boundaries.

What ExamPilot should borrow:

- run risky or untrusted helpers in a bounded environment;
- separate "task definition" from "task execution";
- make agent actions auditable.

Near-term implementation:

- keep task board as the user-visible control plane;
- add execution logs for OCR/card/export jobs;
- later consider a sandbox for third-party conversion tools.

## Priority For ExamPilot

1. OpenHuman-style study Memory Tree.
2. Huashu-style Markdown-to-HTML reports.
3. BoxAgnts-style task logs and execution boundaries.
4. CloakBrowser only as a reminder to keep browser automation isolated and ethical.

## Concrete Backlog

- Build Memory Tree export for `Exam-Wiki`.
- Add source-grounded HTML weekly report.
- Add OCR/card generation task logs.
- Add a stable local UI smoke test.
- Add a noise-compression pass for OCR and flashcard generation.
