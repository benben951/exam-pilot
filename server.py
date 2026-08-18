import json
import hashlib
import mimetypes
import os
import re
import sqlite3
import time
from datetime import date, datetime, timedelta
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape

from scripts.economics_anki import llm_cards, sync_cards, load_dotenv as load_economics_env


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
MATERIAL_INDEX = ROOT.parent / "Exam-Wiki" / "raw" / "materials-file-index.json"
SELECTED_PATHS = ROOT.parent / "Exam-Wiki" / "raw" / "selected-material-paths.txt"
MATERIAL_SAMPLES = ROOT.parent / "Exam-Wiki" / "raw" / "material-samples"
SOFTMICRO_EXTRACTS = ROOT.parent / "Exam-Wiki" / "raw" / "softmicro-extracts"
LEARNING_DB = ROOT / "data" / "learning.db"
STUDY_RECORDS_FILE = ROOT / "data" / "study_records.json"
TASKS_FILE = ROOT / "data" / "agent_tasks.json"
MEMORY_FILE = ROOT / "data" / "memory_observations.json"


SUBJECT_KEYWORDS = [
    ("数学", ["极限", "导数", "积分", "矩阵", "线性代数", "微分方程", "概率论", "高数", "数二"]),
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


def infer_subject(text: str) -> str:
    lowered = text.lower()
    best_subject = "通用学习"
    best_score = 0
    for subject, tags in SUBJECT_KEYWORDS:
        score = sum(1 for tag in tags if tag.lower() in lowered)
        if score > best_score:
            best_subject = subject
            best_score = score
    return best_subject


def extract_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags = []
    for _, candidates in SUBJECT_KEYWORDS:
        for tag in candidates:
            if tag.lower() in lowered and tag not in tags:
                tags.append(tag)
    return tags[:8]


def infer_stage(name: str, length: int, tags: list[str]) -> str:
    text = name
    if any(word in text for word in ["真题", "模拟卷", "错题", "解析", "答案"]):
        return "高级"
    if length > 5_000_000 or len(tags) >= 4:
        return "中级"
    return "初级"


def infer_material_type(name: str) -> str:
    if any(word in name for word in ["经验", "心得", "学长"]):
        return "经验贴"
    if any(word in name for word in ["真题", "模拟卷", "套卷"]):
        return "真题/套卷"
    if any(word in name for word in ["错题"]):
        return "错题集"
    if any(word in name for word in ["高分笔记", "讲义", "教材", "习题", "答案", "解析"]):
        return "教材/讲义"
    if any(word in name for word in ["词汇", "阅读", "作文", "肖八", "肖四"]):
        return "专项资料"
    return "资料索引"


def is_quiz_eligible(material_type: str, sample_text: str) -> bool:
    if material_type == "经验贴":
        return False
    return material_type != "资料索引" or len(sample_text.strip()) > 200


def load_study_records() -> list[dict]:
    if not STUDY_RECORDS_FILE.exists():
        return []
    try:
        payload = json.loads(STUDY_RECORDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, dict):
        records = payload.get("records") or []
    elif isinstance(payload, list):
        records = payload
    else:
        records = []
    normalized = [normalize_study_record(item) for item in records if isinstance(item, dict)]
    normalized.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return normalized


def save_study_records(records: list[dict]) -> None:
    STUDY_RECORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"records": records[:400]}
    STUDY_RECORDS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json_list(path: Path, key: str) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, dict):
        items = payload.get(key) or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    return [item for item in items if isinstance(item, dict)]


def save_json_list(path: Path, key: str, items: list[dict], limit: int = 500) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({key: items[:limit]}, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_task(task: dict) -> dict:
    created_at = task.get("createdAt") or time.strftime("%Y-%m-%d %H:%M:%S")
    title = (task.get("title") or "").strip() or "未命名任务"
    payload = {
        "title": title,
        "status": task.get("status") or "todo",
        "lane": task.get("lane") or "system",
        "priority": task.get("priority") or "medium",
        "source": task.get("source") or "",
        "detail": task.get("detail") or "",
        "owner": task.get("owner") or "ExamPilot",
        "createdAt": created_at,
        "updatedAt": task.get("updatedAt") or created_at,
        "dueAt": task.get("dueAt") or task.get("dueDate") or "",
    }
    digest_source = f'{payload["lane"]}|{payload["title"]}|{payload["source"]}'
    payload["id"] = task.get("id") or hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:16]
    return payload


def normalize_memory(observation: dict) -> dict:
    created_at = observation.get("createdAt") or time.strftime("%Y-%m-%d %H:%M:%S")
    text = (observation.get("text") or "").strip()
    payload = {
        "kind": observation.get("kind") or "note",
        "subject": observation.get("subject") or "通用学习",
        "text": text,
        "source": observation.get("source") or "",
        "tags": observation.get("tags") or [],
        "createdAt": created_at,
    }
    digest_source = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    payload["id"] = observation.get("id") or hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:16]
    return payload


def load_agent_tasks() -> list[dict]:
    saved = [normalize_task(item) for item in load_json_list(TASKS_FILE, "tasks")]
    saved_by_id = {item["id"]: item for item in saved}
    generated = build_generated_tasks()
    merged = []
    for task in generated + saved:
        existing = saved_by_id.get(task["id"])
        merged.append(existing or task)
    deduped = {}
    for task in merged:
        deduped[task["id"]] = task
    tasks = list(deduped.values())
    order = {"doing": 0, "todo": 1, "blocked": 2, "done": 3}
    tasks.sort(key=lambda item: (order.get(item.get("status"), 9), item.get("priority") != "high", item.get("createdAt", "")))
    return tasks


