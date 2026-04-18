"""Ribbon scheduling strategies (NIS-style / Сингапурская методика).

A "ribbon" is one time slot (day + lesson_time) where students from one or
several classes are re-distributed into groups (usually by level).

Four strategies — use the Strategy pattern:
  1. split          — одна параллель / один класс делится на N групп
  2. parallel_level — несколько классов параллели сливаются и делятся по уровням
  3. cross_class    — межпараллельное смешивание (например 7A+8A объединяют на спецкурс)
  4. merge          — несколько групп обратно собираются в один общий урок

Every strategy exposes:
    validate(ribbon, groups, db) -> list[str]   # returns conflict messages
    describe(ribbon, groups)     -> str         # human-readable summary
"""
from __future__ import annotations
import json
from abc import ABC, abstractmethod
from typing import Any

from db import query, query_one


class RibbonStrategy(ABC):
    key: str = ""
    title: str = ""

    @abstractmethod
    def validate(self, ribbon: dict, groups: list[dict]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def describe(self, ribbon: dict, groups: list[dict]) -> str:
        raise NotImplementedError


def _base_conflicts(ribbon: dict, groups: list[dict]) -> list[str]:
    """Conflicts common to every strategy."""
    problems: list[str] = []
    day = ribbon["day_of_week"]
    time = ribbon["lesson_time"]

    # Teacher busy in schedule (outside this ribbon)
    teacher_ids = [g["teacher_id"] for g in groups if g.get("teacher_id")]
    if teacher_ids:
        qmarks = ",".join("?" * len(teacher_ids))
        busy = query(
            f"SELECT teacher_id, class_name FROM schedule WHERE day_of_week=? AND lesson_time=? "
            f"AND teacher_id IN ({qmarks})",
            [day, time, *teacher_ids],
        )
        for b in busy:
            problems.append(
                f"Учитель id={b['teacher_id']} уже ведёт урок в {b['class_name']} в {day} {time}"
            )

    # Rooms busy (same day+time in schedule outside this ribbon)
    rooms = [g["room"] for g in groups if g.get("room")]
    if rooms:
        qmarks = ",".join("?" * len(rooms))
        busy = query(
            f"SELECT room, class_name FROM schedule WHERE day_of_week=? AND lesson_time=? "
            f"AND room IN ({qmarks})",
            [day, time, *rooms],
        )
        for b in busy:
            problems.append(f"Кабинет {b['room']} занят классом {b['class_name']} в {day} {time}")

    # Same teacher in two groups of the same ribbon
    seen_t: dict[int, str] = {}
    for g in groups:
        tid = g.get("teacher_id")
        if tid in seen_t:
            problems.append(f"Учитель id={tid} назначен сразу в 2 группы ленты ({seen_t[tid]} и {g.get('group_name')})")
        else:
            seen_t[tid] = g.get("group_name", "?")

    # Same room used twice in the same ribbon
    seen_r: dict[str, str] = {}
    for g in groups:
        r = g.get("room")
        if r and r in seen_r:
            problems.append(f"Кабинет {r} занят двумя группами ленты ({seen_r[r]} и {g.get('group_name')})")
        elif r:
            seen_r[r] = g.get("group_name", "?")

    # A student must not appear in two groups simultaneously
    seen_s: dict[str, str] = {}
    for g in groups:
        students = g.get("students") or []
        if isinstance(students, str):
            try:
                students = json.loads(students)
            except Exception:
                students = []
        for s in students:
            key = str(s).strip().lower()
            if not key:
                continue
            if key in seen_s:
                problems.append(f"Ученик '{s}' одновременно в группах {seen_s[key]} и {g.get('group_name')}")
            else:
                seen_s[key] = g.get("group_name", "?")

    # Capacity check
    for g in groups:
        cap = g.get("capacity") or 30
        students = g.get("students") or []
        if isinstance(students, str):
            try:
                students = json.loads(students)
            except Exception:
                students = []
        if len(students) > cap:
            problems.append(
                f"Группа '{g.get('group_name')}' перегружена: {len(students)}/{cap}"
            )
    return problems


class SplitStrategy(RibbonStrategy):
    key = "split"
    title = "Деление одного класса на группы"

    def validate(self, ribbon, groups):
        problems = _base_conflicts(ribbon, groups)
        src = json.loads(ribbon.get("source_classes") or "[]")
        if len(src) != 1:
            problems.append("Стратегия SPLIT требует ровно 1 исходный класс")
        if len(groups) < 2:
            problems.append("В SPLIT должно быть минимум 2 группы")
        return problems

    def describe(self, ribbon, groups):
        src = json.loads(ribbon.get("source_classes") or "[]")
        return f"{src[0] if src else '?'} делится на {len(groups)} групп ({ribbon['day_of_week']} {ribbon['lesson_time']})"


class ParallelLevelStrategy(RibbonStrategy):
    key = "parallel_level"
    title = "Параллель классов делится по уровням"

    def validate(self, ribbon, groups):
        problems = _base_conflicts(ribbon, groups)
        src = json.loads(ribbon.get("source_classes") or "[]")
        if len(src) < 2:
            problems.append("Стратегия PARALLEL требует минимум 2 класса")
        # All source classes must share the same parallel (e.g. all start with '7')
        parallels = {s.rstrip("АБВГДЕЖЗABCDE") for s in src}
        if len(parallels) > 1:
            problems.append(f"Классы {src} из разных параллелей — используй стратегию CROSS")
        return problems

    def describe(self, ribbon, groups):
        src = json.loads(ribbon.get("source_classes") or "[]")
        levels = [g.get("level") or g.get("group_name") for g in groups]
        return f"Параллель {'+'.join(src)} по уровням: {', '.join(levels)}"


class CrossClassStrategy(RibbonStrategy):
    key = "cross_class"
    title = "Смешивание классов из разных параллелей"

    def validate(self, ribbon, groups):
        problems = _base_conflicts(ribbon, groups)
        src = json.loads(ribbon.get("source_classes") or "[]")
        if len(src) < 2:
            problems.append("Стратегия CROSS требует минимум 2 класса")
        parallels = {s.rstrip("АБВГДЕЖЗABCDE") for s in src}
        if len(parallels) < 2:
            problems.append("CROSS имеет смысл только для разных параллелей — используй PARALLEL_LEVEL")
        return problems

    def describe(self, ribbon, groups):
        src = json.loads(ribbon.get("source_classes") or "[]")
        return f"Спецкурс для {'+'.join(src)}: {len(groups)} групп"


class MergeStrategy(RibbonStrategy):
    key = "merge"
    title = "Слияние групп обратно в общий урок"

    def validate(self, ribbon, groups):
        problems = _base_conflicts(ribbon, groups)
        if len(groups) != 1:
            problems.append("Стратегия MERGE должна содержать ровно одну итоговую группу")
        return problems

    def describe(self, ribbon, groups):
        src = json.loads(ribbon.get("source_classes") or "[]")
        g = groups[0] if groups else {}
        return f"Объединение {'+'.join(src)} на '{g.get('subject', '?')}' в кабинете {g.get('room', '?')}"


STRATEGIES: dict[str, RibbonStrategy] = {
    s.key: s
    for s in [SplitStrategy(), ParallelLevelStrategy(), CrossClassStrategy(), MergeStrategy()]
}


def get_strategy(key: str) -> RibbonStrategy:
    s = STRATEGIES.get((key or "").lower())
    if not s:
        raise ValueError(f"Неизвестная стратегия ленты: {key}. Доступны: {list(STRATEGIES)}")
    return s


def validate_ribbon(ribbon: dict, groups: list[dict]) -> dict[str, Any]:
    strat = get_strategy(ribbon.get("strategy", "split"))
    problems = strat.validate(ribbon, groups)
    return {
        "strategy": strat.key,
        "title": strat.title,
        "describe": strat.describe(ribbon, groups),
        "conflicts": problems,
        "valid": len(problems) == 0,
    }
