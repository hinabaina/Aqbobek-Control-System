"""Seed Aqbobek school.db with REAL teachers + schedule from user-provided PDFs.

Run: python3 backend/seed_real_data.py
"""
import json
import sqlite3
import re
import sys
from pathlib import Path

DB_PATH = "/app/data/school.db"

# Canonical lesson time slots we will keep in the schedule.
TIME_SLOTS = ["08:00", "09:05", "10:10", "11:00", "11:50", "13:05", "14:20", "15:05"]

# Raw teacher data from "нагрузка учителей для хакатона 2025-2026.pdf"
RAW_TEACHERS = [
    {"full_name": "Нажмадинов Марат", "role": "Учитель", "subject": "Алгебра/Геометрия/ҰБТ"},
    {"full_name": "Есалина Айзада", "role": "Учитель", "subject": "Алгебра/Геометрия"},
    {"full_name": "Даулетбаева Сая", "role": "Учитель", "subject": "Алгебра/Геометрия"},
    {"full_name": "Жоламан Мейрамбек", "role": "Учитель", "subject": "Алгебра/Геометрия"},
    {"full_name": "Арыстанғалиқызы Ақмарал", "role": "Учитель", "subject": "Алгебра/Геометрия"},
    {"full_name": "Байдирахманова Б.С.", "role": "Учитель", "subject": "Алгебра/Геометрия"},
    {"full_name": "Сулейманов Бегдулла", "role": "Учитель", "subject": "Физика"},
    {"full_name": "Сунгариева Айгерим Бисенбаевна", "role": "Учитель", "subject": "Физика"},
    {"full_name": "Ахметова Индира", "role": "Учитель", "subject": "Информатика/Программалау"},
    {"full_name": "Сапар Елжан Шакизадаұлы", "role": "Учитель", "subject": "Информатика"},
    {"full_name": "Курмангалиев Е.К.", "role": "Учитель", "subject": "Информатика"},
    {"full_name": "Балтабай Жанболат Бекболатұлы", "role": "Учитель", "subject": "Қазақстан тарихы/Дүниежүзі тарихы"},
    {"full_name": "Қангерей Қанат", "role": "Учитель", "subject": "Қазақстан тарихы/Дүниежүзі тарихы/Құқық"},
    {"full_name": "Иван Оралсын", "role": "Учитель", "subject": "Қазақстан тарихы/Дүниежүзі тарихы"},
    {"full_name": "Сарқытбаев Н.", "role": "Учитель", "subject": "АӘД/Тарих/Құқық"},
    {"full_name": "Ақырап Ақерке", "role": "Учитель", "subject": "IELTS/Ағылшын тілі"},
    {"full_name": "Таңатар Мадина", "role": "Учитель", "subject": "IELTS/Ағылшын тілі"},
    {"full_name": "Қайыржанова Аружан", "role": "Учитель", "subject": "Ағылшын тілі/Китайский"},
    {"full_name": "Халелова Анель", "role": "Куратор", "subject": "Қазақ тілі/Қазақ әдебиеті"},
    {"full_name": "Бактыгулов Аманжол", "role": "Учитель", "subject": "Қазақ тілі/Қазақ әдебиеті/Абайтану"},
    {"full_name": "Утенова Куралай", "role": "Учитель", "subject": "Қазақ тілі/Қазақ әдебиеті/Абайтану"},
    {"full_name": "Жомартова Айым Кайратқызы", "role": "Куратор", "subject": "Қазақ тілі/Қазақ әдебиеті/Абайтану"},
    {"full_name": "Таукенова Г.З.", "role": "Учитель", "subject": "Қазақ тілі/Қазақ әдебиеті"},
    {"full_name": "Матигулова Гульсара Бактыбергеновна", "role": "Учитель", "subject": "Орыс тілі мен әдебиеті"},
    {"full_name": "Гореева Альфия Махмудовна", "role": "Учитель", "subject": "Орыс тілі мен әдебиеті"},
    {"full_name": "Жадырасын Ернұр", "role": "Учитель", "subject": "География"},
    {"full_name": "Касимов Е.К.", "role": "Учитель", "subject": "География"},
    {"full_name": "Караева Аружан", "role": "Учитель", "subject": "Биология"},
    {"full_name": "Қайырқұлов Нұрсұлтан Амангелдіұлы", "role": "Учитель", "subject": "Биология"},
    {"full_name": "Шарафадинова Айжан Мырзабекқызы", "role": "Учитель", "subject": "Биология"},
    {"full_name": "Назаров Дастан", "role": "Учитель", "subject": "Химия"},
    {"full_name": "Аманғазы Сәнім", "role": "Учитель", "subject": "Химия"},
    {"full_name": "Аділов Тлепберген Бекболұлы", "role": "Учитель", "subject": "Дене тәрбиесі"},
    {"full_name": "Қарабай Айбат Нұрлыбайұлы", "role": "Учитель", "subject": "Дене тәрбиесі"},
    {"full_name": "Қойшан Ырысжан Асқарбекқызы", "role": "Учитель", "subject": "Көркем еңбек"},
    {"full_name": "Қазиев Нұртлеу", "role": "Учитель", "subject": "Көркем еңбек"},
    {"full_name": "Жаулбаев А.З.", "role": "Специалист", "subject": "Профориентация"},
    {"full_name": "Душманова А.Қ.", "role": "Психолог", "subject": "Психология"},
    {"full_name": "Саламатұлы А.", "role": "Куратор", "subject": "Тәрбие сағаты"},
    {"full_name": "Мұрат Ә.", "role": "Куратор", "subject": "Тәрбие сағаты"},
    {"full_name": "Косов М.", "role": "Учитель", "subject": "Робототехника"},
]

