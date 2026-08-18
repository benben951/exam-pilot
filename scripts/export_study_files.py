import argparse
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "learning.db"
DEFAULT_WIKI = ROOT.parent / "Exam-Wiki"


SUBJECT_DIRS = {
    "数学": "math",
    "英语一": "english",
    "831经济学": "professional-course",
    "政治": "politics",
    "高考语文": "gaokao",
    "高考数学": "gaokao",
    "高考英语": "gaokao",
    "高考历史": "gaokao",
    "高考政治": "gaokao",
    "高考地理": "gaokao",
    "雅思": "ielts",
    "技术/竞赛": "tech",
}


def connect(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_dirs(wiki: Path):
    for folder in [
        "mistakes",
        "weakness",
        "plan",
        "flashcards",
        "materials",
        "gaokao",
        "tech",
        "ielts",
        "math",
        "english",
        "professional-course",
        "politics",
    ]:
        (wiki / folder).mkdir(parents=True, exist_ok=True)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def export_materials(conn, wiki: Path):
    rows = conn.execute(
        """
        SELECT subject, material_type, status, title, path, extracted_chars, summary
        FROM materials
        ORDER BY subject, material_type, title
        """
    ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["subject"]].append(row)

    lines = [
        "# 学习资料索引",
        "",
        f"Last updated: {date.today().isoformat()}",
        "",
        "这个文件来自 ExamPilot 后端解析管道。`text_extracted` 表示已经抽取出文本；`needs_ocr` 表示 PDF 主要是扫描/图片，后续需要 OCR；`unsupported` 表示当前管道还没有解析这种文件格式。",
        "",
    ]
    for subject, items in grouped.items():
        lines.extend([f"## {subject}", ""])
        lines.append("| 资料 | 类型 | 状态 | 抽取字数 | 路径 |")
        lines.append("| --- | --- | --- | ---: | --- |")
        for item in items:
            lines.append(
                f"| {item['title']} | {item['material_type']} | {item['status']} | {item['extracted_chars']} | `{item['path']}` |"
            )
        lines.append("")
    write(wiki / "materials" / "index.md", "\n".join(lines))


def export_weakness(conn, wiki: Path):
    rows = conn.execute(
        """
        SELECT subject, status, COUNT(*) as count
        FROM materials
        GROUP BY subject, status
        ORDER BY subject, status
        """
    ).fetchall()
    card_rows = conn.execute(
        """
        SELECT subject, topic, COUNT(*) as count, AVG(quality) as avg_quality
        FROM flashcards
        GROUP BY subject, topic
        ORDER BY subject, count DESC
        """
    ).fetchall()

    lines = [
        "# 薄弱点地图",
        "",
        f"Last updated: {date.today().isoformat()}",
        "",
        "## 数据可用性",
        "",
        "| 科目 | 状态 | 资料数 |",
        "| --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(f"| {row['subject']} | {row['status']} | {row['count']} |")

    lines.extend(
        [
            "",
            "## 当前可练知识点",
            "",
            "| 科目 | 主题 | 卡片数 | 平均质量 | 建议 |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in card_rows:
        advice = "继续刷同类题，并在错题集记录错因" if row["count"] >= 3 else "先补资料抽取或手动补题"
        lines.append(
            f"| {row['subject']} | {row['topic']} | {row['count']} | {round(row['avg_quality'] or 0, 1)} | {advice} |"
        )

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 优先对 `needs_ocr` 的数学套卷、解析、831 真题和强化讲义做 OCR。",
            "- 每次做错题后，把错因写入 `mistakes/index.md`，至少记录：知识点、错因、下次识别规则。",
            "- 每周根据本文件更新 `plan/current-week.md`，只保留 3 个最高优先级。",
        ]
    )
    write(wiki / "weakness" / "map.md", "\n".join(lines))


def export_flashcards(conn, wiki: Path):
    rows = conn.execute(
        """
        SELECT subject, topic, card_type, front, back, source_title, quality
        FROM flashcards
        ORDER BY subject, quality DESC, topic
        """
    ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["subject"]].append(row)

    for subject, items in grouped.items():
        folder = SUBJECT_DIRS.get(subject, "flashcards")
        lines = [
            f"# {subject} 闪卡与练习题",
            "",
            f"Last updated: {date.today().isoformat()}",
            "",
        ]
        for idx, item in enumerate(items, 1):
            lines.extend(
                [
                    f"## {idx}. {item['topic']} / {item['card_type']}",
                    "",
                    f"Source: `{item['source_title']}`",
                    "",
                    f"Q: {item['front']}",
                    "",
                    f"A: {item['back']}",
                    "",
                    f"Quality: {item['quality']}",
                    "",
                ]
            )
        write(wiki / folder / "flashcards.md", "\n".join(lines))


def export_mistake_templates(wiki: Path):
    index = wiki / "mistakes" / "index.md"
    if not index.exists():
        write(
            index,
            """# 错题总表

| Date | Subject | Topic | Source | Error type | Next-time rule | Status |
| --- | --- | --- | --- | --- | --- | --- |
""",
        )

    write(
        wiki / "mistakes" / "TEMPLATE.md",
        """# 错题记录模板

日期：
科目：
来源：
题目/截图位置：
我的答案：
正确答案：
错误类型：
关键卡点：
正确逻辑：
下次识别规则：
同类题复测：
状态：未复测 / 已复测仍错 / 已掌握
""",
    )


def export_plan(wiki: Path):
    write(
        wiki / "plan" / "current-week.md",
        f"""# 本周计划

Last updated: {date.today().isoformat()}

## 本周三件事

1. 数学：完成 5 条错题规则，优先处理可复测题型。
2. 英语/雅思：完成 2 次阅读或写作复盘。
3. 专业课/高考专项：从后端题库抽 10 张卡片做主动回忆。

## 每日最低动作

| Day | Math | English | Professional / Gaokao | Review |
| --- | --- | --- | --- | --- |
| Mon | | | | |
| Tue | | | | |
| Wed | | | | |
| Thu | | | | |
| Fri | | | | |
| Sat | | | | |
| Sun | | | | |

## 周末复盘

- 本周真正推进：
- 反复错误：
- 下周最高优先级：
""",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--wiki", default=str(DEFAULT_WIKI))
    args = parser.parse_args()

    wiki = Path(args.wiki)
    ensure_dirs(wiki)
    conn = connect(Path(args.db))
    export_materials(conn, wiki)
    export_weakness(conn, wiki)
    export_flashcards(conn, wiki)
    export_mistake_templates(wiki)
    export_plan(wiki)
    conn.close()
    print(f"Exported study files to {wiki}")


if __name__ == "__main__":
    main()
