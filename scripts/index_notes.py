import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


TEXT_EXTENSIONS = {".md", ".txt"}


def iter_files(roots):
    for root in roots:
        path = Path(root)
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            yield path
        elif path.is_dir():
            for item in path.rglob("*"):
                if item.is_file() and item.suffix.lower() in TEXT_EXTENSIONS:
                    yield item


def read_text(path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def summarize(text, limit=240):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined = " ".join(lines)
    return joined[:limit]


def infer_subject(path):
    parts = {part.lower() for part in path.parts}
    if "math" in parts:
        return "math"
    if "english" in parts:
        return "english"
    if "professional-course" in parts:
        return "economics"
    if "politics" in parts:
        return "politics"
    if "ielts-wiki" in parts:
        return "ielts"
    return "general"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    records = []
    for path in iter_files(args.roots):
        text = read_text(path)
        digest = hashlib.sha1(str(path).encode("utf-8") + text[:2000].encode("utf-8", errors="ignore")).hexdigest()
        records.append(
            {
                "id": digest[:12],
                "path": str(path),
                "subject": infer_subject(path),
                "suffix": path.suffix.lower(),
                "chars": len(text),
                "summary": summarize(text),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(records)} files -> {out}")


if __name__ == "__main__":
    main()
