import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


def read_text(path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def infer_subject(path):
    lowered = str(path).lower()
    if "math" in lowered:
        return "math"
    if "english" in lowered:
        return "english"
    if "professional-course" in lowered or "economics" in lowered:
        return "economics"
    if "politics" in lowered:
        return "politics"
    if "ielts" in lowered:
        return "ielts"
    return "general"


def clean_cell(text):
    return re.sub(r"\s+", " ", text.strip())


def cards_from_markdown_tables(text, source, subject):
    cards = []
    lines = text.splitlines()
    current_heading = ""
    for line in lines:
        if line.startswith("##"):
            current_heading = line.lstrip("#").strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        if "---" in line:
            continue
        cells = [clean_cell(cell) for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0] in {"模块", "主题", "Subject"}:
            continue
        topic = cells[0]
        prompt = " / ".join(cells[:2])
        answer = "；".join(cells[2:])
        stable = hashlib.sha1(f"{source}:{prompt}:{answer}".encode("utf-8")).hexdigest()[:12]
        cards.append(
            {
                "id": stable,
                "subject": subject,
                "topic": topic,
                "card_type": "qa",
                "front": f"{prompt} 的核心要求是什么？",
                "back": answer,
                "source": str(source),
                "difficulty": 2,
                "tags": [current_heading] if current_heading else [],
                "created_at": date.today().isoformat(),
            }
        )
    return cards


def cards_from_bullets(text, source, subject):
    cards = []
    current_heading = ""
    for line in text.splitlines():
        if line.startswith("##"):
            current_heading = line.lstrip("#").strip()
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        item = stripped[2:].strip()
        if len(item) < 12 or len(item) > 140:
            continue
        if item.startswith("`") or item.startswith("[") or "\\" in item or "/" in item:
            continue
        if current_heading.lower() in {"references", "参考资料", "当前本地可抽取文本主要来自", "2018-2023 真题高频信号"}:
            continue
        stable = hashlib.sha1(f"{source}:{current_heading}:{item}".encode("utf-8")).hexdigest()[:12]
        cards.append(
            {
                "id": stable,
                "subject": subject,
                "topic": current_heading or "general",
                "card_type": "qa",
                "front": f"回忆要点：{current_heading or 'general'}",
                "back": item,
                "source": str(source),
                "difficulty": 1,
                "tags": [current_heading] if current_heading else [],
                "created_at": date.today().isoformat(),
            }
        )
    return cards


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    text = read_text(source)
    subject = infer_subject(source)
    cards = cards_from_markdown_tables(text, source, subject) + cards_from_bullets(text, source, subject)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for card in cards:
            handle.write(json.dumps(card, ensure_ascii=False) + "\n")
    print(f"Generated {len(cards)} cards -> {out}")


if __name__ == "__main__":
    main()