def save_agent_task(task: dict) -> dict:
    normalized = normalize_task({**task, "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S")})
    saved = [normalize_task(item) for item in load_json_list(TASKS_FILE, "tasks")]
    saved = [item for item in saved if item["id"] != normalized["id"]]
    saved.insert(0, normalized)
    save_json_list(TASKS_FILE, "tasks", saved)
    return normalized


def load_memory_observations(query: str = "") -> list[dict]:
    observations = [normalize_memory(item) for item in load_json_list(MEMORY_FILE, "observations")]
    if query.strip():
        tokens = [token for token in re.split(r"[\s,，。；;、/\\|]+", query.strip()) if token]
        observations = [
            item for item in observations
            if token_score(" ".join([item["subject"], item["text"], item["source"], " ".join(item.get("tags") or [])]), tokens) > 0
        ]
    observations.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return observations[:80]


def save_memory_observation(observation: dict) -> dict:
    normalized = normalize_memory(observation)
    saved = [normalize_memory(item) for item in load_json_list(MEMORY_FILE, "observations")]
    saved = [item for item in saved if item["id"] != normalized["id"]]
    saved.insert(0, normalized)
    save_json_list(MEMORY_FILE, "observations", saved)
    return normalized


def build_generated_tasks() -> list[dict]:
    conn = db_connect()
    if not conn:
        return []
    rows = conn.execute(
        """
        SELECT title, path, subject, status, material_type
        FROM materials
        WHERE status = 'needs_ocr'
        ORDER BY
          CASE WHEN subject = '831经济学' THEN 0 ELSE 1 END,
          CASE WHEN material_type = '真题/套卷' THEN 0 ELSE 1 END,
          size DESC
        LIMIT 10
        """
    ).fetchall()
    conn.close()
    tasks = []
    for row in rows:
        task_id = "ocr-" + hashlib.sha1((row["path"] or row["title"]).encode("utf-8")).hexdigest()[:12]
        tasks.append(
            normalize_task(
                {
                    "id": task_id,
                    "title": f'OCR 入库：{row["title"]}',
                    "status": "todo",
                    "lane": "ocr",
                    "priority": "high" if row["subject"] == "831经济学" else "medium",
                    "source": row["path"] or "",
                    "detail": f'{row["subject"] or "未知科目"} · {row["material_type"] or "资料"} · {row["status"]}',
                    "owner": "ExamPilot",
                    "createdAt": "generated-from-db",
                    "updatedAt": "generated-from-db",
                }
            )
        )
    return tasks


def normalize_study_record(record: dict) -> dict:
    created_at = record.get("createdAt") or time.strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "kind": record.get("kind") or "diagnosis",
        "subject": record.get("subject") or "通用学习",
        "hours": float(record.get("hours") or 0),
        "accuracy": float(record.get("accuracy") or 0),
        "errorType": record.get("errorType") or "未分类",
        "note": record.get("note") or "",
        "rule": record.get("rule") or "",
        "title": record.get("title") or "",
        "source": record.get("source") or "",
        "tags": record.get("tags") or [],
        "createdAt": created_at,
    }
    fingerprint = hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    payload["id"] = record.get("id") or fingerprint
    return payload


def parse_activity_datetime(value: str | None) -> datetime | None:
    """Parse the date formats already used by the local study files."""
    if not value:
        return None
    text = str(value).strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def build_monitoring_report(
    records: list[dict] | None = None,
    tasks: list[dict] | None = None,
    now: datetime | None = None,
    window_days: int = 7,
) -> dict:
    """Build a deterministic, local-only study operations report."""
    now = now or datetime.now()
    records = [normalize_study_record(item) for item in (records or [])]
    tasks = [normalize_task(item) for item in (tasks or [])]
    window_start = now - timedelta(days=max(1, window_days) - 1)
    recent = [
        item for item in records
        if (parsed := parse_activity_datetime(item.get("createdAt"))) and parsed >= window_start and parsed <= now
    ]
    hours = sum(max(0.0, float(item.get("hours") or 0)) for item in recent)
    accuracies = [float(item.get("accuracy") or 0) for item in recent if item.get("accuracy") is not None]
    active_dates = {parse_activity_datetime(item.get("createdAt")).date() for item in recent if parse_activity_datetime(item.get("createdAt"))}
    streak = 0
    cursor = now.date()
    while cursor in active_dates:
        streak += 1
        cursor -= timedelta(days=1)
    overdue = []
    for task in tasks:
        due = parse_activity_datetime(task.get("dueAt"))
        if task.get("status") not in {"done", "cancelled"} and task.get("priority") == "high" and due and due.date() < now.date():
            overdue.append(task)
    reasons = []
    if not records:
        risk = "unknown"
        reasons.append("还没有可用于监测的学习记录")
    else:
        if overdue:
            reasons.append(f"有 {len(overdue)} 个高优先级任务逾期")
        if not recent:
            reasons.append(f"最近 {window_days} 天没有学习记录")
        if recent and sum(1 for item in recent if float(item.get("accuracy") or 0) < 60) >= 2:
            reasons.append("最近记录中有多次正确率低于 60%")
        if overdue or not recent or (accuracies and sum(accuracies) / len(accuracies) < 60):
            risk = "high"
        elif len(active_dates) < 3 or (accuracies and sum(accuracies) / len(accuracies) < 75):
            risk = "medium"
        else:
            risk = "low"
        if not reasons:
            reasons.append("学习记录、活跃天数和任务状态暂未出现明显风险")
    subjects = sorted({item.get("subject") for item in recent if item.get("subject")})
    actions = []
    if overdue:
        actions.append("先处理一个逾期高优先级任务，并把状态更新为进行中或完成")
    if not recent:
        actions.append("今天记录一次 25 分钟以上的主动学习")
    if recent and (accuracies and sum(accuracies) / len(accuracies) < 75):
        actions.append("围绕最近的薄弱点完成一次小测或错题复测")
    if not actions:
        actions.append("保持当前节奏，并在本周结束前完成一次复盘")
    return {
        "windowDays": window_days,
        "from": window_start.strftime("%Y-%m-%d"),
        "to": now.strftime("%Y-%m-%d"),
        "studyHours": round(hours, 2),
        "recordCount": len(recent),
        "averageAccuracy": round(sum(accuracies) / len(accuracies), 1) if accuracies else 0,
        "ruleCount": sum(1 for item in recent if str(item.get("rule") or "").strip()),
        "activeDays": len(active_dates),
        "streakDays": streak,
        "subjectCoverage": subjects,
        "overdueHighPriorityTasks": overdue,
        "riskLevel": risk,
        "riskReasons": reasons,
        "nextActions": actions,
    }


