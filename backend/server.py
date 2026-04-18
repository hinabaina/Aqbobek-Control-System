"""Aqbobek ACS backend – FastAPI app on shared SQLite (school.db)."""
import os
import logging
from datetime import datetime, date
from typing import Optional, Any
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

import db
import auth
import ai
import schedule_gen

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("acs")

app = FastAPI(title="Aqbobek ACS")
api = APIRouter(prefix="/api")


# ---------- Startup ----------
@app.on_event("startup")
async def on_startup() -> None:
    db.init_schema()
    # Seed teachers if table has no teachers yet (only keeps bot-seed items).
    count = db.query_one("SELECT COUNT(*) as c FROM employees")
    if not count or count["c"] == 0:
        base_teachers = [
            ("Нажмадинов Марат", "Учитель", "Алгебра/Геометрия"),
            ("Есалина Айзада", "Учитель", "Алгебра/Геометрия"),
            ("Сунгариева Айгерим Бисенбаевна", "Учитель", "Физика"),
            ("Ахметова Индира", "Учитель", "Информатика"),
            ("Балтабай Жанболат Бекболатұлы", "Учитель", "История"),
            ("Ақырап Ақерке", "Учитель", "Английский/IELTS"),
            ("Таңатар Мадина", "Учитель", "Английский/IELTS"),
            ("Бактыгулов Аманжол", "Учитель", "Казахский язык"),
            ("Матигулова Гульсара Бактыбергеновна", "Учитель", "Русский язык"),
            ("Жадырасын Ернұр", "Учитель", "География"),
            ("Иванов Иван", "Завхоз", "Хозяйство"),
            ("Петрова Анна", "Секретарь", "Администрация"),
        ]
        for name, role, subj in base_teachers:
            db.execute(
                "INSERT INTO employees (full_name, role, subject) VALUES (?, ?, ?)",
                (name, role, subj),
            )
    auth.seed_admin_and_teachers()
    logger.info("DB initialized at %s", db.DB_PATH)


# ---------- Models ----------
class LoginInput(BaseModel):
    email: str
    password: str


class EmployeeIn(BaseModel):
    full_name: str
    role: str = "Учитель"
    subject: Optional[str] = None
    phone: Optional[str] = None
    qualification: Optional[str] = None
    email: Optional[str] = None
    user_role: Optional[str] = "teacher"


class TaskIn(BaseModel):
    title: str
    description: Optional[str] = ""
    assigned_to: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[str] = None


class StatusIn(BaseModel):
    status: str


class IncidentIn(BaseModel):
    title: str
    description: Optional[str] = ""
    assigned_to: Optional[int] = None
    priority: str = "medium"


class ScheduleIn(BaseModel):
    teacher_id: int
    class_name: str
    day_of_week: str
    lesson_time: str
    room: str


class CanteenIn(BaseModel):
    date: str
    class_name: str
    students_count: int
    notes: Optional[str] = ""


class VoiceTextIn(BaseModel):
    text: str


class SimplifyIn(BaseModel):
    text: str
    mode: str = "simplify"


class GenerateScheduleIn(BaseModel):
    classes: list[dict]
    rooms: list[str] = []
    days: Optional[list[str]] = None
    times: Optional[list[str]] = None
    replace: bool = False


class SubstituteIn(BaseModel):
    date: str
    teacher_id: int
    reason: Optional[str] = "Болезнь"


