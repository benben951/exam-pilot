import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT.parent / "Exam-Wiki" / "raw" / "materials-file-index.json"
DEFAULT_DB = ROOT / "data" / "learning.db"
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".jsonl"}


SUBJECT_KEYWORDS = [
    ("数学", ["极限", "导数", "积分", "矩阵", "线性代数", "微分方程", "概率论", "高数", "数二", "二次型"]),
    ("英语一", ["阅读", "长难句", "翻译", "作文", "同义替换", "完形", "新题型", "考研英语", "张剑"]),
    ("831经济学", ["微观", "宏观", "经济学", "消费者", "生产者", "博弈", "委托代理", "Solow", "货币", "软微", "金融科技"]),
    ("政治", ["马原", "毛中特", "史纲", "思修", "肖八", "肖四", "时政", "选择题"]),
    ("高考语文", ["高考语文", "语文", "现代文", "文言文", "古诗", "作文", "病句", "成语", "阅读理解"]),
    ("高考数学", ["高考数学", "函数", "数列", "立体几何", "解析几何", "概率", "导数", "三角函数", "圆锥曲线"]),
    ("高考英语", ["高考英语", "完形填空", "语法填空", "七选五", "续写", "应用文", "英语阅读"]),
    ("高考历史", ["高考历史", "中国古代史", "中国近代史", "世界史", "史料", "历史解释", "唯物史观"]),
    ("高考政治", ["高考政治", "经济生活", "政治生活", "文化生活", "哲学", "中特", "主观题"]),
    ("高考地理", ["高考地理", "自然地理", "人文地理", "区域地理", "等值线", "气候", "地貌", "人口", "产业"]),
    ("雅思", ["IELTS", "雅思", "口语", "听力", "小作文", "大作文"]),
    ("技术/竞赛", ["Python", "模型", "baseline", "AUC", "Kaggle", "TAAC", "agent", "RAG", "GitHub"]),
]

SUBJECT_ALLOWED_TAGS = {
    subject: tags for subject, tags in SUBJECT_KEYWORDS
}

SUBJECT_ALLOWED_TAGS["831经济学"] = [
    "微观",
    "宏观",
    "经济学",
    "消费者",
    "生产者",
    "博弈",
    "委托代理",
    "Solow",
    "货币",
    "软微",
    "金融科技",
    "需求",
    "供给",
    "垄断",
    "效用",
    "成本",
    "投资",
]