def first_match_excerpt(text: str, tokens: list[str], window: int = 120) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return ""
    lowered = clean.lower()
    for token in tokens:
        idx = lowered.find(token.lower())
        if idx >= 0:
            start = max(0, idx - window // 2)
            end = min(len(clean), idx + len(token) + window // 2)
            excerpt = clean[start:end]
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(clean):
                excerpt = excerpt + "..."
            return excerpt
    return clean[: window * 2] + ("..." if len(clean) > window * 2 else "")


def token_score(text: str, tokens: list[str]) -> int:
    lowered = (text or "").lower()
    return sum(1 for token in tokens if token and token.lower() in lowered)


LOW_VALUE_EVIDENCE_TERMS = [
    "联系方式",
    "公众号",
    "助教微信",
    "集训营",
    "协议班",
    "价格",
    "随报随学",
    "版权所有",
    "qq ",
    "www.",
]


def evidence_quality_penalty(text: str) -> int:
    lowered = (text or "").lower()
    return sum(1 for term in LOW_VALUE_EVIDENCE_TERMS if term.lower() in lowered)


def evidence_content_rank(text: str) -> tuple[int, int]:
    clean = text or ""
    useful_signals = ["求", "证明", "推导", "假设", "效用", "均衡", "函数", "模型", "答案", "解析", "曲线", "供给", "需求"]
    return (token_score(clean, useful_signals) - evidence_quality_penalty(clean) * 3, len(clean))


def search_db_materials(query: str, limit: int = 12) -> dict:
    query = (query or "").strip()
    tokens = [token for token in re.split(r"[\s,，。；;、/\\|]+", query) if token]
    conn = db_connect()
    if not conn:
        return {"query": query, "materials": [], "evidence": [], "total": 0}

    material_rows = conn.execute(
        """
        SELECT id, path, title, extension, size, subject, material_type, status, extracted_chars, summary, updated_at
        FROM materials
        """
    ).fetchall()
    chunk_rows = conn.execute(
        """
        SELECT c.material_id, c.chunk_index, c.subject, c.text, c.tags, m.title, m.path, m.status
        FROM chunks c
        LEFT JOIN materials m ON m.id = c.material_id
        """
    ).fetchall()
    conn.close()

    matched_materials = []
    for row in material_rows:
        joined = " ".join(
            [
                row["title"] or "",
                row["path"] or "",
                row["summary"] or "",
                row["subject"] or "",
                row["material_type"] or "",
                row["status"] or "",
            ]
        )
        score = token_score(joined, tokens)
        if not query:
            score = 1
        if score or not query:
            matched_materials.append(
                {
                    "id": row["id"],
                    "path": row["path"],
                    "title": row["title"],
                    "extension": row["extension"],
                    "size": row["size"],
                    "subject": row["subject"],
                    "materialType": row["material_type"],
                    "status": row["status"],
                    "extractedChars": row["extracted_chars"],
                    "summary": row["summary"] or "",
                    "updatedAt": row["updated_at"],
                    "score": score,
                }
            )
    matched_materials.sort(key=lambda item: (item["score"], item["updatedAt"] or ""), reverse=True)
    matched_materials = matched_materials[:limit]

    material_lookup = {item["id"]: item for item in matched_materials}
    evidence = []
    for row in chunk_rows:
        text = row["text"] or ""
        joined = " ".join([text, row["tags"] or "", row["subject"] or ""])
        score = token_score(joined, tokens)
        if not query:
            score = 1 if row["chunk_index"] < 2 else 0
        score -= evidence_quality_penalty(text)
        if score <= 0:
            continue
        material_id = row["material_id"]
        if query and material_id not in material_lookup and len(evidence) >= limit * 2:
            continue
        evidence.append(
            {
                "materialId": material_id,
                "title": row["title"] or "",
                "path": row["path"] or "",
                "subject": row["subject"] or "",
                "chunkIndex": row["chunk_index"],
                "excerpt": first_match_excerpt(text, tokens),
                "tags": row["tags"] or "",
                "status": row["status"] or "",
                "score": score,
            }
        )
    evidence.sort(key=lambda item: (item["score"], -item["chunkIndex"]), reverse=True)
    return {
        "query": query,
        "materials": matched_materials,
        "evidence": evidence[: limit * 2],
        "total": len(material_rows),
    }


def get_material_detail(material_id: str) -> dict:
    conn = db_connect()
    if not conn:
        return {}
    material = conn.execute(
        """
        SELECT id, path, title, extension, size, subject, material_type, status, extracted_chars, summary, updated_at
        FROM materials
        WHERE id = ?
        """,
        (material_id,),
    ).fetchone()
    if not material:
        conn.close()
        return {}
    chunks = conn.execute(
        """
        SELECT chunk_index, subject, text, tags
        FROM chunks
        WHERE material_id = ?
        ORDER BY chunk_index ASC
        LIMIT 40
        """,
        (material_id,),
    ).fetchall()
    flashcards = conn.execute(
        """
        SELECT id, topic, card_type, front, back, quality, created_at
        FROM flashcards
        WHERE material_id = ?
        ORDER BY quality DESC, created_at DESC
        LIMIT 12
        """,
        (material_id,),
    ).fetchall()
    conn.close()
    chunk_items = [
        {
            "chunkIndex": row["chunk_index"],
            "subject": row["subject"],
            "text": row["text"] or "",
            "tags": row["tags"] or "",
        }
        for row in chunks
    ]
    chunk_items.sort(key=lambda item: (evidence_content_rank(item["text"]), -item["chunkIndex"]), reverse=True)

    return {
        "material": {
            "id": material["id"],
            "path": material["path"],
            "title": material["title"],
            "extension": material["extension"],
            "size": material["size"],
            "subject": material["subject"],
            "materialType": material["material_type"],
            "status": material["status"],
            "extractedChars": material["extracted_chars"],
            "summary": material["summary"] or "",
            "updatedAt": material["updated_at"],
        },
        "chunks": chunk_items[:18],
        "flashcards": [
            {
                "id": row["id"],
                "topic": row["topic"],
                "cardType": row["card_type"],
                "front": row["front"],
                "back": row["back"],
                "quality": row["quality"],
                "createdAt": row["created_at"],
            }
            for row in flashcards
        ],
    }


def build_weakness_report() -> dict:
    conn = db_connect()
    flashcards = []
    material_status = {}
    if conn:
        flashcards = conn.execute(
            """
            SELECT subject, topic, AVG(quality) AS avg_quality, COUNT(*) AS total
            FROM flashcards
            GROUP BY subject, topic
            ORDER BY avg_quality ASC, total DESC
            """
        ).fetchall()
        material_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM materials
            GROUP BY status
            ORDER BY total DESC
            """
        ).fetchall()
        material_status = {row["status"]: row["total"] for row in material_rows}
        conn.close()

    records = load_study_records()
    subject_scores: dict[str, list[float]] = {}
    topic_scores: dict[str, list[float]] = {}
    for record in records:
        if record.get("subject"):
            subject_scores.setdefault(record["subject"], []).append(float(record.get("accuracy") or 0))
        topic_key = f'{record.get("subject") or "通用学习"} · {record.get("errorType") or "未分类"}'
        topic_scores.setdefault(topic_key, []).append(float(record.get("accuracy") or 0))

    record_weaknesses = [
        {
            "subject": subject,
            "score": round(sum(scores) / len(scores), 1) if scores else 0,
            "count": len(scores),
            "source": "本地诊断记录",
        }
        for subject, scores in subject_scores.items()
    ]
    record_weaknesses.sort(key=lambda item: (item["score"], item["count"]))

    topic_weaknesses = [
        {
            "topic": topic,
            "score": round(sum(scores) / len(scores), 1) if scores else 0,
            "count": len(scores),
        }
        for topic, scores in topic_scores.items()
    ]
    topic_weaknesses.sort(key=lambda item: (item["score"], item["count"]))

    flashcard_weaknesses = [
        {
            "subject": row["subject"],
            "topic": row["topic"],
            "score": round(row["avg_quality"] or 0, 1),
            "count": row["total"],
            "source": "后端题库",
        }
        for row in flashcards
    ][:8]

    ocr_materials = []
    conn = db_connect()
    if conn:
        rows = conn.execute(
            """
            SELECT title, path, status, extracted_chars
            FROM materials
            WHERE status = 'needs_ocr'
            ORDER BY size DESC
            LIMIT 8
            """
        ).fetchall()
        conn.close()
        ocr_materials = [
            {
                "title": row["title"],
                "path": row["path"],
                "status": row["status"],
                "extractedChars": row["extracted_chars"],
            }
            for row in rows
        ]

    return {
        "records": records[:30],
        "subjectWeaknesses": record_weaknesses[:8],
        "topicWeaknesses": topic_weaknesses[:8],
        "flashcardWeaknesses": flashcard_weaknesses,
        "materialStatus": material_status,
        "ocrGaps": ocr_materials,
    }


def compact_name(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


def load_sample_text(name: str) -> str:
    stem = Path(name).stem
    compact_stem = compact_name(stem)
    candidates = []
    for folder in [MATERIAL_SAMPLES, SOFTMICRO_EXTRACTS]:
        if folder.exists():
            candidates.extend(folder.glob("*.txt"))
    for candidate in candidates:
        candidate_compact = compact_name(candidate.stem)
        if compact_stem and (compact_stem in candidate_compact or candidate_compact in compact_stem):
            text = candidate.read_text(encoding="utf-8", errors="ignore")
            return text[:8000]
    return ""


def load_preloaded_materials() -> list[dict]:
    if not MATERIAL_INDEX.exists():
        return []
    index = json.loads(MATERIAL_INDEX.read_text(encoding="utf-8-sig"))
    selected = set()
    if SELECTED_PATHS.exists():
        selected = {line.strip() for line in SELECTED_PATHS.read_text(encoding="utf-8-sig").splitlines() if line.strip()}

    records = []
    for item in index:
        path = item.get("FullName", "")
        name = item.get("Name", Path(path).name)
        length = int(item.get("Length") or 0)
        text = f"{name} {path}"
        tags = extract_tags(text)
        subject = infer_subject(text)
        stage = infer_stage(name, length, tags)
        material_type = infer_material_type(name)
        sample_text = load_sample_text(name)
        quiz_eligible = is_quiz_eligible(material_type, sample_text)
        records.append(
            {
                "id": f"preload-{len(records) + 1}",
                "title": name,
                "subject": subject,
                "stage": stage,
                "materialType": material_type,
                "quizEligible": quiz_eligible,
                "tags": tags,
                "summary": f"本地备考资料：{name}。文件大小约 {round(length / 1024 / 1024, 2)} MB。",
                "text": sample_text or f"本地路径：{path}\n资料名：{name}\n自动标签：{'、'.join(tags) or subject}",
                "hasExtractedText": bool(sample_text.strip()),
                "path": path,
                "isPriority": path in selected,
                "createdAt": "preloaded"
            }
        )

    records.sort(key=lambda item: (not item["isPriority"], item["subject"], item["title"]))
    return records


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "ExamPilot local API"})
            return
        if parsed.path == "/api/materials/search":
            self.handle_material_search(parsed)
            return
        if parsed.path == "/api/materials/detail":
            self.handle_material_detail(parsed)
            return
        if parsed.path == "/api/weaknesses":
            self.send_json(build_weakness_report())
            return
        if parsed.path == "/api/records":
            self.handle_records()
            return
        if parsed.path == "/api/monitoring":
            self.send_json(build_monitoring_report(load_study_records(), load_agent_tasks()))
            return
        if parsed.path == "/api/tasks":
            self.send_json({"tasks": load_agent_tasks()})
            return
        if parsed.path == "/api/memory":
            self.handle_memory_search(parsed)
            return
        if parsed.path == "/api/wechat/callback":
            self.handle_wechat_verify(parsed)
            return
        if parsed.path == "/api/materials/preload":
            self.send_json({"materials": load_preloaded_materials()})
            return
        if parsed.path == "/api/flashcards":
            self.send_json({"cards": load_db_flashcards()})
            return
        if parsed.path == "/api/db/stats":
            self.send_json(load_db_stats())
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/ai/analyze":
            self.handle_ai_analyze()
            return
        if parsed.path == "/api/deepseek/ask":
            self.handle_deepseek_ask()
            return
        if parsed.path == "/api/records":
            self.handle_record_create()
            return
        if parsed.path == "/api/tasks":
            self.handle_task_create()
            return
        if parsed.path == "/api/memory":
            self.handle_memory_create()
            return
        if parsed.path == "/api/ielts/speaking/analyze":
            self.handle_ielts_speaking_analyze()
            return
        if parsed.path == "/api/economics/cards/generate":
            self.handle_economics_cards_generate()
            return
        if parsed.path == "/api/economics/cards/sync":
            self.handle_economics_cards_sync()
            return
        if parsed.path == "/api/wechat/callback":
            self.handle_wechat_message(parsed)
            return
        self.send_json({"error": "not found"}, status=404)

    def handle_records(self):
        self.send_json({"records": load_study_records(), "weaknesses": build_weakness_report()})

    def handle_record_create(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        record = normalize_study_record(payload)
        records = load_study_records()
        records = [item for item in records if item["id"] != record["id"]]
        records.insert(0, record)
        save_study_records(records)
        self.send_json({"record": record, "records": records[:30], "weaknesses": build_weakness_report()})

    def handle_material_search(self, parsed):
        params = parse_qs(parsed.query)
        query = first_param(params, "q")
        limit = int(first_param(params, "limit") or "12")
        self.send_json(search_db_materials(query, limit=limit))

    def handle_material_detail(self, parsed):
        params = parse_qs(parsed.query)
        material_id = first_param(params, "id")
        if not material_id:
            self.send_json({"error": "missing_material_id"}, status=400)
            return
        detail = get_material_detail(material_id)
        if not detail:
            self.send_json({"error": "not_found"}, status=404)
            return
        self.send_json(detail)

    def handle_task_create(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        task = save_agent_task(payload)
        self.send_json({"task": task, "tasks": load_agent_tasks()})

    def handle_memory_search(self, parsed):
        params = parse_qs(parsed.query)
        query = first_param(params, "q")
        self.send_json({"observations": load_memory_observations(query)})

    def handle_memory_create(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        observation = save_memory_observation(payload)
        self.send_json({"observation": observation, "observations": load_memory_observations()})

    def handle_ielts_speaking_analyze(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        feedback = analyze_ielts_speaking(payload)
        self.send_json({"feedback": feedback})

    def handle_economics_cards_generate(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        text = str(payload.get("text") or "").strip()
        if not text:
            self.send_json({"error": "missing_text", "message": "请先粘贴教材小节、错题或真题解析。"}, status=400)
            return
        topic = str(payload.get("topic") or "微观::消费者理论")
        deck = str(payload.get("deck") or "831经济学::微观")
        source = str(payload.get("source") or "ExamPilot 831经济学网页")
        limit = max(1, min(20, int(payload.get("limit") or 8)))
        load_economics_env()
        cards = llm_cards(text, topic, deck, source, limit)
        self.send_json({"cards": cards, "count": len(cards)})

    def handle_economics_cards_sync(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        cards = payload.get("cards") or []
        if not isinstance(cards, list) or not cards:
            self.send_json({"error": "missing_cards", "message": "没有可同步的卡片。"}, status=400)
            return
        anki_url = str(payload.get("ankiUrl") or "http://127.0.0.1:8765")
        try:
            added, failed = sync_cards(cards, anki_url, verbose=False)
        except Exception as error:
            self.send_json(
                {
                    "error": "anki_sync_failed",
                    "message": str(error),
                    "hint": "请确认 Anki 已打开、AnkiConnect 已安装。如果 ExamPilot 网页占用 8765 端口，需要先停止网页服务或把 AnkiConnect 改到其他端口。",
                },
                status=502,
            )
            return
        self.send_json({"added": added, "failed": failed})

    def translate_path(self, path):
        parsed = urlparse(path)
        relative = parsed.path.lstrip("/") or "index.html"
        target = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
            return str(WEB_ROOT / "index.html")
        return str(target)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def handle_ai_analyze(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
        base_urls = get_base_urls()
        base_url = base_urls[0]
        if not api_key:
            self.send_json(
                {
                    "error": "missing_api_key",
                    "message": "本地 AI 接口还没有配置 OPENAI_API_KEY。请在启动前设置环境变量；中转站还需要 OPENAI_BASE_URL。"
                },
                status=503,
            )
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        prompt = payload.get("prompt") or "请分析这份学习数据。"
        prompt = protect_non_ascii_prompt(prompt)
        try:
            data, analysis, endpoint, base_url = call_any_model(base_urls, api_key, model, prompt, timeout=60)
        except Exception as error:
            self.send_json({"error": "openai_request_failed", "message": str(error)}, status=502)
            return

        if not analysis.strip():
            analysis = "模型接口已连通，但返回内容为空。请尝试更换模型名或检查中转站响应格式。"
        self.send_json({"model": model, "base_url": base_url, "endpoint": endpoint, "analysis": analysis, "raw": data})

    def handle_deepseek_ask(self):
        load_economics_env()
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ECON_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ECON_LLM_API_KEY"):
            base_urls = [(os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("ECON_LLM_BASE_URL") or "https://api.deepseek.com").rstrip("/")]
            model = os.environ.get("DEEPSEEK_MODEL") or os.environ.get("ECON_LLM_MODEL") or "deepseek-chat"
        else:
            base_urls = get_base_urls()
            model = os.environ.get("OPENAI_MODEL") or "gpt-5.2"
        if not api_key:
            self.send_json({"error": "missing_api_key", "message": "请先在 .env.local 配置 DEEPSEEK_API_KEY。"}, status=503)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        prompt = payload.get("prompt") or payload.get("question") or "请分析我的学习复盘。"
        prompt = protect_non_ascii_prompt(prompt)
        try:
            data, analysis, endpoint, base_url = call_any_model(base_urls, api_key, model, prompt, timeout=60)
        except Exception as error:
            self.send_json({"error": "deepseek_request_failed", "message": str(error)}, status=502)
            return
        self.send_json({"model": model, "base_url": base_url, "endpoint": endpoint, "analysis": analysis, "raw": data})

    def handle_wechat_verify(self, parsed):
        params = parse_qs(parsed.query)
        signature = first_param(params, "signature")
        timestamp = first_param(params, "timestamp")
        nonce = first_param(params, "nonce")
        echostr = first_param(params, "echostr")
        if verify_wechat_signature(signature, timestamp, nonce):
            self.send_response(200)
            body = echostr.encode("utf-8")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(403)
        self.end_headers()

    def handle_wechat_message(self, parsed):
        params = parse_qs(parsed.query)
        signature = first_param(params, "signature")
        timestamp = first_param(params, "timestamp")
        nonce = first_param(params, "nonce")
        if not verify_wechat_signature(signature, timestamp, nonce):
            self.send_response(403)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            message = parse_wechat_xml(raw)
        except ET.ParseError:
            self.send_wechat_text("", "", "消息解析失败，请发送文字。")
            return

        from_user = message.get("FromUserName", "")
        to_user = message.get("ToUserName", "")
        msg_type = message.get("MsgType", "")
        if msg_type != "text":
            self.send_wechat_text(from_user, to_user, "ExamPilot 当前先支持文字消息。你可以发送：高考地理 等值线 错题分析。")
            return

        user_text = message.get("Content", "").strip()
        reply = build_wechat_reply(user_text)
        self.send_wechat_text(from_user, to_user, reply)

    def send_wechat_text(self, to_user, from_user, content):
        body = f"""<xml>
<ToUserName><![CDATA[{escape(to_user)}]]></ToUserName>
<FromUserName><![CDATA[{escape(from_user)}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>""".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def extract_response_text(data: dict) -> str:
    chunks = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                chunks.append(text)
    return "\n".join(chunks) if chunks else json.dumps(data, ensure_ascii=False, indent=2)


def first_param(params: dict, name: str) -> str:
    values = params.get(name) or [""]
    return values[0]


def verify_wechat_signature(signature: str, timestamp: str, nonce: str) -> bool:
    token = os.environ.get("WECHAT_TOKEN", "exampilot-token")
    pieces = sorted([token, timestamp or "", nonce or ""])
    digest = hashlib.sha1("".join(pieces).encode("utf-8")).hexdigest()
    return bool(signature) and digest == signature


def parse_wechat_xml(raw: bytes) -> dict:
    root = ET.fromstring(raw)
    return {child.tag: child.text or "" for child in root}


def build_wechat_reply(user_text: str) -> str:
    subject = infer_subject(user_text)
    tags = extract_tags(user_text)
    if not user_text:
        return "我是 ExamPilot 学习助手。发送你的科目、错题或卡点，我会帮你定位薄弱点。"

    prompt = (
        "你是 ExamPilot 微信学习助手。请用中文，120字以内，给学生一个具体学习建议。"
        f"\n用户消息：{user_text}\n识别科目：{subject}\n标签：{'、'.join(tags) or '未识别'}"
    )
    ai = call_model(prompt)
    if ai:
        return ai[:600]
    tags_text = "、".join(tags) if tags else "暂未识别明确知识点"
    return f"已识别：{subject}；关键词：{tags_text}。建议先记录题目来源、错误原因和下次识别规则，再做2道同类题复测。"


def db_connect():
    if not LEARNING_DB.exists():
        return None
    conn = sqlite3.connect(LEARNING_DB)
    conn.row_factory = sqlite3.Row
    return conn


def load_db_flashcards(limit: int = 300) -> list[dict]:
    conn = db_connect()
    if not conn:
        return []
    rows = conn.execute(
        """
        SELECT id, subject, topic, card_type, front, back, source_title, quality
        FROM flashcards
        ORDER BY quality DESC, created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "subject": row["subject"],
            "topic": row["topic"],
            "card_type": row["card_type"],
            "front": row["front"],
            "back": row["back"],
            "source": row["source_title"],
            "quality": row["quality"],
        }
        for row in rows
    ]


def load_db_stats() -> dict:
    conn = db_connect()
    if not conn:
        return {"materials": 0, "chunks": 0, "flashcards": 0, "needs_ocr": 0, "records": len(load_study_records())}
    stats = {
        "materials": conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0],
        "chunks": conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        "flashcards": conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0],
        "needs_ocr": conn.execute("SELECT COUNT(*) FROM materials WHERE status = 'needs_ocr'").fetchone()[0],
        "records": len(load_study_records()),
    }
    conn.close()
    return stats