# ---------- Auth ----------
@api.post("/auth/login")
async def login(data: LoginInput):
    user = auth.get_user_by_email(data.email)
    if not user or not auth.verify_password(data.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Неверная почта или пароль")
    token = auth.create_access_token(user["id"], user["email"], user.get("user_role") or "teacher")
    u = {k: v for k, v in user.items() if k != "password_hash"}
    return {"access_token": token, "token_type": "bearer", "user": u}


@api.get("/auth/me")
async def me(user: dict = Depends(auth.get_current_user)):
    return user


# ---------- Dashboard ----------
@api.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(auth.get_current_user)):
    today = date.today().isoformat()
    employees = db.query_one("SELECT COUNT(*) c FROM employees")["c"]
    incidents_open = db.query_one(
        "SELECT COUNT(*) c FROM incidents WHERE status IN ('new','in_progress')"
    )["c"]
    tasks_open = db.query_one(
        "SELECT COUNT(*) c FROM tasks WHERE status IN ('new','in_progress')"
    )["c"]
    canteen_today = db.query_one(
        "SELECT COALESCE(SUM(students_count),0) c FROM canteen WHERE date = ?",
        (today,),
    )["c"]
    substitutions_today = db.query_one(
        "SELECT COUNT(*) c FROM substitutions WHERE date = ?",
        (today,),
    )["c"]
    messages_week = db.query_one(
        "SELECT COUNT(*) c FROM messages WHERE created_at >= datetime('now','-7 days')"
    )["c"]
    incidents_recent = db.query(
        "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 6"
    )
    return {
        "employees": employees,
        "incidents_open": incidents_open,
        "tasks_open": tasks_open,
        "canteen_today": canteen_today,
        "substitutions_today": substitutions_today,
        "messages_week": messages_week,
        "incidents_recent": incidents_recent,
    }


@api.get("/dashboard/heatmap")
async def heatmap(user: dict = Depends(auth.get_current_user)):
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    teachers = db.query(
        "SELECT id, full_name, role, subject FROM employees "
        "WHERE user_role != 'director' OR user_role IS NULL "
        "ORDER BY full_name LIMIT 20"
    )
    schedule_rows = db.query("SELECT teacher_id, day_of_week FROM schedule")
    load: dict[int, dict[str, int]] = {}
    for r in schedule_rows:
        load.setdefault(r["teacher_id"], {d: 0 for d in days})
        if r["day_of_week"] in load[r["teacher_id"]]:
            load[r["teacher_id"]][r["day_of_week"]] += 1
    data = []
    for t in teachers:
        row = {"teacher_id": t["id"], "full_name": t["full_name"], "subject": t["subject"]}
        for d in days:
            row[d] = (load.get(t["id"], {}) or {}).get(d, 0)
        data.append(row)
    return {"days": days, "rows": data}


# ---------- Employees ----------
@api.get("/employees")
async def list_employees(user: dict = Depends(auth.get_current_user)):
    rows = db.query(
        "SELECT e.id, e.full_name, e.role, e.subject, e.phone, e.qualification, "
        "e.email, e.user_role, t.telegram_id FROM employees e "
        "LEFT JOIN telegram_links t ON t.employee_id = e.id ORDER BY e.id"
    )
    return rows


@api.post("/employees")
async def create_employee(data: EmployeeIn, user: dict = Depends(auth.require_director)):
    pwd_hash = auth.hash_password("teacher123")
    new_id = db.execute(
        "INSERT INTO employees (full_name, role, subject, phone, qualification, email, password_hash, user_role) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            data.full_name,
            data.role,
            data.subject,
            data.phone,
            data.qualification,
            data.email or f"teacher_new_{datetime.now().timestamp():.0f}@aqbobek.kz",
            pwd_hash,
            data.user_role or "teacher",
        ),
    )
    return db.query_one("SELECT * FROM employees WHERE id = ?", (new_id,))


@api.put("/employees/{emp_id}")
async def update_employee(emp_id: int, data: EmployeeIn, user: dict = Depends(auth.require_director)):
    db.execute(
        "UPDATE employees SET full_name=?, role=?, subject=?, phone=?, qualification=?, email=COALESCE(?, email), user_role=? WHERE id=?",
        (data.full_name, data.role, data.subject, data.phone, data.qualification, data.email, data.user_role, emp_id),
    )
    return db.query_one("SELECT * FROM employees WHERE id = ?", (emp_id,))


@api.delete("/employees/{emp_id}")
async def delete_employee(emp_id: int, user: dict = Depends(auth.require_director)):
    db.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    return {"ok": True}