SUBJECT_ALLOWED_TAGS["数学"] = [
    "极限",
    "导数",
    "积分",
    "矩阵",
    "线性代数",
    "微分方程",
    "概率论",
    "高数",
    "数二",
    "二次型",
    "函数",
    "数列",
    "解析几何",
]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS materials (
          id TEXT PRIMARY KEY,
          path TEXT UNIQUE,
          title TEXT,
          extension TEXT,
          size INTEGER,
          subject TEXT,
          material_type TEXT,
          status TEXT,
          extracted_chars INTEGER,
          summary TEXT,
          updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY,
          material_id TEXT,
          chunk_index INTEGER,
          subject TEXT,
          text TEXT,
          tags TEXT,
          FOREIGN KEY(material_id) REFERENCES materials(id)
        );
        CREATE TABLE IF NOT EXISTS flashcards (
          id TEXT PRIMARY KEY,
          material_id TEXT,
          chunk_id TEXT,
          subject TEXT,
          topic TEXT,
          card_type TEXT,
          front TEXT,
          back TEXT,
          source_title TEXT,
          quality INTEGER,
          created_at TEXT,
          FOREIGN KEY(material_id) REFERENCES materials(id),
          FOREIGN KEY(chunk_id) REFERENCES chunks(id)
        );
        """
    )
    return conn


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def infer_subject(text: str) -> str:
    lowered = text.lower()
    best = ("通用学习", 0)
    for subject, tags in SUBJECT_KEYWORDS:
        score = sum(1 for tag in tags if tag.lower() in lowered)
        if score > best[1]:
            best = (subject, score)
    return best[0]


def extract_tags(text: str, subject: str | None = None) -> list[str]:
    lowered = text.lower()
    tags = []
    if subject and subject in SUBJECT_ALLOWED_TAGS:
        pools = [(subject, SUBJECT_ALLOWED_TAGS[subject])]
    else:
        pools = SUBJECT_KEYWORDS
    for _, candidates in pools:
        for tag in candidates:
            if tag.lower() in lowered and tag not in tags:
                tags.append(tag)
    return tags[:10]


def infer_material_type(name: str) -> str:
    if any(word in name for word in ["经验", "心得", "学长"]):
        return "经验贴"
    if any(word in name for word in ["真题", "模拟卷", "套卷"]):
        return "真题/套卷"
    if "错题" in name:
        return "错题集"
    if any(word in name for word in ["高分笔记", "讲义", "教材", "习题", "答案", "解析", "提纲", "总结"]):
        return "教材/讲义"
    if any(word in name for word in ["词汇", "阅读", "作文", "肖八", "肖四"]):
        return "专项资料"
    return "资料"


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def extract_pdf_text(path: Path, max_pages: int) -> tuple[str, str]:
    try:
        import pdfplumber
    except ImportError:
        return "", "missing_pdfplumber"

    texts = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            if max_pages <= 0 and len(pdf.pages) > 30:
                probe_pages = pdf.pages[:3]
                probe_text = "\n".join((page.extract_text() or "") for page in probe_pages)
                if len(clean_extracted_text(probe_text)) < 80:
                    return probe_text, "needs_ocr"
            pages = pdf.pages if max_pages <= 0 else pdf.pages[:max_pages]
            for page in pages:
                texts.append(page.extract_text() or "")
    except Exception as exc:
        return "", f"extract_error:{exc}"
    text = "\n".join(part for part in texts if part.strip())
    if len(text.strip()) < 80:
        return text, "needs_ocr"
    return text, "text_extracted"


def extract_text(path: Path, max_pages: int) -> tuple[str, str]:
    if not path.exists():
        return "", "missing_file"
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return read_text_file(path), "text_extracted"
    if suffix == ".pdf":
        return extract_pdf_text(path, max_pages)
    return "", "unsupported"


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def looks_like_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    noise_patterns = [
        "微信公众号",
        "关注微信公众号",
        "咨询课程",
        "课程",
        "侵权立删",
        "获取",
        "盗版",
        "视频",
        "考点精析",
        "添加",
        "小松学长",
        "大头园",
        "大头圆",
    ]
    if any(pattern in stripped for pattern in noise_patterns) and len(stripped) < 80:
        return True
    if re.fullmatch(r"[-—_·\s]*\d{1,4}[-—_·\s]*", stripped):
        return True
    if len(stripped) <= 3 and not re.search(r"[\u4e00-\u9fffA-Za-z]", stripped):
        return True
    # PDF watermarks often become spaced single-character lines.
    tokens = stripped.split()
    if len(tokens) >= 6 and all(len(token) <= 2 for token in tokens):
        return True
    return False


def clean_extracted_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if looks_like_noise_line(line):
            continue
        line = re.sub(r"微信号[:：]?\S+", "", line)
        line = re.sub(r"QQ交流群[:：]?\S+", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"(?:\b[0-9A-Za-z]\s+){8,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def looks_like_bad_training_text(text: str) -> bool:
    if not text or len(text.strip()) < 80:
        return True
    cid_count = text.count("(cid:")
    if cid_count >= 2 or cid_count / max(len(text), 1) > 0.003:
        return True
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    useful = cjk + latin
    if useful / max(len(text), 1) < 0.18:
        return True
    symbol_noise = len(re.findall(r"[�‡¶ÆªÅ«»ºíü™À¤›ﬁﬂ†±ÄÇÉÑÖÜáàâä]", text))
    if symbol_noise >= 12 and cjk < 60:
        return True
    watermark_hits = sum(
        text.count(word)
        for word in [
            "微信公众号",
            "经济学考研交流",
            "小胖老师微信",
            "最专业的经济学考研辅导团队",
            "北大小胖考研",
            "怡课工作室",
            "北大学长带你玩转",
            "Scanned by CamScanner",
        ]
    )
    if watermark_hits >= 2:
        return True
    if watermark_hits >= 1 and cjk < 160:
        return True
    return False


def split_by_question_boundaries(text: str) -> list[str]:
    pattern = re.compile(r"(?=(?:^|\n)\s*(?:[一二三四五六七八九十]+、|\d+[、.．]|（\d+）|\(\d+\)))")
    parts = [part.strip() for part in pattern.split(text) if part.strip()]
    return [part for part in parts if len(part) >= 120]


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    text = clean_extracted_text(normalize_text(text))
    if not text:
        return []
    question_parts = split_by_question_boundaries(text)
    if len(question_parts) >= 3:
        chunks = []
        for part in question_parts:
            if len(part) <= chunk_size * 1.4:
                chunks.append(part[: int(chunk_size * 1.4)])
            else:
                chunks.extend(chunk_text(part, chunk_size=chunk_size, overlap=overlap))
        return chunks
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if len(chunk) >= 120:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def summary(text: str) -> str:
    clean = re.sub(r"\s+", " ", clean_extracted_text(text)).strip()
    return clean[:220]


def generate_cards(material: dict, chunk_id: str, chunk: str, tags: list[str]) -> list[dict]:
    cards = []
    material_type = material["material_type"]
    if material_type == "经验贴":
        return cards
    if looks_like_bad_training_text(chunk):
        return cards

    tags = [tag for tag in tags if tag in SUBJECT_ALLOWED_TAGS.get(material["subject"], tags)]
    topic = tags[0] if tags else material["subject"]
    sentences = [
        part.strip()
        for part in re.split(r"[。！？；\n]", chunk)
        if 28 <= len(part.strip()) <= 180
    ]
    tagged = [s for s in sentences if any(tag in s for tag in tags)]
    useful = tagged or sentences
    if not useful:
        return cards

    first = clean_card_back(useful[0])
    if looks_like_bad_training_text(first):
        return cards
    if len(first) < 20:
        return cards
    cards.append(
        {
            "topic": topic,
            "card_type": "active_recall",
            "front": f"不看资料，回忆《{material['title']}》中“{topic}”相关的一个核心考点或解题规则。",
                "back": first,
                "quality": 70,
        }
    )

    if material_type in {"真题/套卷", "错题集"}:
        back = clean_card_back(summary(chunk))
        if looks_like_bad_training_text(back):
            return cards
        cards.append(
            {
                "topic": topic,
                "card_type": "exam_drill",
                "front": f"根据《{material['title']}》的片段，设计一道同类题，并说明第一步应该识别什么条件。",
                "back": back,
                "quality": 82,
            }
        )
    elif material_type in {"教材/讲义", "专项资料"} and len(useful) > 1:
        back = clean_card_back(useful[1])
        if looks_like_bad_training_text(back):
            return cards
        cards.append(
            {
                "topic": topic,
                "card_type": "concept_check",
                "front": f"解释“{topic}”在《{material['title']}》里的适用条件或常见陷阱。",
                "back": back,
                "quality": 74,
            }
        )
    return cards


def clean_card_back(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Drop obvious mojibake/watermark leftovers.
    text = re.sub(r"\(cid:\d+\)", "", text)
    text = re.sub(r"[A-Za-z]\s+[A-Za-z]\s+[A-Za-z](?:\s+[A-Za-z]){3,}", "", text)
    text = re.sub(r"(?:微信公众号|关注微信公众号|咨询课程|经济学考研交流QQ\s*群|小胖老师微信|最专业的经济学考研辅导团队|北大小胖考研|怡课工作室|北大学长带你玩转)[：:]?\s*\S*", "", text)
    return text.strip()


def upsert_material(conn, record: dict, text: str, status: str):
    path = record["FullName"]
    title = record["Name"]
    material_id = sha1(path)
    subject = infer_subject(f"{title}\n{text[:2000]}")
    material_type = infer_material_type(title)
    conn.execute(
        """
        INSERT INTO materials(id, path, title, extension, size, subject, material_type, status, extracted_chars, summary, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          title=excluded.title,
          extension=excluded.extension,
          size=excluded.size,
          subject=excluded.subject,
          material_type=excluded.material_type,
          status=excluded.status,
          extracted_chars=excluded.extracted_chars,
          summary=excluded.summary,
          updated_at=excluded.updated_at
        """,
        (
            material_id,
            path,
            title,
            record.get("Extension", ""),
            int(record.get("Length") or 0),
            subject,
            material_type,
            status,
            len(text),
            summary(text) if text else "",
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    return {"id": material_id, "title": title, "subject": subject, "material_type": material_type}


def process_record(conn, record: dict, max_pages: int, max_chunks_per_material: int):
    path = Path(record["FullName"])
    text, status = extract_text(path, max_pages=max_pages)
    text = clean_extracted_text(normalize_text(text))
    material = upsert_material(conn, record, text, status)

    conn.execute("DELETE FROM chunks WHERE material_id = ?", (material["id"],))
    conn.execute("DELETE FROM flashcards WHERE material_id = ?", (material["id"],))

    chunks = chunk_text(text)
    if max_chunks_per_material > 0:
        chunks = chunks[:max_chunks_per_material]
    for idx, chunk in enumerate(chunks):
        tags = extract_tags(chunk, material["subject"]) or extract_tags(record["Name"], material["subject"])
        chunk_id = sha1(f"{material['id']}:{idx}:{chunk[:120]}")
        conn.execute(
            "INSERT OR REPLACE INTO chunks(id, material_id, chunk_index, subject, text, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, material["id"], idx, material["subject"], chunk, json.dumps(tags, ensure_ascii=False)),
        )
        for card in generate_cards(material, chunk_id, chunk, tags):
            card_id = sha1(f"{chunk_id}:{card['front']}")
            conn.execute(
                """
                INSERT OR REPLACE INTO flashcards(id, material_id, chunk_id, subject, topic, card_type, front, back, source_title, quality, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    material["id"],
                    chunk_id,
                    material["subject"],
                    card["topic"],
                    card["card_type"],
                    card["front"],
                    card["back"],
                    material["title"],
                    card["quality"],
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
    return status, len(text), len(chunks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default=str(DEFAULT_INDEX))
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--limit", type=int, default=40, help="0 means process all records")
    parser.add_argument("--max-pages", type=int, default=20, help="0 means all pages")
    parser.add_argument("--max-chunks-per-material", type=int, default=12, help="0 means all chunks")
    args = parser.parse_args()

    records = json.loads(Path(args.index).read_text(encoding="utf-8-sig"))
    conn = connect(Path(args.db))
    processed = 0
    stats = {}
    selected_records = records if args.limit <= 0 else records[: args.limit]
    total = len(selected_records)
    for record in selected_records:
        status, chars, chunks = process_record(conn, record, args.max_pages, args.max_chunks_per_material)
        stats[status] = stats.get(status, 0) + 1
        processed += 1
        print(f"[{processed}/{total}] {status} chars={chars} chunks={chunks} {record['Name']}")
        conn.commit()

    material_count = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    card_count = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0]
    print(json.dumps({"processed": processed, "stats": stats, "materials": material_count, "chunks": chunk_count, "flashcards": card_count}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
