"""SQLite database layer shared with the Telegram bot."""
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

DB_PATH = os.environ.get("SCHOOL_DB_PATH", "/app/data/school.db")


def _ensure_db_dir() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        conn.commit()
        return cur.lastrowid


def executescript(script: str) -> None:
    with get_conn() as conn:
        conn.executescript(script)
        conn.commit()


def column_exists(table: str, column: str) -> bool:
    rows = query(f"PRAGMA table_info({table})")
    return any(r["name"] == column for r in rows)


def table_exists(table: str) -> bool:
    row = query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return row is not None


def init_schema() -> None:
    """Create missing tables and add missing columns to existing ones."""
    _ensure_db_dir()
    # Base tables the bot uses – create if missing (idempotent).
    executescript(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            raw_text TEXT,
            message_type TEXT,
            parsed_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Учитель',
            subject TEXT,
            phone TEXT,
            qualification TEXT
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            lesson_time TEXT NOT NULL,
            room TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by INTEGER,
            assigned_to INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'new',
            priority TEXT DEFAULT 'medium',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by INTEGER,
            assigned_to INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'new',
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            source_type TEXT DEFAULT 'dashboard',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS canteen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            class_name TEXT NOT NULL,
            students_count INTEGER NOT NULL,
            meals_count INTEGER NOT NULL,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS telegram_links (
            telegram_id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            tg_username TEXT,
            linked_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS substitutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            original_teacher_id INTEGER NOT NULL,
            substitute_teacher_id INTEGER,
            class_name TEXT,
            lesson_time TEXT,
            day_of_week TEXT,
            room TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            rejected_candidates TEXT DEFAULT '[]',
            schedule_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            decided_at DATETIME
        );
        CREATE TABLE IF NOT EXISTS ribbons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            strategy TEXT NOT NULL DEFAULT 'split',
            parallel TEXT,
            day_of_week TEXT NOT NULL,
            lesson_time TEXT NOT NULL,
            source_classes TEXT NOT NULL DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ribbon_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ribbon_id INTEGER NOT NULL,
            group_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher_id INTEGER NOT NULL,
            room TEXT NOT NULL,
            capacity INTEGER DEFAULT 30,
            level TEXT,
            students TEXT DEFAULT '[]',
            FOREIGN KEY (ribbon_id) REFERENCES ribbons(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            actor_id INTEGER,
            actor_name TEXT,
            entity TEXT NOT NULL,
            entity_id INTEGER,
            action TEXT NOT NULL,
            payload TEXT
        );
        """
    )

    # Upgrade existing columns without breaking older DB.
    for table, col, ddl in [
        ("substitutions", "day_of_week", "ALTER TABLE substitutions ADD COLUMN day_of_week TEXT"),
        ("substitutions", "room", "ALTER TABLE substitutions ADD COLUMN room TEXT"),
        ("substitutions", "rejected_candidates", "ALTER TABLE substitutions ADD COLUMN rejected_candidates TEXT DEFAULT '[]'"),
        ("substitutions", "schedule_id", "ALTER TABLE substitutions ADD COLUMN schedule_id INTEGER"),
        ("substitutions", "decided_at", "ALTER TABLE substitutions ADD COLUMN decided_at DATETIME"),
        ("tasks", "expected_duration", "ALTER TABLE tasks ADD COLUMN expected_duration INTEGER"),
        ("tasks", "scheduled_day", "ALTER TABLE tasks ADD COLUMN scheduled_day TEXT"),
        ("tasks", "scheduled_time", "ALTER TABLE tasks ADD COLUMN scheduled_time TEXT"),
    ]:
        if not column_exists(table, col):
            executescript(ddl + ";")

    # Add auth columns to employees without breaking the bot.
    for col, ddl in [
        ("email", "ALTER TABLE employees ADD COLUMN email TEXT"),
        ("password_hash", "ALTER TABLE employees ADD COLUMN password_hash TEXT"),
        ("user_role", "ALTER TABLE employees ADD COLUMN user_role TEXT DEFAULT 'teacher'"),
    ]:
        if not column_exists("employees", col):
            executescript(ddl + ";")