# ------- Schedule short-name matching helpers -------
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def match_teacher(short: str, all_teachers: list[dict]) -> int | None:
    """Map 'Байдирахманова Б.С.' to a full_name row id."""
    if not short:
        return None
    # strip trailing punctuation
    s = norm(short.replace(".", " "))
    # split into tokens (first non-empty → surname)
    parts = [p for p in s.split() if p]
    if not parts:
        return None
    surname = parts[0].lower()
    # Try exact surname prefix match
    candidates = []
    for t in all_teachers:
        full = norm(t["full_name"]).lower()
        if full.startswith(surname):
            candidates.append(t)
    if len(candidates) == 1:
        return candidates[0]["id"]
    # Try surname + first initial
    if len(parts) > 1 and candidates:
        initial = parts[1][0].lower()
        for t in candidates:
            full = norm(t["full_name"]).lower().split()
            if len(full) > 1 and full[1].startswith(initial):
                return t["id"]
        return candidates[0]["id"]
    if candidates:
        return candidates[0]["id"]
    return None


def normalize_time(raw: str) -> str | None:
    """'10.10-10:55' → '10:10'. Map to canonical slots."""
    if not raw:
        return None
    m = re.search(r"(\d{1,2})[:.](\d{2})", raw)
    if not m:
        return None
    hh, mm = m.group(1), m.group(2)
    cand = f"{int(hh):02d}:{mm}"
    if cand in TIME_SLOTS:
        return cand
    # Try nearest canonical
    for slot in TIME_SLOTS:
        if slot.startswith(f"{int(hh):02d}:"):
            return slot
    return None


# ------- Main seed -------
def load_schedule_json() -> list[dict]:
    path = Path(__file__).parent.parent / "data" / "real_schedule.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Seed teachers (idempotent by full_name).
    added = 0
    for t in RAW_TEACHERS:
        cur.execute("SELECT id FROM employees WHERE full_name = ?", (t["full_name"],))
        row = cur.fetchone()
        if row:
            # update subject/role in case they changed
            cur.execute(
                "UPDATE employees SET role = ?, subject = ? WHERE id = ?",
                (t["role"], t["subject"], row["id"]),
            )
        else:
            cur.execute(
                "INSERT INTO employees (full_name, role, subject) VALUES (?,?,?)",
                (t["full_name"], t["role"], t["subject"]),
            )
            added += 1
    conn.commit()
    print(f"Teachers seeded: +{added} (total {len(RAW_TEACHERS)} canonical)")

    # 2. Seed schedule
    schedule_data = load_schedule_json()
    if not schedule_data:
        print("No schedule JSON found at /app/data/real_schedule.json — skipping schedule.")
        conn.close()
        return

    cur.execute("SELECT id, full_name FROM employees")
    all_teachers = [dict(r) for r in cur.fetchall()]

    # Clear existing schedule and re-seed (non-destructive for other tables)
    cur.execute("DELETE FROM schedule")
    conn.commit()

    inserted = 0
    skipped = 0
    unmatched: set[str] = set()
    for item in schedule_data:
        teacher_name = item.get("teacher_name") or ""
        # Some rows have "subject teacher" concatenated, skip those without teacher_name
        if not teacher_name or teacher_name.isdigit():
            skipped += 1
            continue
        tid = match_teacher(teacher_name, all_teachers)
        if not tid:
            unmatched.add(teacher_name)
            skipped += 1
            continue
        time_norm = normalize_time(item.get("lesson_time", ""))
        if not time_norm:
            skipped += 1
            continue
        class_name = norm(item.get("class_name", ""))
        day = norm(item.get("day_of_week", ""))
        room = norm(item.get("room", "")) or "—"
        if not class_name or not day:
            skipped += 1
            continue
        # de-dup identical slots
        cur.execute(
            "SELECT id FROM schedule WHERE teacher_id=? AND class_name=? AND day_of_week=? AND lesson_time=? AND room=?",
            (tid, class_name, day, time_norm, room),
        )
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO schedule (teacher_id, class_name, day_of_week, lesson_time, room) VALUES (?,?,?,?,?)",
            (tid, class_name, day, time_norm, room),
        )
        inserted += 1
    conn.commit()
    print(f"Schedule seeded: {inserted} rows, skipped {skipped}.")
    if unmatched:
        print("Unmatched teachers (first 15):", list(unmatched)[:15])
    conn.close()


if __name__ == "__main__":
    main()
