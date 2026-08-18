import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "economics_anki_cards.jsonl"


ECON_DECKS = [
    "831经济学::微观",
    "831经济学::宏观",
    "831经济学::真题",
    "831经济学::错题",
]


SYSTEM_PROMPT = """你是北大软微金融科技 831 经济学综合备考教练。
目标不是泛泛解释，而是把材料转成可用于考试输出的 Anki 卡片。
卡片必须服务：概念记忆、公式推导、模型框架、课后题套路、真题答题。
不要复制长段原文。不要编造书中没有的页码或题号。
"""


def load_dotenv(path: Path = ROOT / ".env.local") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def compact_text(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def stable_id(*parts: str) -> str:
    import hashlib

    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:12]


@dataclass
class LlmConfig:
    api_key: str
    base_url: str
    model: str


def get_llm_config() -> LlmConfig | None:
    api_key = (
        os.environ.get("ECON_LLM_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not api_key:
        return None
    base_url = (
        os.environ.get("ECON_LLM_BASE_URL")
        or os.environ.get("DEEPSEEK_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.deepseek.com"
    ).rstrip("/")
    model = os.environ.get("ECON_LLM_MODEL") or os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
    return LlmConfig(api_key=api_key, base_url=base_url, model=model)


def call_chat(config: LlmConfig, prompt: str, timeout: int = 90) -> str:
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def parse_json_cards(text: str) -> list[dict]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\[.*\]", cleaned, re.S)
    if match:
        cleaned = match.group(0)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("model output is not a JSON list")
    return [item for item in data if isinstance(item, dict)]


def heuristic_cards(text: str, topic: str, deck: str, source: str, limit: int) -> list[dict]:
    sentences = [
        item.strip()
        for item in re.split(r"[。！？；\n]", text)
        if 18 <= len(item.strip()) <= 180
    ]
    cards = []
    keywords = ["定义", "公式", "模型", "均衡", "效用", "需求", "供给", "IS", "LM", "通货膨胀", "增长", "福利"]
    chosen = [s for s in sentences if any(k in s for k in keywords)] or sentences
    for idx, sentence in enumerate(chosen[:limit]):
        card_type = "concept"
        if any(k in sentence for k in ["推导", "公式", "方程"]):
            card_type = "derivation"
        elif any(k in sentence for k in ["真题", "考法", "答题"]):
            card_type = "exam"
        cue = sentence[:28]
        cards.append(
            {
                "deck": deck,
                "topic": topic,
                "card_type": card_type,
                "front": f"【{topic}】围绕“{cue}...”应主动回忆什么？",
                "back": sentence,
                "exam_note": "复习时补充：定义、图形/公式、常见考法、易错点。",
                "source": source,
                "tags": ["831经济学", topic, card_type],
                "id": stable_id(source, topic, sentence),
            }
        )
    return cards


def llm_cards(text: str, topic: str, deck: str, source: str, limit: int) -> list[dict]:
    config = get_llm_config()
    if not config:
        return heuristic_cards(text, topic, deck, source, limit)
    prompt = f"""
请把下面材料转成 {limit} 张以内 Anki 卡片。

主题：{topic}
目标牌组：{deck}
来源：{source}

输出严格 JSON 数组，每个元素包含：
deck, topic, card_type, front, back, exam_note, source, tags

card_type 只能从 concept / formula / derivation / model / exam / mistake 中选。
front 要短，适合主动回忆。
back 要包含考试作答需要的关键点，但不要复制长段材料。
exam_note 写软微 831 可能怎么考、易错点或答题动作。

材料：
{compact_text(text, 6000)}
""".strip()
    try:
        raw = call_chat(config, prompt)
        cards = parse_json_cards(raw)
    except Exception as error:
        print(f"LLM unavailable, using local heuristic cards. reason={error}", file=sys.stderr)
        return heuristic_cards(text, topic, deck, source, limit)
    normalized = []
    for item in cards[:limit]:
        front = str(item.get("front") or "").strip()
        back = str(item.get("back") or "").strip()
        if not front or not back:
            continue
        item["deck"] = str(item.get("deck") or deck)
        item["topic"] = str(item.get("topic") or topic)
        item["card_type"] = str(item.get("card_type") or "concept")
        item["source"] = str(item.get("source") or source)
        tags = item.get("tags") or ["831经济学", topic, item["card_type"]]
        item["tags"] = [clean_tag(str(tag)) for tag in tags if str(tag).strip()]
        item["id"] = stable_id(item["source"], item["topic"], front, back)
        normalized.append(item)
    return normalized


def clean_tag(tag: str) -> str:
    return re.sub(r"\s+", "_", tag.strip())


def write_jsonl(cards: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for card in cards:
            handle.write(json.dumps(card, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    cards = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cards.append(json.loads(line))
    return cards


def anki_request(action: str, params: dict | None = None, anki_url: str = "http://127.0.0.1:8765") -> dict:
    body = json.dumps({"action": action, "version": 6, "params": params or {}}).encode("utf-8")
    request = urllib.request.Request(
        anki_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "error" not in data or "result" not in data:
        raise RuntimeError("The endpoint responded, but it does not look like AnkiConnect.")
    if data["error"]:
        raise RuntimeError(data["error"])
    return data


def ensure_decks(decks: list[str], anki_url: str) -> None:
    existing = set(anki_request("deckNames", anki_url=anki_url)["result"])
    for deck in decks:
        if deck not in existing:
            anki_request("createDeck", {"deck": deck}, anki_url=anki_url)


def pick_basic_model(anki_url: str) -> str:
    models = anki_request("modelNames", anki_url=anki_url)["result"]
    for candidate in ("Basic", "基本"):
        if candidate in models:
            return candidate
    if models:
        return models[0]
    return "Basic"


def model_fields(model_name: str, anki_url: str) -> list[str]:
    try:
        return anki_request("modelFieldNames", {"modelName": model_name}, anki_url=anki_url)["result"]
    except Exception:
        return ["Front", "Back"]


def card_to_note(card: dict, model_name: str = "Basic", fields: list[str] | None = None) -> dict:
    deck = card.get("deck") or "831经济学::微观"
    tags = [clean_tag(tag) for tag in card.get("tags", [])]
    if "831经济学" not in tags:
        tags.insert(0, "831经济学")
    fields = fields or ["Front", "Back"]
    front_field = "Front" if "Front" in fields else ("正面" if "正面" in fields else fields[0])
    back_field = "Back" if "Back" in fields else ("背面" if "背面" in fields else (fields[1] if len(fields) > 1 else fields[0]))
    return {
        "deckName": deck,
        "modelName": model_name,
        "fields": {
            front_field: str(card.get("front") or ""),
            back_field: format_back(card),
        },
        "options": {"allowDuplicate": False, "duplicateScope": "deck"},
        "tags": tags,
    }


def format_back(card: dict) -> str:
    parts = [
        str(card.get("back") or "").strip(),
        "",
        f"<b>考试提示：</b>{str(card.get('exam_note') or '复习时补充常见考法和易错点。').strip()}",
        f"<br><b>来源：</b>{str(card.get('source') or '').strip()}",
        f"<br><b>主题：</b>{str(card.get('topic') or '').strip()}",
    ]
    return "<br>".join(part for part in parts if part is not None)


def sync_cards(cards: list[dict], anki_url: str, verbose: bool = False) -> tuple[int, int]:
    ensure_decks(sorted({str(card.get("deck") or "831经济学::微观") for card in cards} | set(ECON_DECKS)), anki_url)
    basic_model = pick_basic_model(anki_url)
    fields = model_fields(basic_model, anki_url)
    added = 0
    failed = 0
    for card in cards:
        note = card_to_note(card, basic_model, fields)
        try:
            result = anki_request("addNote", {"note": note}, anki_url=anki_url)["result"]
            if result:
                added += 1
        except Exception as error:
            if verbose:
                first_field = next(iter(note["fields"].values()), "")
                print(f"Skipped: {first_field[:60]} -> {error}", file=sys.stderr)
            failed += 1
    return added, failed


def command_generate(args: argparse.Namespace) -> None:
    load_dotenv()
    text = read_text(Path(args.input)) if args.input != "-" else sys.stdin.read()
    source = args.source or args.input
    cards = llm_cards(text, args.topic, args.deck, source, args.limit)
    write_jsonl(cards, Path(args.out))
    print(f"Generated {len(cards)} cards -> {args.out}")


def command_sync(args: argparse.Namespace) -> None:
    cards = read_jsonl(Path(args.input))
    try:
        added, failed = sync_cards(cards, args.anki_url, verbose=args.verbose)
    except urllib.error.URLError as error:
        raise SystemExit(
            "Cannot reach AnkiConnect. Open Anki, install/enable AnkiConnect, and make sure port 8765 is not occupied by ExamPilot.\n"
            f"Details: {error}"
        )
    print(f"Synced to Anki. added={added}, skipped_or_failed={failed}")


def command_check_anki(args: argparse.Namespace) -> None:
    try:
        names = anki_request("deckNames", anki_url=args.anki_url)["result"]
    except Exception as error:
        raise SystemExit(
            "AnkiConnect is not ready. Open Anki and check the AnkiConnect add-on.\n"
            f"Details: {error}"
        )
    print("AnkiConnect OK")
    print(f"Deck count: {len(names)}")


def command_create_decks(args: argparse.Namespace) -> None:
    ensure_decks(ECON_DECKS, args.anki_url)
    print("Created/verified decks:")
    for deck in ECON_DECKS:
        print(f"- {deck}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and sync 831 economics Anki cards.")
    sub = parser.add_subparsers(required=True)

    generate = sub.add_parser("generate", help="Generate economics cards from a text/markdown file.")
    generate.add_argument("--input", required=True, help="Input text/markdown path, or '-' for stdin.")
    generate.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSONL path.")
    generate.add_argument("--topic", required=True, help="Topic, e.g. 微观::消费者理论.")
    generate.add_argument("--deck", default="831经济学::微观", help="Target Anki deck.")
    generate.add_argument("--source", default="", help="Human-readable source label.")
    generate.add_argument("--limit", type=int, default=12, help="Max number of cards.")
    generate.set_defaults(func=command_generate)

    sync = sub.add_parser("sync", help="Sync generated JSONL cards to Anki through AnkiConnect.")
    sync.add_argument("--input", default=str(DEFAULT_OUT), help="Input JSONL path.")
    sync.add_argument("--anki-url", default="http://127.0.0.1:8765", help="AnkiConnect URL.")
    sync.add_argument("--verbose", action="store_true", help="Print skipped card reasons.")
    sync.set_defaults(func=command_sync)

    check = sub.add_parser("check-anki", help="Check whether AnkiConnect is available.")
    check.add_argument("--anki-url", default="http://127.0.0.1:8765", help="AnkiConnect URL.")
    check.set_defaults(func=command_check_anki)

    decks = sub.add_parser("create-decks", help="Create the default 831 economics decks.")
    decks.add_argument("--anki-url", default="http://127.0.0.1:8765", help="AnkiConnect URL.")
    decks.set_defaults(func=command_create_decks)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    start = time.time()
    args.func(args)
    elapsed = time.time() - start
    print(f"Done in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
