# ExamPilot

Local-first AI learning operating system for exam prep, IELTS, technical learning, and competition study.

This project starts as a real study system and can grow into a broader local-first learning product.

## Current Scope

- Index local Markdown study notes.
- Generate active-recall flashcards from compact notes.
- Quiz from flashcards.
- Keep the door open for RAG, knowledge graph, mastery tracking, and a web UI.

## Quick Start

### Web App

Double-click:

```text
启动 ExamPilot.bat
```

Or run:

```powershell
cd C:\Users\jie13\Documents\Playground\exam-pilot
python server.py
```

Open:

```text
http://127.0.0.1:8765
```

The current web version runs fully in the browser and stores data in `localStorage`.
It can be shared as static files or deployed to any static hosting service.

### AI API

The local backend now exposes:

- `/api/ai/analyze`
- `/api/materials/search`
- `/api/materials/detail`
- `/api/records`
- `/api/weaknesses`
- `/api/tasks`
- `/api/memory`

Set an API key before starting if you want the web app to call OpenAI:

```powershell
Copy-Item .env.local.example .env.local
# edit .env.local
python server.py
```

Without `OPENAI_API_KEY`, the app still works locally but the AI analysis button will show a setup message.

The study UI can also search local materials, inspect source evidence, and persist diagnosis / weekly review records into `data/study_records.json`.
The Agent page persists task-board items into `data/agent_tasks.json` and long-term observations into `data/memory_observations.json`.
If the browser supports Web Speech, the Agent page can also dictate a memory note by voice.

### Study Operations Monitor

ExamPilot exposes `/api/monitoring`, a local-first monitoring layer that converts study records and task state into a seven-day operational report:

- study hours, active days, streak continuity, and average accuracy;
- mistake-rule coverage and subject coverage;
- overdue high-priority tasks;
- risk level, reasons, and next actions.

The report is a human-in-the-loop study aid. It does not make autonomous high-stakes decisions and does not upload private study records by default.

Run the focused tests and inspect the report locally:

```powershell
python -m unittest discover -s tests -v
python server.py
Invoke-RestMethod http://127.0.0.1:8765/api/monitoring
```

For OpenAI-compatible relay services, set `OPENAI_BASE_URL` in `.env.local`.

### WeChat Test Account

ExamPilot includes a WeChat callback endpoint:

```text
/api/wechat/callback
```

See:

```text
docs/WECHAT_TEST_ACCOUNT.md
```

### Phone Sharing

Local `127.0.0.1` only works on your own computer. For a friend to use it on a phone, deploy it with one of these:

- Static-only demo: GitHub Pages / Netlify / Vercel, no private local files.
- Full AI version: deploy the backend to a server or cloud platform and keep the API key server-side.
- Temporary LAN test: bind the server to your computer's LAN IP and let the phone join the same Wi-Fi.

### Scripts

```powershell
python .\scripts\index_notes.py --roots "C:\Users\jie13\Documents\Playground\Exam-Wiki" --out .\data\index.json
python .\scripts\generate_flashcards.py --input "C:\Users\jie13\Documents\Playground\Exam-Wiki\professional-course\softmicro-economics-topic-map.md" --out .\data\flashcards.jsonl
python .\scripts\quiz_flashcards.py --cards .\data\flashcards.jsonl --count 5
```

## Design Principles

- Local first.
- Source grounded.
- Active recall over rereading.
- Mistake diagnosis over vague explanation.
- Small useful notes over huge copied material.
- Real user workflow before product polish.

## Agentic References

ExamPilot keeps a lightweight pattern map in:

```text
docs/AGENTIC_PATTERNS.md
docs/OPEN_SOURCE_RADAR.md
```

Current priorities borrowed from recent agent projects:

- progressive retrieval before full context loading;
- persistent study memory;
- visible task queues for OCR and weekly review;
- skill-like workflows for each subject;
- browser voice capture for quick memory notes.
- OpenHuman-style memory tree and Huashu-style Markdown/HTML reports as next product directions.
