"""JWT + bcrypt authentication helpers for Aqbobek ACS."""
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from db import query, query_one, execute

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MIN = 60 * 24  # 1 day


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MIN),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])


def get_user_by_email(email: str) -> Optional[dict]:
    return query_one(
        "SELECT id, full_name, role, subject, email, password_hash, user_role, phone "
        "FROM employees WHERE LOWER(email) = LOWER(?)",
        (email,),
    )


def get_user_by_id(user_id: int) -> Optional[dict]:
    return query_one(
        "SELECT id, full_name, role, subject, email, user_role, phone "
        "FROM employees WHERE id = ?",
        (user_id,),
    )


def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = None
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Сессия истекла")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Неверный токен")

    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


def require_director(user: dict = Depends(get_current_user)) -> dict:
    if (user.get("user_role") or "").lower() != "director":
        raise HTTPException(status_code=403, detail="Доступ только для директора")
    return user


def seed_admin_and_teachers() -> None:
    """Seed director account and ensure each teacher has a default login."""
    admin_email = os.environ.get("ADMIN_EMAIL", "director@aqbobek.kz").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "director123")

    # 1. Ensure director exists.
    existing = query_one(
        "SELECT id, password_hash FROM employees WHERE LOWER(email) = ?",
        (admin_email,),
    )
    if not existing:
        # Is there an employee with role Директор already?
        director_row = query_one(
            "SELECT id FROM employees WHERE role = 'Директор' LIMIT 1"
        )
        if director_row:
            execute(
                "UPDATE employees SET email = ?, password_hash = ?, user_role = 'director' "
                "WHERE id = ?",
                (admin_email, hash_password(admin_password), director_row["id"]),
            )
        else:
            execute(
                "INSERT INTO employees (full_name, role, subject, email, password_hash, user_role) "
                "VALUES (?, 'Директор', 'Администрация', ?, ?, 'director')",
                ("Директор школы", admin_email, hash_password(admin_password)),
            )
    else:
        # Rotate password if it changed in env.
        if not verify_password(admin_password, existing.get("password_hash") or ""):
            execute(
                "UPDATE employees SET password_hash = ?, user_role = 'director' WHERE id = ?",
                (hash_password(admin_password), existing["id"]),
            )

    # 2. Ensure every teacher/staff has a login (email = id@aqbobek.kz, password = teacher123).
    default_pwd = "teacher123"
    rows = query_one("SELECT COUNT(*) as c FROM employees WHERE email IS NULL OR email = ''")
    if rows and rows["c"] > 0:
        teachers = query(
            "SELECT id, full_name, role FROM employees WHERE email IS NULL OR email = ''"
        )
        for t in teachers:
            email = f"teacher{t['id']}@aqbobek.kz"
            role = (t.get("role") or "").lower()
            user_role = "director" if "директор" in role else "teacher"
            execute(
                "UPDATE employees SET email = ?, password_hash = ?, user_role = COALESCE(user_role, ?) "
                "WHERE id = ?",
                (email, hash_password(default_pwd), user_role, t["id"]),
            )
