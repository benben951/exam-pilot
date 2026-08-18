# 831 经济学 Anki + DeepSeek 学习工作流

目标：用最少工具完成「教材理解 -> 卡片记忆 -> 做题输出 -> 错题复盘」。

## 工具分工

- PDF 阅读器：看尼克尔森、曼昆、做题本、真题。
- DeepSeek API：把小节、错题、真题解析生成 Anki 卡片初稿。
- Anki：每天复习概念、公式、模型、推导、真题问法。
- Codex：解释难点、批改答案、判断哪些卡片值得保留。

## Anki 牌组

脚本默认创建：

- `831经济学::微观`
- `831经济学::宏观`
- `831经济学::真题`
- `831经济学::错题`

## 安装 AnkiConnect

1. 打开 Anki 桌面版。
2. 工具 -> 插件 -> 获取插件。
3. 输入 AnkiConnect 插件代码：`2055492159`。
4. 重启 Anki。

注意：AnkiConnect 默认端口是 `8765`，和 ExamPilot 网页默认端口相同。
同步 Anki 时如果网页服务占用 `8765`，先关掉 ExamPilot 网页服务，或以后把 ExamPilot 改到别的端口。

## 配置 DeepSeek API

在 `.env.local` 里添加：

```text
DEEPSEEK_API_KEY=你的key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

也可以用已有 `OPENAI_API_KEY/OPENAI_BASE_URL`，脚本会自动读取。

## 生成卡片

从文本或 Markdown 生成卡片：

```powershell
python .\scripts\economics_anki.py generate `
  --input .\tmp\consumer-theory-notes.md `
  --topic "微观::消费者理论" `
  --deck "831经济学::微观" `
  --out .\data\economics_anki_cards.jsonl `
  --limit 12
```

如果没有配置 API，脚本会用本地规则生成简易卡片；配置 API 后会生成更适合考试输出的卡片。

## 同步到 Anki

确认 Anki 已打开且 AnkiConnect 可用：

```powershell
python .\scripts\economics_anki.py check-anki
```

创建默认牌组：

```powershell
python .\scripts\economics_anki.py create-decks
```

同步卡片：

```powershell
python .\scripts\economics_anki.py sync --input .\data\economics_anki_cards.jsonl
```

## 每天怎么用

1. 看教材或做题本 30-40 分钟。
2. 只摘 1 个小节或 1 道错题，不要一次塞太多。
3. 生成 5-12 张 Anki 卡。
4. 人工删掉低质量卡。
5. Anki 复习 10-15 分钟。
6. 每周至少写 1-2 道完整真题答案，再交给 Codex 批改。

## 卡片标准

好卡片：

- front 短，能触发主动回忆。
- back 包含定义、公式/图形、考法、易错点。
- 服务软微 831 的计算、证明、论述输出。

坏卡片：

- 大段复制教材。
- 问题太泛，比如「消费者理论是什么」。
- 只记结论，不记推导条件。