# ---------- Incidents ----------
@api.get("/incidents")
async def list_incidents(user: dict = Depends(auth.get_current_user)):
    rows = db.query(
        "SELECT i.*, e.full_name as assignee_name FROM incidents i "
        "LEFT JOIN employees e ON e.id = i.assigned_to ORDER BY i.created_at DESC"
    )
    return rows


@api.post("/incidents")
async def create_incident(data: IncidentIn, user: dict = Depends(auth.get_current_user)):
    new_id = db.execute(
        "INSERT INTO incidents (created_by, assigned_to, title, description, priority) VALUES (?,?,?,?,?)",
        (user["id"], data.assigned_to, data.title, data.description, data.priority),
    )
    return db.query_one("SELECT * FROM incidents WHERE id=?", (new_id,))


@api.patch("/incidents/{iid}/status")
async def incident_status(iid: int, data: StatusIn, user: dict = Depends(auth.get_current_user)):
    db.execute("UPDATE incidents SET status=? WHERE id=?", (data.status, iid))
    return db.query_one("SELECT * FROM incidents WHERE id=?", (iid,))


@api.patch("/incidents/{iid}/assign")
async def incident_assign(iid: int, payload: dict, user: dict = Depends(auth.require_director)):
    db.execute("UPDATE incidents SET assigned_to=? WHERE id=?", (payload.get("assigned_to"), iid))
    return db.query_one("SELECT * FROM incidents WHERE id=?", (iid,))


# ---------- Tasks ----------
@api.get("/tasks")
async def list_tasks(
    user: dict = Depends(auth.get_current_user),
    mine: bool = False,
):
    if mine or (user.get("user_role") or "").lower() != "director":
        rows = db.query(
            "SELECT t.*, e.full_name as assignee_name, c.full_name as creator_name "
            "FROM tasks t "
            "LEFT JOIN employees e ON e.id = t.assigned_to "
            "LEFT JOIN employees c ON c.id = t.created_by "
            "WHERE t.assigned_to = ? ORDER BY t.created_at DESC",
            (user["id"],),
        )
    else:
        rows = db.query(
            "SELECT t.*, e.full_name as assignee_name, c.full_name as creator_name "
            "FROM tasks t "
            "LEFT JOIN employees e ON e.id = t.assigned_to "
            "LEFT JOIN employees c ON c.id = t.created_by "
            "ORDER BY t.created_at DESC"
        )
    return rows


@api.post("/tasks")
async def create_task(data: TaskIn, user: dict = Depends(auth.get_current_user)):
    new_id = db.execute(
        "INSERT INTO tasks (created_by, assigned_to, title, description, priority, due_date, source_type) "
        "VALUES (?,?,?,?,?,?, 'dashboard')",
        (user["id"], data.assigned_to, data.title, data.description, data.priority, data.due_date),
    )
    return db.query_one("SELECT * FROM tasks WHERE id=?", (new_id,))


@api.patch("/tasks/{tid}/status")
async def task_status(tid: int, data: StatusIn, user: dict = Depends(auth.get_current_user)):
    db.execute("UPDATE tasks SET status=? WHERE id=?", (data.status, tid))
    return db.query_one("SELECT * FROM tasks WHERE id=?", (tid,))


# ---------- Canteen ----------
@api.get("/canteen")
async def canteen_list(date_from: Optional[str] = None, date_to: Optional[str] = None, user: dict = Depends(auth.get_current_user)):
    if date_from and date_to:
        rows = db.query(
            "SELECT * FROM canteen WHERE date BETWEEN ? AND ? ORDER BY date DESC, class_name",
            (date_from, date_to),
        )
    else:
        rows = db.query("SELECT * FROM canteen ORDER BY date DESC, class_name LIMIT 200")
    return rows


@api.get("/canteen/summary")
async def canteen_summary(user: dict = Depends(auth.get_current_user)):
    today = date.today().isoformat()
    today_rows = db.query(
        "SELECT class_name, SUM(students_count) as students, SUM(meals_count) as meals "
        "FROM canteen WHERE date = ? GROUP BY class_name",
        (today,),
    )
    week = db.query(
        "SELECT date, SUM(students_count) as total FROM canteen "
        "WHERE date >= date('now','-14 days') GROUP BY date ORDER BY date"
    )
    return {"today": today_rows, "by_day": week}


