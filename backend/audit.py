"""Audit log helper (append-only)."""
from __future__ import annotations
import json
from db import execute, query


def log(actor: dict | None, entity: str, action: str, entity_id: int | None = None, payload: dict | None = None):
    execute(
        "INSERT INTO audit_log (actor_id, actor_name, entity, entity_id, action, payload) VALUES (?,?,?,?,?,?)",
        (
            (actor or {}).get("id"),
            (actor or {}).get("full_name", "system"),
            entity,
            entity_id,
            action,
            json.dumps(payload or {}, ensure_ascii=False),
        ),
    )


def recent(limit: int = 100, entity: str | None = None) -> list[dict]:
    if entity:
        return query(
            "SELECT * FROM audit_log WHERE entity = ? ORDER BY created_at DESC LIMIT ?",
            (entity, limit),
        )
    return query("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,))