def analyze_ielts_speaking(payload: dict) -> dict:
    part = str(payload.get("part") or "part1")
    question = str(payload.get("question") or "")
    transcript = str(payload.get("transcript") or "").strip()
    duration_sec = int(payload.get("durationSec") or 0)
    azure_configured = bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))
    prompt = build_ielts_speaking_prompt(part, question, transcript, duration_sec, azure_configured)
    model_text = call_model(prompt)
    parsed = parse_json_object(model_text)
    if parsed:
        parsed.setdefault("source", "model")
        parsed.setdefault("pronunciationStatus", "configured" if azure_configured else "not_configured")
        if not azure_configured:
            parsed["pronunciation"] = parsed.get("pronunciation") or "未配置 Azure Speech Pronunciation Assessment，暂不能给音素级发音分数。"
        return parsed
    return local_ielts_speaking_feedback(part, question, transcript, duration_sec, azure_configured)


def build_ielts_speaking_prompt(part: str, question: str, transcript: str, duration_sec: int, azure_configured: bool) -> str:
    return f"""
你是 IELTS Speaking 教练。请根据以下口语回答给出中文反馈。
Part: {part}
Question: {question}
Transcript: {transcript}
Duration seconds: {duration_sec}
Pronunciation API configured: {azure_configured}

请只输出 JSON，不要 Markdown：
{{
  "bandEstimate": "5.5-7.0 之间的一个估计",
  "fluency": "流利度反馈，具体到停顿、长度、组织",
  "vocabulary": "词汇反馈，指出可替换表达",
  "grammar": "语法反馈，指出优先修正点",
  "pronunciation": "如果没有发音 API，不要编造音素问题，只说明无法做音素级评估",
  "topProblems": ["最优先修正的问题1", "问题2", "问题3"],
  "betterVersion": "保持用户原意的更自然英文版本，80-130词以内",
  "nextQuestion": "下一道同 Part 练习题"
}}
""".strip()