@api.post("/canteen")
async def canteen_create(data: CanteenIn, user: dict = Depends(auth.get_current_user)):
    new_id = db.execute(
        "INSERT INTO canteen (date, class_name, students_count, meals_count, notes) VALUES (?,?,?,?,?)",
        (data.date, data.class_name, data.students_count, data.students_count, data.notes),
    )
    return db.query_one("SELECT * FROM canteen WHERE id=?", (new_id,))


# ---------- Schedule ----------
@api.get("/schedule")
async def schedule_list(
    teacher_id: Optional[int] = None,
    class_name: Optional[str] = None,
    room: Optional[str] = None,
    user: dict = Depends(auth.get_current_user),
):
    where = []
    params: list[Any] = []
    if teacher_id:
        where.append("s.teacher_id = ?")
        params.append(teacher_id)
    if class_name:
        where.append("s.class_name = ?")
        params.append(class_name)
    if room:
        where.append("s.room = ?")
        params.append(room)
    sql = (
        "SELECT s.*, e.full_name as teacher_name, e.subject as teacher_subject "
        "FROM schedule s LEFT JOIN employees e ON e.id = s.teacher_id"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.day_of_week, s.lesson_time"
    return db.query(sql, params)


@api.post("/schedule")
async def schedule_create(data: ScheduleIn, user: dict = Depends(auth.require_director)):
    # conflict check
    conflict = db.query_one(
        "SELECT * FROM schedule WHERE day_of_week=? AND lesson_time=? AND (teacher_id=? OR room=?)",
        (data.day_of_week, data.lesson_time, data.teacher_id, data.room),
    )
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Конфликт: учитель или кабинет уже заняты в {data.day_of_week} {data.lesson_time}",
        )
    new_id = db.execute(
        "INSERT INTO schedule (teacher_id, class_name, day_of_week, lesson_time, room) VALUES (?,?,?,?,?)",
        (data.teacher_id, data.class_name, data.day_of_week, data.lesson_time, data.room),
    )
    return db.query_one("SELECT * FROM schedule WHERE id=?", (new_id,))


@api.delete("/schedule/{sid}")
async def schedule_delete(sid: int, user: dict = Depends(auth.require_director)):
    db.execute("DELETE FROM schedule WHERE id=?", (sid,))
    return {"ok": True}


@api.put("/schedule/{sid}")
async def schedule_update(sid: int, data: ScheduleIn, user: dict = Depends(auth.require_director)):
    db.execute(
        "UPDATE schedule SET teacher_id=?, class_name=?, day_of_week=?, lesson_time=?, room=? WHERE id=?",
        (data.teacher_id, data.class_name, data.day_of_week, data.lesson_time, data.room, sid),
    )
    return db.query_one("SELECT * FROM schedule WHERE id=?", (sid,))


# ---------- AI: Generate schedule ----------
@api.post("/ai/schedule/generate")
async def ai_generate_schedule(data: GenerateScheduleIn, user: dict = Depends(auth.require_director)):
    teachers = db.query("SELECT id, full_name, subject, role FROM employees WHERE role='Учитель'")
    result = schedule_gen.generate_schedule(
        classes=data.classes,
        teachers=teachers,
        rooms=data.rooms or ["101", "102", "103", "104", "105", "Спортзал", "Лингафон"],
        days=data.days,
        times=data.times,
    )
    if data.replace:
        db.execute("DELETE FROM schedule", ())
        for s in result["schedule"]:
            db.execute(
                "INSERT INTO schedule (teacher_id, class_name, day_of_week, lesson_time, room) VALUES (?,?,?,?,?)",
                (s["teacher_id"], s["class_name"], s["day_of_week"], s["lesson_time"], s["room"]),
            )
    return result


