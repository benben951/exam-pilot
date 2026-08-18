# ExamPilot Architecture

## V0

V0 is Markdown-native:

- `Exam-Wiki` and `IELTS-Wiki` are the knowledge base.
- Scripts create indexes, flashcards, and quizzes.
- Codex skills provide the tutoring workflow.

## V1

Add retrieval:

- chunk Markdown and extracted PDF text;
- search by keyword first;
- later add embeddings/vector search;
- answer with source paths.
- compress noisy extracted text before generating cards.

Recommended retrieval shape:

- search results first;
- timeline / source evidence second;
- full material detail third.

OpenHuman-inspired memory shape:

- subject tree;
- topic summaries;
- source evidence links;
- editable Markdown exports.

## V2

Add learning intelligence:

- mastery score by topic;
- spaced repetition;
- mistake trend analysis;
- weekly planning agent.

Recommended agent patterns:

- persistent memory for decisions and weak points;
- skill-driven study workflows;
- separate queue for OCR / quiz / export jobs;
- task board for visible progress.
- execution logs for every background job.

## V3

Add product layer:

- web dashboard;
- study session mode;
- graph view of topic dependencies;
- GitHub-ready demo data.
- Markdown-to-HTML study reports.

Optional future layer:

- voice capture and spoken summaries;
- background workers for long OCR runs;
- multi-agent orchestration only after retrieval is stable.
- sandboxed helper execution for third-party converters.