def parse_json_object(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.S)
    if match:
        cleaned = match.group(0)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def local_ielts_speaking_feedback(part: str, question: str, transcript: str, duration_sec: int, azure_configured: bool) -> dict:
    words = re.findall(r"[A-Za-z']+", transcript)
    word_count = len(words)
    lower = transcript.lower()
    fillers = re.findall(r"\b(?:um|uh|er|like|you know|actually|basically)\b", lower)
    sentence_count = max(1, len(re.findall(r"[.!?。！？]", transcript)) or round(word_count / 18) or 1)
    words_per_sentence = word_count / sentence_count
    target_min, target_max = {
        "part2": (90, 140),
        "part3": (45, 80),
    }.get(part, (25, 55))
    band = 5.5
    if word_count >= 60:
        band += 0.4
    if word_count >= 120:
        band += 0.3
    if target_min <= duration_sec <= target_max:
        band += 0.3
    if len(fillers) > 4:
        band -= 0.3
    if words_per_sentence > 28 or words_per_sentence < 7:
        band -= 0.2
    band = max(4.5, min(7.5, round(band * 2) / 2))
    pronunciation = "Azure Speech Pronunciation Assessment 已配置，可在下一步接入音素、重音、流利度细分。"
    pronunciation_status = "configured"
    if not azure_configured:
        pronunciation = "未配置 Azure Speech Pronunciation Assessment，暂不能给音素级发音分数。"
        pronunciation_status = "not_configured"
    return {
        "bandEstimate": f"{band:.1f}",
        "fluency": "回答偏短，先保证直接回答、原因、例子三步完整。" if word_count < 40 else f"词数约 {word_count}，长度可用；下一步减少重复开头和填充词。",
        "vocabulary": "按转写文本粗评：每次回答至少加入 2 个主题词和 1 个具体动词/形容词，避免一直用 good、important、interesting。",
        "grammar": "先保证简单句准确，再稳定加入 because、although、which 等复合句。不要为了复杂而牺牲清晰。",
        "pronunciation": pronunciation,
        "topProblems": [
            f"填充词数量：{len(fillers)}。",
            f"录音时长：{duration_sec} 秒；本题建议 {target_min}-{target_max} 秒。",
            "发音细节需要接 Azure Speech key 后评估。" if not azure_configured else "下一步接入真实音频上传后输出发音细分。"
        ],
        "betterVersion": better_speaking_version(part),
        "nextQuestion": next_speaking_question(part, question),
        "source": "local_fallback",
        "pronunciationStatus": pronunciation_status,
    }