# ---------- AI: Substitution ----------
@api.post("/ai/substitute")
async def ai_substitute(data: SubstituteIn, user: dict = Depends(auth.require_director)):
    absent = db.query_one("SELECT id, full_name, subject, role FROM employees WHERE id=?", (data.teacher_id,))
    if not absent:
        raise HTTPException(status_code=404, detail="Учитель не найден")
    lessons = db.query("SELECT * FROM schedule WHERE teacher_id=?", (data.teacher_id,))
    all_schedule = db.query("SELECT teacher_id, day_of_week, lesson_time FROM schedule")
    all_teachers = db.query(
        "SELECT id, full_name, subject, role FROM employees WHERE role='Учитель' AND id != ?",
        (data.teacher_id,),
    )
    suggestions = []
    for lesson in lessons:
        cands = schedule_gen.find_substitute_candidates(absent, lesson, all_teachers, all_schedule)[:5]
        pick = cands[0] if cands else None
        if pick:
            # Save substitution as pending
            db.execute(
                "INSERT INTO substitutions (date, original_teacher_id, substitute_teacher_id, class_name, lesson_time, reason, status) "
                "VALUES (?,?,?,?,?,?,'pending')",
                (data.date, data.teacher_id, pick["id"], lesson["class_name"], lesson["lesson_time"], data.reason),
            )
        suggestions.append({
            "lesson": lesson,
            "candidates": cands,
            "picked": pick,
        })
    return {
        "absent_teacher": absent,
        "date": data.date,
        "lessons": lessons,
        "suggestions": suggestions,
    }


@api.get("/substitutions")
async def list_substitutions(user: dict = Depends(auth.get_current_user)):
    rows = db.query(
        "SELECT s.*, eo.full_name as original_name, es.full_name as substitute_name "
        "FROM substitutions s "
        "LEFT JOIN employees eo ON eo.id = s.original_teacher_id "
        "LEFT JOIN employees es ON es.id = s.substitute_teacher_id "
        "ORDER BY s.created_at DESC LIMIT 50"
    )
    return rows


# ---------- AI: Voice to tasks ----------
@api.post("/ai/voice/transcribe")
async def ai_voice_transcribe(
    file: UploadFile = File(...),
    user: dict = Depends(auth.get_current_user),
):
    content = await file.read()
    text = await ai.transcribe_audio(content, filename=file.filename or "voice.webm")
    return {"text": text}


@api.post("/ai/voice/parse")
async def ai_voice_parse(data: VoiceTextIn, user: dict = Depends(auth.require_director)):
    employees = db.query("SELECT id, full_name, role FROM employees")
    tasks = await ai.parse_voice_to_tasks(data.text, employees)
    # Auto-create tasks
    created = []
    for t in tasks:
        new_id = db.execute(
            "INSERT INTO tasks (created_by, assigned_to, title, description, priority, due_date, source_type) "
            "VALUES (?,?,?,?,?,?, 'voice')",
            (
                user["id"],
                t.get("assigned_to_id"),
                t.get("title", "Задача"),
                t.get("description", ""),
                t.get("priority", "medium"),
                t.get("due_date"),
            ),
        )
        created.append(db.query_one("SELECT * FROM tasks WHERE id=?", (new_id,)))
    return {"parsed": tasks, "created": created}


# ---------- AI: Simplify / generate orders (RAG-lite) ----------
@api.post("/ai/orders/simplify")
async def ai_simplify(data: SimplifyIn, user: dict = Depends(auth.get_current_user)):
    out = await ai.simplify_order(data.text, data.mode)
    return {"result": out}


# ---------- Classes ----------
@api.get("/classes")
async def list_classes(user: dict = Depends(auth.get_current_user)):
    rows = db.query("SELECT DISTINCT class_name FROM schedule WHERE class_name != '' ORDER BY class_name")
    if not rows:
        return [{"class_name": c} for c in ["1А", "1Б", "2А", "2Б", "3А", "3Б", "3В", "4А", "4Б"]]
    return rows


# ---------- Messages feed (from bot) ----------
@api.get("/messages")
async def messages_feed(limit: int = 50, user: dict = Depends(auth.require_director)):
    return db.query("SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,))


# Mount router & CORS
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"name": "Aqbobek ACS API", "version": "1.0"}
