"""Groq AI helpers for Aqbobek ACS (same key as the Telegram bot)."""
import os
import json
import aiohttp
from typing import Optional

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
WHISPER_MODEL = "whisper-large-v3-turbo"


def _key() -> str:
    return os.environ["GROQ_API_KEY"]


async def chat_json(system: str, user: str, model: str = DEFAULT_MODEL) -> dict:
    """Call Groq and force a JSON response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as sess:
        async with sess.post(GROQ_URL, json=payload, headers=headers, timeout=60) as r:
            data = await r.json()
            if r.status != 200:
                raise RuntimeError(f"Groq API error: {data}")
            raw = data["choices"][0]["message"]["content"]
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)


async def chat_text(system: str, user: str, model: str = DEFAULT_MODEL, temperature: float = 0.3) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as sess:
        async with sess.post(GROQ_URL, json=payload, headers=headers, timeout=60) as r:
            data = await r.json()
            if r.status != 200:
                raise RuntimeError(f"Groq API error: {data}")
            return data["choices"][0]["message"]["content"]


async def transcribe_audio(file_bytes: bytes, filename: str = "voice.webm") -> str:
    data = aiohttp.FormData()
    data.add_field("file", file_bytes, filename=filename, content_type="audio/webm")
    data.add_field("model", WHISPER_MODEL)
    headers = {"Authorization": f"Bearer {_key()}"}
    async with aiohttp.ClientSession() as sess:
        async with sess.post(GROQ_WHISPER_URL, data=data, headers=headers, timeout=120) as r:
            data_j = await r.json()
            if r.status != 200:
                raise RuntimeError(f"Groq Whisper error: {data_j}")
            return (data_j.get("text") or "").strip()


async def parse_voice_to_tasks(text: str, employees: list[dict]) -> list[dict]:
    """Given a voice transcript and list of employees, return tasks list."""
    names = ", ".join(f"{e['id']}={e['full_name']}" for e in employees)
    system = (
        "Ты — диспетчер задач школы Aqbobek. Пользователь надиктовал поручения. "
        "Разбей речь на несколько отдельных задач. Для каждой найди подходящего сотрудника "
        "из справочника. Верни СТРОГО JSON вида: "
        '{"tasks":[{"assigned_to_id": <int|null>, "assigned_to_name": <str|null>, '
        '"title": <str>, "description": <str>, "priority": "low|medium|high", '
        '"due_date": <str|null>}]}. '
        f"Справочник сотрудников: {names}. Язык результата — русский."
    )
    result = await chat_json(system, text)
    return result.get("tasks", [])


async def suggest_substitute(
    absent_teacher: dict,
    lesson: dict,
    candidates: list[dict],
) -> dict:
    """Ask AI which candidate is the best substitute for a missing teacher."""
    cand_txt = "\n".join(
        f"- id={c['id']} {c['full_name']} ({c.get('subject') or c.get('role')}) "
        f"сегодня уроков: {c.get('load_today', 0)}"
        for c in candidates
    )
    system = (
        "Ты — AI-завуч. Нужно найти замену для заболевшего учителя. Выбери ОДНОГО самого подходящего "
        "из списка кандидатов по совпадению предмета/квалификации и минимальной текущей нагрузке. "
        "Верни JSON: {\"substitute_id\": <int>, \"reason\": <str на русском>}. "
        "Если подходящих нет — верни substitute_id=null и reason."
    )
    user = (
        f"Отсутствующий учитель: {absent_teacher.get('full_name')} "
        f"({absent_teacher.get('subject') or absent_teacher.get('role')}).\n"
        f"Урок: класс {lesson.get('class_name')}, {lesson.get('day_of_week')} "
        f"{lesson.get('lesson_time')}, кабинет {lesson.get('room')}.\n"
        f"Кандидаты:\n{cand_txt}"
    )
    return await chat_json(system, user)


async def simplify_order(text: str, mode: str = "simplify") -> str:
    if mode == "generate":
        system = (
            "Ты — юрист-делопроизводитель школы Казахстана. Сгенерируй официальный приказ директора школы "
            "на русском языке по описанию задачи. Используй структуру: шапка (школа), номер приказа, дата, "
            "преамбула 'В целях ...', основная часть 'ПРИКАЗЫВАЮ:' со списком пунктов, "
            "ответственные, сроки, подпись директора. Делай формулировки точными и юридически корректными."
        )
    else:
        system = (
            "Перепиши сложный бюрократический приказ для учителей в виде понятного, короткого чек-листа "
            "на русском языке. Используй маркированные пункты, простой язык, без воды. Добавь короткое "
            "резюме в 1-2 строки в начале."
        )
    return await chat_text(system, text, temperature=0.3)


async def generate_schedule_ai(constraints: dict) -> dict:
    system = (
        "Ты — генератор школьного расписания. На вход — список классов с предметами (часы в неделю), "
        "список учителей (имя, предмет, id), список кабинетов. Верни JSON "
        '{"schedule":[{"teacher_id":<int>,"class_name":<str>,"day_of_week":<str>,'
        '"lesson_time":<str>,"room":<str>}]}. Дни: Понедельник..Пятница. '
        "Время: 08:00, 09:00, 10:00, 11:00, 12:00, 13:00. "
        "Избегай конфликтов (один учитель / один кабинет в один слот). "
        "Распределяй равномерно по дням. Учитывай часы в неделю для каждого предмета."
    )
    return await chat_json(system, json.dumps(constraints, ensure_ascii=False))