def better_speaking_version(part: str) -> str:
    if part == "part2":
        return "I would like to talk about a useful skill I learned recently. At first, I found it difficult because I did not have a clear method, so I broke it into smaller steps and practised a little every day. Gradually, I became more confident, and the skill started to help me in both work and study."
    if part == "part3":
        return "In my view, people learn faster when they have clear feedback and a strong reason to improve. Motivation matters, but the environment is also important. For example, a good teacher or a useful tool can help learners avoid wasting time and focus on the real problem."
    return "Yes, I do. I think it is important because it affects my daily routine. For example, I often use it when I study or work, and it helps me save time and stay organised."


def next_speaking_question(part: str, current: str) -> str:
    questions = {
        "part1": ["What do you usually do after work?", "Do you prefer studying alone or with others?", "How often do you use technology?"],
        "part2": ["Describe a difficult task you completed successfully.", "Describe a place where you can concentrate well.", "Describe a project you made with AI."],
        "part3": ["How has technology changed education?", "Should companies train young employees?", "What qualities help people change careers?"],
    }.get(part, [])
    for question in questions:
        if question != current:
            return question
    return questions[0] if questions else "Tell me more about this topic."


def call_model(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""
    model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
    base_urls = get_base_urls()
    try:
        _, analysis, _, _ = call_any_model(base_urls, api_key, model, prompt, timeout=30)
        return analysis
    except Exception:
        return ""


def get_base_urls() -> list[str]:
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


def call_any_model(base_urls: list[str], api_key: str, model: str, prompt: str, timeout: int = 60):
    errors = []
    for base_url in base_urls:
        try:
            data = call_responses_api(base_url, api_key, model, prompt, timeout=timeout)
            return data, data.get("output_text") or extract_response_text(data), "responses", base_url
        except Exception as error:
            errors.append(f"{base_url}/responses: {error}")
        try:
            data = call_chat_completions_api(base_url, api_key, model, prompt, timeout=timeout)
            return data, extract_chat_completion_text(data), "chat/completions", base_url
        except Exception as error:
            errors.append(f"{base_url}/chat/completions: {error}")
    raise RuntimeError("; ".join(errors))


def call_responses_api(base_url: str, api_key: str, model: str, prompt: str, timeout: int = 60) -> dict:
    request_body = json.dumps({"model": model, "input": prompt}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/responses",
        data=request_body,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        if not raw.strip():
            return {"choices": [{"message": {"content": ""}}], "_empty_response": True}
        return json.loads(raw)


def call_chat_completions_api(base_url: str, api_key: str, model: str, prompt: str, timeout: int = 60) -> dict:
    request_body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是 ExamPilot 学习助手，请给出具体、简洁、可执行的中文建议。"},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=request_body,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def protect_non_ascii_prompt(prompt: str) -> str:
    if not any(ord(char) > 127 for char in prompt):
        return prompt
    escaped = prompt.encode("unicode_escape").decode("ascii")
    return (
        "The following user request is encoded with Python unicode_escape because the API relay may corrupt "
        "non-ASCII input. Decode the escape sequences mentally first, then answer the original request in "
        "Simplified Chinese.\n\n"
        f"Encoded request:\n{escaped}"
    )


def extract_chat_completion_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return json.dumps(data, ensure_ascii=False, indent=2)
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if content is None and choices[0].get("text"):
        return choices[0].get("text")
    return json.dumps(content, ensure_ascii=False, indent=2)


def main():
    mimetypes.add_type("text/javascript", ".js")
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("ExamPilot local API running at http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
