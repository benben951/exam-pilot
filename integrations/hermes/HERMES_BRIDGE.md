# Hermes Bridge For ExamPilot

Purpose: let the Feishu-connected Hermes bot use ExamPilot as the study backend.

## Recommended Connection Levels

### Level 1: Skill / Context Injection

Add this file or `EXAMPILOT_ECONOMICS_SKILL.md` to Hermes shared context:

```toml
[hermes]
shared_context_files = [
  "C:/Users/jie13/Documents/Playground/exam-pilot/integrations/hermes/EXAMPILOT_ECONOMICS_SKILL.md"
]
```

Use this for quick Feishu chat:

- explain economics concepts;
- route questions to the right study workflow;
- enforce source-grounded answers;
- avoid turning Feishu into vague chatting.

### Level 2: HTTP API Bridge

Keep ExamPilot running:

```powershell
cd C:\Users\jie13\Documents\Playground\exam-pilot
python server.py
```

Hermes can call:

- `GET http://127.0.0.1:8765/api/materials/search?q=效用函数&limit=8`
- `GET http://127.0.0.1:8765/api/materials/detail?id=<material_id>`
- `GET http://127.0.0.1:8765/api/tasks`
- `POST http://127.0.0.1:8765/api/memory`
- `POST http://127.0.0.1:8765/api/records`

Use this when the user asks:

- "从我的资料里找..."
- "保存这个错因"
- "今天 831 学什么"
- "把这个知识点加入长期记忆"

### Level 3: MCP / Codex Executor

Hermes can invoke Codex CLI as executor. Codex then uses its configured MCP tools.

Important:

- Hermes does not automatically inherit this desktop chat's MCP tools.
- MCP servers must be configured in the Codex CLI config used by Hermes.
- Do not expose secrets, browser cookies, or auth files to Hermes prompts.
- Prefer ExamPilot HTTP API for learning workflows before giving Hermes raw filesystem access.

## Safe Routing

Feishu message examples:

- `831 查资料 效用函数`
- `831 讲解 Slutsky 方程`
- `831 出题 CES 效用函数 3道`
- `831 错题复盘：...`
- `831 保存记忆：...`
- `831 今日任务`

Hermes should route these to the economics skill, not the generic coding pipeline.

## Voice

Feishu can carry audio messages, but voice learning needs an extra ASR/TTS bridge:

1. receive Feishu audio message;
2. download audio resource by file key;
3. transcribe with Whisper / faster-whisper / another ASR;
4. send text to Hermes route;
5. optionally synthesize reply with TTS;
6. upload audio and send an `audio` message back.

Start with voice-to-text only. Full two-way voice is useful later but not necessary for exam prep.
