"""Greedy schedule generator for Aqbobek ACS.

Input:
  classes: [{"class_name": "3А", "subjects": [{"subject": "Алгебра", "hours": 5}, ...]}]
  teachers: [{"id": 1, "full_name": "...", "subject": "Алгебра/Геометрия"}]
  rooms: ["101", "102", "спортзал", ...]
  days: list[str] (default Пн..Пт)
  times: list[str] (default 08:00..13:00)

Output:
  [{"teacher_id", "class_name", "day_of_week", "lesson_time", "room"}, ...]
"""
from __future__ import annotations
from typing import Any

DEFAULT_DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
DEFAULT_TIMES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"]


def _subject_matches(teacher_subj: str, need: str) -> bool:
    if not teacher_subj or not need:
        return False
    ts = teacher_subj.lower()
    nd = need.lower()
    if nd in ts or ts in nd:
        return True
    for tok in ts.replace("/", " ").split():
        if tok and tok in nd:
            return True
    return False


def generate_schedule(
    classes: list[dict],
    teachers: list[dict],
    rooms: list[str],
    days: list[str] | None = None,
    times: list[str] | None = None,
) -> dict[str, Any]:
    days = days or DEFAULT_DAYS
    times = times or DEFAULT_TIMES
    rooms = rooms or ["101", "102", "103", "104", "105"]

    # occupancy
    busy_teacher: set[tuple[int, str, str]] = set()  # (teacher_id, day, time)
    busy_room: set[tuple[str, str, str]] = set()     # (room, day, time)
    busy_class: set[tuple[str, str, str]] = set()    # (class, day, time)

    result: list[dict] = []
    conflicts: list[str] = []

    for cls in classes:
        class_name = cls["class_name"]
        for subj in cls.get("subjects", []):
            subject = subj["subject"]
            hours = int(subj.get("hours", 1))
            candidates = [t for t in teachers if _subject_matches(t.get("subject", ""), subject)]
            if not candidates:
                conflicts.append(f"{class_name} · {subject}: нет учителя")
                continue
            placed = 0
            for day in days:
                for time in times:
                    if placed >= hours:
                        break
                    if (class_name, day, time) in busy_class:
                        continue
                    teacher = None
                    for t in candidates:
                        if (t["id"], day, time) not in busy_teacher:
                            teacher = t
                            break
                    if not teacher:
                        continue
                    room = None
                    for r in rooms:
                        if (r, day, time) not in busy_room:
                            room = r
                            break
                    if not room:
                        continue
                    busy_teacher.add((teacher["id"], day, time))
                    busy_room.add((room, day, time))
                    busy_class.add((class_name, day, time))
                    result.append(
                        {
                            "teacher_id": teacher["id"],
                            "class_name": class_name,
                            "day_of_week": day,
                            "lesson_time": time,
                            "room": room,
                            "subject": subject,
                        }
                    )
                    placed += 1
                if placed >= hours:
                    break
            if placed < hours:
                conflicts.append(f"{class_name} · {subject}: удалось {placed}/{hours}")
    return {"schedule": result, "conflicts": conflicts}


def find_substitute_candidates(
    absent_teacher: dict,
    lesson: dict,
    all_teachers: list[dict],
    all_schedule: list[dict],
) -> list[dict]:
    """Return teachers who are FREE during lesson's time slot and have similar subject."""
    day = lesson["day_of_week"]
    time = lesson["lesson_time"]
    busy_ids = {
        s["teacher_id"] for s in all_schedule
        if s["day_of_week"] == day and s["lesson_time"] == time
    }
    subj = absent_teacher.get("subject") or ""
    out = []
    for t in all_teachers:
        if t["id"] == absent_teacher["id"]:
            continue
        if t["id"] in busy_ids:
            continue
        load_today = sum(
            1 for s in all_schedule if s["teacher_id"] == t["id"] and s["day_of_week"] == day
        )
        out.append({
            **t,
            "load_today": load_today,
            "subject_match": _subject_matches(t.get("subject", ""), subj),
        })
    # sort: subject match first, then lower load
    out.sort(key=lambda x: (not x["subject_match"], x["load_today"]))
    return out
