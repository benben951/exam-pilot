import argparse
import base64
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT.parent / "Exam-Wiki"
ENV_FILE = ROOT / ".env.local"
DB_PATH = ROOT / "data" / "learning.db"
OCR_DIR = WIKI / "raw" / "ocr-extracts"


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_base_urls():
    urls = [os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")]
    fallback = os.environ.get("OPENAI_FALLBACK_BASE_URL", "")
    if fallback:
        urls.append(fallback)
    cleaned = []
    for url in urls:
        value = url.rstrip("/")
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def call_responses_ocr(base_url: str, api_key: str, model: str, prompt: str, images: list[str], timeout: int = 90):
    content = [{"type": "input_text", "text": prompt}]
    for image_url in images:
        content.append({"type": "input_image", "image_url": image_url})
    body = json.dumps({"model": model, "input": [{"role": "user", "content": content}]}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/responses",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def call_chat_ocr(base_url: str, api_key: str, model: str, prompt: str, images: list[str], timeout: int = 90):
    content = [{"type": "text", "text": prompt}]
    for image_url in images:
        content.append({"type": "image_url", "image_url": {"url": image_url}})
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    output = data.get("output") or []
    parts = []
    for item in output:
        for content in item.get("content") or []:
            text = content.get("text")
            if text:
                parts.append(text)
    if parts:
        return "\n".join(parts)
    return json.dumps(data, ensure_ascii=False, indent=2)


def extract_chat_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return json.dumps(data, ensure_ascii=False, indent=2)
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return json.dumps(data, ensure_ascii=False, indent=2)


def ocr_with_fallback(api_key: str, model: str, prompt: str, images: list[str]):
    base_urls = get_base_urls()
    errors = []
    for base_url in base_urls:
        try:
            data = call_responses_ocr(base_url, api_key, model, prompt, images)
            return extract_response_text(data), base_url, "responses"
        except Exception as exc:
            errors.append(f"{base_url}/responses: {exc}")
        try:
            data = call_chat_ocr(base_url, api_key, model, prompt, images)
            return extract_chat_text(data), base_url, "chat/completions"
        except Exception as exc:
            errors.append(f"{base_url}/chat/completions: {exc}")
    raise RuntimeError("; ".join(errors))


def page_to_data_url(page, dpi: int = 180) -> str:
    pix = page.get_pixmap(matrix=page.parent._get_zoom_matrix(dpi / 72, dpi / 72), alpha=False)
    mime = "image/png"
    data = base64.b64encode(pix.tobytes("png")).decode("ascii")
    return f"data:{mime};base64,{data}"


def pdf_to_images(path: Path, max_pages: int = 3, dpi: int = 180) -> list[str]:
    import fitz

    doc = fitz.open(str(path))
    try:
        images = []
        total = min(max_pages, doc.page_count)
        for index in range(total):
            page = doc.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            data = base64.b64encode(pix.tobytes("png")).decode("ascii")
            images.append(f"data:image/png;base64,{data}")
        return images
    finally:
        doc.close()


def image_to_data_url(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def pick_materials(conn, limit: int):
    rows = conn.execute(
        """
        SELECT id, subject, material_type, status, title, path, size, extracted_chars
        FROM materials
        WHERE status IN ('needs_ocr', 'unsupported')
        ORDER BY
          CASE
            WHEN subject = '831经济学' THEN 0
            WHEN subject = '英语一' THEN 1
            WHEN subject = '政治' THEN 2
            ELSE 3
          END,
          CASE
            WHEN title LIKE '%真题%' THEN 0
            WHEN title LIKE '%解析%' THEN 1
            WHEN title LIKE '%讲义%' THEN 2
            WHEN title LIKE '%答案%' THEN 3
            ELSE 4
          END,
          size ASC
        """
    ).fetchall()
    return rows[:limit]


def material_prompt(row):
    return (
        "你是OCR引擎。请把图片中的中文、英文、数字、公式尽量准确转写成纯文本。"
        "要求：1. 只输出识别结果，不要解释；2. 保留题号、段落、公式和表格换行；"
        "3. 不要补写原文没有的内容；4. 如果有明显广告水印，可以省略；"
        f"5. 这份资料的科目是{row['subject']}，标题是《{row['title']}》。"
    )


def classify_text(text: str) -> bool:
    cleaned = re.sub(r"\s+", "", text)
    if len(cleaned) < 40:
        return False
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    weird = len(re.findall(r"[‡¶ÆªÅ«»ºíü™À¤›ﬁﬂ†±ÄÇÉÑÖÜáàâä]", text))
    if cjk < 20 and weird > 10:
        return False
    return True


def update_material(conn, material_id: str, text: str, status: str):
    conn.execute(
        """
        UPDATE materials
        SET status = ?, extracted_chars = ?, summary = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, len(text), text[:240], datetime.now().isoformat(timespec="seconds"), material_id),
    )


def mark_ocr_failed(conn, material_id: str, reason: str):
    conn.execute(
        """
        UPDATE materials
        SET status = 'ocr_failed', summary = ?, updated_at = ?
        WHERE id = ?
        """,
        (reason[:240], datetime.now().isoformat(timespec="seconds"), material_id),
    )


def rebuild_cards(conn, material_id: str, subject: str, title: str, text: str):
    from build_learning_db import chunk_text, extract_tags, generate_cards, sha1

    conn.execute("DELETE FROM chunks WHERE material_id = ?", (material_id,))
    conn.execute("DELETE FROM flashcards WHERE material_id = ?", (material_id,))

    chunks = chunk_text(text)
    if not chunks and len(re.sub(r"\s+", "", text)) >= 40:
        chunks = [text.strip()]
    inserted = 0
    for idx, chunk in enumerate(chunks):
        tags = extract_tags(chunk, subject) or extract_tags(title, subject)
        chunk_id = sha1(f"{material_id}:{idx}:{chunk[:120]}")
        conn.execute(
            "INSERT OR REPLACE INTO chunks(id, material_id, chunk_index, subject, text, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, material_id, idx, subject, chunk, json.dumps(tags, ensure_ascii=False)),
        )
        generated = generate_cards(
            {"subject": subject, "material_type": "真题/套卷", "title": title},
            chunk_id,
            chunk,
            tags,
        )
        if not generated:
            topic = tags[0] if tags else ("软微真题" if "软微" in title else subject)
            generated = [
                {
                    "topic": topic,
                    "card_type": "ocr_exam_drill",
                    "front": f"识别《{title}》这一页真题的题型，并说出第一步应抓住的条件。",
                    "back": chunk[:360],
                    "quality": 78,
                }
            ]
        for card in generated:
            card_id = sha1(f"{chunk_id}:{card['front']}")
            conn.execute(
                """
                INSERT OR REPLACE INTO flashcards(id, material_id, chunk_id, subject, topic, card_type, front, back, source_title, quality, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    material_id,
                    chunk_id,
                    subject,
                    card["topic"],
                    card["card_type"],
                    card["front"],
                    card["back"],
                    title,
                    card["quality"],
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            inserted += 1
    return len(chunks), inserted


def export_ocr_file(material, text: str):
    safe_name = re.sub(r"[\\\\/:*?\"<>|]+", "_", material["title"]).strip()
    out = OCR_DIR / f"{material['subject']}" / f"{safe_name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    content = [
        f"# {material['title']}",
        "",
        f"- Subject: {material['subject']}",
        f"- Status: OCR extracted",
        f"- Source: `{material['path']}`",
        f"- Updated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "```text",
        text.strip(),
        "```",
        "",
    ]
    out.write_text("\n".join(content), encoding="utf-8")
    return out


def ocr_one(conn, material, api_key: str, model: str, max_pages: int):
    path = Path(material["path"])
    if path.suffix.lower() == ".pdf":
        images = pdf_to_images(path, max_pages=max_pages)
    else:
        images = [image_to_data_url(path)]

    prompt = material_prompt(material)
    text, base_url, endpoint = ocr_with_fallback(api_key, model, prompt, images)
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not classify_text(text):
        return {
            "ok": False,
            "reason": "low_quality",
            "base_url": base_url,
            "endpoint": endpoint,
            "text": text,
        }

    export_path = export_ocr_file(material, text)
    update_material(conn, material["id"], text, "text_extracted")
    chunks, cards = rebuild_cards(conn, material["id"], material["subject"], material["title"], text)
    return {
        "ok": True,
        "base_url": base_url,
        "endpoint": endpoint,
        "text": text,
        "export_path": str(export_path),
        "chunks": chunks,
        "cards": cards,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.2"))
    args = parser.parse_args()

    load_env(ENV_FILE)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in .env.local")

    OCR_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    materials = pick_materials(conn, args.limit)
    results = []
    for idx, material in enumerate(materials, 1):
        print(f"[{idx}/{len(materials)}] OCR {material['subject']} | {material['title']}")
        try:
            result = ocr_one(conn, material, api_key, args.model, args.max_pages)
            conn.commit()
            results.append({"title": material["title"], **result})
            if result.get("ok"):
                print(f"  ok chunks={result.get('chunks')} cards={result.get('cards')} -> {result.get('export_path')}")
            else:
                print(f"  skip reason={result.get('reason')}")
        except Exception as exc:
            conn.rollback()
            mark_ocr_failed(conn, material["id"], str(exc))
            conn.commit()
            results.append({"title": material["title"], "ok": False, "error": str(exc)})
            print(f"  fail: {exc}")

    out = ROOT / "data" / "ocr-run-report.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report -> {out}")
    conn.close()


if __name__ == "__main__":
    main()
