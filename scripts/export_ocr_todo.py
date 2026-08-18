import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "learning.db"
DEFAULT_OUT = ROOT.parent / "Exam-Wiki" / "materials" / "ocr-todo.md"


def priority(row) -> int:
    title = row["title"]
    score = 0
    if row["subject"] == "831经济学":
        score += 60
    if "软微" in title or "金融科技" in title or "431" in title:
        score += 35
    if "真题" in title or "套卷" in title or "试题" in title:
        score += 30
    if "讲义" in title or "习题" in title or "错题" in title:
        score += 20
    if row["status"] == "ocr_failed":
        score -= 50
    if row["subject"] == "数学":
        score -= 20
    return -score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT subject, title, path, status, material_type, size
        FROM materials
        WHERE status IN ('needs_ocr', 'unsupported', 'ocr_failed')
        ORDER BY subject, title
        """
    ).fetchall()
    rows = sorted(rows, key=priority)

    lines = [
        "# OCR 待办清单",
        "",
        "当前策略：优先处理 831 经济学、软微真题、专业课高价值资料；数学资料先由知能行主练，这里只保留待办。`needs_ocr` 通常是扫描 PDF；`unsupported` 通常是图片、docx、OneNote 或缓存文件；`ocr_failed` 表示上次 OCR 失败，后续单独重试。",
        "",
        "| Priority | Subject | Type | Status | Title | Path |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for idx, row in enumerate(rows, 1):
        lines.append(
            f"| {idx} | {row['subject']} | {row['material_type']} | {row['status']} | {row['title']} | `{row['path']}` |"
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} OCR todo items -> {out}")


if __name__ == "__main__":
    main()
