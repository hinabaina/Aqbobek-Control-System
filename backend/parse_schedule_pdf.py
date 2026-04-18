"""Robust parser for /app/data/schedule.pdf → /app/data/real_schedule.json.

Each page contains one pair of classes (e.g. 7A / 7B).
Day markers (Kazakh names) appear between lesson blocks.
We iterate tables per page and track current day.
"""
import json
import re
from pathlib import Path
import pdfplumber

PDF_PATH = "/app/data/schedule.pdf"
OUT_PATH = "/app/data/real_schedule.json"

DAYS = {
    "Дүйсенбі": "Понедельник",
    "Сейсенбі": "Вторник",
    "Сәрсенбі": "Среда",
    "Бейсенбі": "Четверг",
    "Жұма": "Пятница",
}


def clean(s):
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s).replace("\n", " ")).strip()


def split_subject_teacher(cell: str) -> tuple[str, str]:
    c = clean(cell)
    if not c:
        return "", ""
    m = re.search(
        r"\b([А-ЯЁӘІҢҒҮҰҚӨҺ][а-яёәіңғүұқөһ]{2,}(?:[ҚқЕеЖжӘәҰұ][а-яёәіңғүұқөһ]*)?)\s+"
        r"([А-ЯЁӘІҢҒҮҰҚӨҺ]\.?(?:[А-ЯЁӘІҢҒҮҰҚӨҺ]\.?)?)",
        c,
    )
    if m:
        return c[: m.start(1)].strip(), c[m.start(1):].strip()
    parts = c.split()
    if len(parts) >= 3:
        return " ".join(parts[:-2]), " ".join(parts[-2:])
    return c, ""


def find_classes_in_text(text: str) -> list[str]:
    """Find class pair from header. Handles multiple layouts."""
    CLASS_RE = r"(?:1[0-2]|[7-9])\s*[А-ЯA-ZВ]"
    # 'Уақыт № 7A каб 7B' — normal order
    m = re.search(r"Уақыт\s+№?\s*(" + CLASS_RE + r")\s+каб\s+(" + CLASS_RE + r")", text)
    if m:
        return [m.group(1).replace(" ", ""), m.group(2).replace(" ", "")]
    # '10В каб Уақыт № 11А' — reversed
    m = re.search(r"(" + CLASS_RE + r")\s+каб\s+Уақыт\s+№?\s*(" + CLASS_RE + r")", text)
    if m:
        return [m.group(1).replace(" ", ""), m.group(2).replace(" ", "")]
    # Bare pair near start: line like '7C 8A'
    for line in text.split("\n")[:6]:
        m = re.match(r"\s*(" + CLASS_RE + r")\s+(" + CLASS_RE + r")\s*$", line)
        if m:
            return [m.group(1).replace(" ", ""), m.group(2).replace(" ", "")]
    return [None, None]


def day_from_text(text: str) -> str | None:
    for kz, ru in DAYS.items():
        if kz in text:
            return ru
    return None


def parse():
    out = []
    with pdfplumber.open(PDF_PATH) as pdf:
        current_classes = [None, None]
        for page in pdf.pages:
            text = page.extract_text() or ""
            classes = find_classes_in_text(text)
            if classes[0]:
                current_classes = classes
            # Split page text into blocks by day markers
            # We'll iterate tables and look up day from neighboring text context
            tables = page.extract_tables() or []
            # Build a day context map per table row by matching row blobs inside text
            # Simpler: check text for sequence of (day_marker, following lines)
            # Split text into segments by day occurrences (order matters)
            segments = []
            cursor = 0
            for m in re.finditer(r"(" + "|".join(DAYS.keys()) + r")", text):
                segments.append((cursor, m.start(), None))
                cursor = m.start()
            segments.append((cursor, len(text), None))
            # Determine day for each segment
            segs = []
            for a, b, _ in segments:
                chunk = text[a:b]
                d = day_from_text(chunk)
                segs.append((a, b, d))
            # Now for each table row, find which segment it belongs to by searching its time+subject in text
            default_day = None
            for kz, ru in DAYS.items():
                if kz in text:
                    default_day = ru
                    break
            current_day = default_day or "Понедельник"

            # Walk through tables rows sequentially; update current_day if row blob contains a day marker
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    cells = [clean(c) for c in row]
                    blob = " ".join(cells)
                    for kz, ru in DAYS.items():
                        if kz in blob:
                            current_day = ru
                            break
                    if len(cells) < 6:
                        continue
                    m = re.search(r"(\d{1,2})[.:](\d{2})", cells[0])
                    if not m:
                        continue
                    hh, mm = int(m.group(1)), m.group(2)
                    time_norm = f"{hh:02d}:{mm}"
                    for idx, cls_i in ((2, 0), (4, 1)):
                        lesson = cells[idx] if idx < len(cells) else ""
                        room = cells[idx + 1] if idx + 1 < len(cells) else ""
                        cls = current_classes[cls_i]
                        if not lesson or not cls:
                            continue
                        low = lesson.lower()
                        if any(skip in low for skip in ["үй жұмысы", "таңғы ас", "обед", "үзіліс"]):
                            continue
                        subj, teacher = split_subject_teacher(lesson)
                        if not teacher:
                            continue
                        out.append({
                            "class_name": cls,
                            "day_of_week": current_day,
                            "lesson_time": time_norm,
                            "subject": subj,
                            "teacher_name": teacher,
                            "room": room,
                        })
    # dedupe
    seen = set()
    uniq = []
    for r in out:
        key = (r["class_name"], r["day_of_week"], r["lesson_time"], r["teacher_name"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def main():
    rows = parse()
    Path(OUT_PATH).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    # stats
    days = {}
    classes = set()
    for r in rows:
        days[r["day_of_week"]] = days.get(r["day_of_week"], 0) + 1
        classes.add(r["class_name"])
    print(f"Wrote {len(rows)} rows.")
    print(f"Classes: {sorted(classes)}")
    print(f"By day: {days}")


if __name__ == "__main__":
    main()
