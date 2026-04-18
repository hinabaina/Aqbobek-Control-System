"""AI Estimation Engine + Smart Placement for teacher tasks."""
from __future__ import annotations
import json
from datetime import datetime, date
from typing import Optional

import ai
from db import query, query_one, execute

DEFAULT_TIMES = ["08:00", "09:05", "10:10", "11:00", "11:50", "13:05", "14:20", "15:05"]
DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
DAY_INDEX = {d: i for i, d in enumerate(DAYS)}


async def estimate_duration(text: str) -> int:
    """Ask LLM to estimate expected duration (minutes)."""
    system = (
        "Ты — эксперт по тайм-менеджменту в школе. Оцени, сколько минут займёт выполнение "
        "поручения. Верни СТРОГО JSON вида {\"minutes\": <int 10..240>, \"reasoning\": <str на русском>}. "
        "Простые поручения (позвонить, проверить чат): 10-20 мин. Подготовка актового зала или обход: 45-90 мин. "
        "Методические совещания и проверка тетрадей: 60-120 мин."
    )
    try:
        out = await ai.chat_json(system, text)
        m = int(out.get("minutes", 45))
        return max(10, min(240, m))
    except Exception:
        return 45  # sensible default if LLM unavailable


def _teacher_busy_map(teacher_id: int) -> dict[str, set[str]]:
    """Return {day: {time, ...}} when teacher is busy in schedule or scheduled tasks."""
    busy: dict[str, set[str]] = {d: set() for d in DAYS}
    for r in query(
        "SELECT day_of_week, lesson_time FROM schedule WHERE teacher_id = ?",
        (teacher_id,),
    ):
        if r["day_of_week"] in busy:
            busy[r["day_of_week"]].add(r["lesson_time"])
    for r in query(
        "SELECT scheduled_day, scheduled_time FROM tasks "
        "WHERE assigned_to = ? AND scheduled_day IS NOT NULL AND status != 'done'",
        (teacher_id,),
    ):
        if r["scheduled_day"] in busy:
            busy[r["scheduled_day"]].add(r["scheduled_time"])
    return busy


def find_open_window(teacher_id: int, from_day_index: int = 0) -> Optional[dict]:
    """Return next available (day, time) slot (window) for a teacher starting at from_day_index."""
    busy = _teacher_busy_map(teacher_id)
    today = date.today()
    today_idx = today.weekday() if today.weekday() < 5 else 0
    start = max(from_day_index, today_idx)
    # scan forward through week
    for di in range(start, len(DAYS)):
        day = DAYS[di]
        for t in DEFAULT_TIMES:
            if t not in busy[day]:
                return {"day": day, "time": t}
    # wrap: check earlier part of week (next week)
    for di in range(0, start):
        day = DAYS[di]
        for t in DEFAULT_TIMES:
            if t not in busy[day]:
                return {"day": day, "time": t}
    return None


def place_task(task_id: int) -> Optional[dict]:
    """Find and persist open window for an existing task. Returns slot or None."""
    t = query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not t or not t.get("assigned_to"):
        return None
    slot = find_open_window(t["assigned_to"])
    if not slot:
        return None
    execute(
        "UPDATE tasks SET scheduled_day = ?, scheduled_time = ? WHERE id = ?",
        (slot["day"], slot["time"], task_id),
    )
    return slot


def reschedule_tasks_on_schedule_change(teacher_id: int) -> int:
    """When a teacher's schedule changes, shift their already-scheduled tasks that now conflict."""
    busy = _teacher_busy_map(teacher_id)
    affected = 0
    tasks = query(
        "SELECT id, scheduled_day, scheduled_time FROM tasks "
        "WHERE assigned_to = ? AND scheduled_day IS NOT NULL AND status != 'done'",
        (teacher_id,),
    )
    for t in tasks:
        # check by asking schedule directly (to ignore self-task)
        lesson = query_one(
            "SELECT id FROM schedule WHERE teacher_id = ? AND day_of_week = ? AND lesson_time = ?",
            (teacher_id, t["scheduled_day"], t["scheduled_time"]),
        )
        if lesson:
            slot = find_open_window(teacher_id)
            if slot:
                execute(
                    "UPDATE tasks SET scheduled_day = ?, scheduled_time = ? WHERE id = ?",
                    (slot["day"], slot["time"], t["id"]),
                )
                affected += 1
    return affected
