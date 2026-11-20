"""Supabase client and data helpers for NutriRAG."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

_supabase = None
_init_error: str | None = None


def get_supabase():
    """Lazy-create Supabase client. Returns None if credentials missing."""
    global _supabase, _init_error
    if _supabase is not None:
        return _supabase
    if _init_error:
        return None

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        _init_error = "Supabase credentials missing"
        return None

    try:
        from supabase import create_client

        _supabase = create_client(url, key)
        return _supabase
    except Exception as exc:  # noqa: BLE001
        _init_error = str(exc)
        return None


def get_food_nutrients(food_name: str) -> list[dict[str, Any]]:
    """Legacy name-based lookup (kept for compatibility)."""
    client = get_supabase()
    if not client:
        return []
    try:
        response = (
            client.table("foods")
            .select("*")
            .ilike("food_name", f"%{food_name}%")
            .execute()
        )
        return response.data or []
    except Exception:
        # Fallback to older table name if present
        try:
            response = (
                client.table("food_nutrients")
                .select("*")
                .ilike("food_name", f"%{food_name}%")
                .execute()
            )
            return response.data or []
        except Exception:
            return []


def fetch_all_foods() -> list[dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    try:
        response = client.table("foods").select("*").execute()
        return response.data or []
    except Exception:
        try:
            response = client.table("food_nutrients").select("*").execute()
            return response.data or []
        except Exception:
            return []


def fetch_all_notes() -> list[dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    try:
        response = client.table("nutrition_notes").select("*").execute()
        return response.data or []
    except Exception:
        return []


def upsert_foods(rows: list[dict[str, Any]]) -> int:
    client = get_supabase()
    if not client or not rows:
        return 0
    response = client.table("foods").upsert(rows, on_conflict="food_name").execute()
    return len(response.data or [])


def upsert_notes(rows: list[dict[str, Any]]) -> int:
    client = get_supabase()
    if not client or not rows:
        return 0
    # No unique topic constraint guaranteed — insert and ignore duplicates by clearing first in seed
    response = client.table("nutrition_notes").insert(rows).execute()
    return len(response.data or [])


def clear_notes() -> None:
    client = get_supabase()
    if not client:
        return
    try:
        client.table("nutrition_notes").delete().neq("id", 0).execute()
    except Exception:
        pass


def save_profile(profile: dict[str, Any]) -> dict[str, Any]:
    client = get_supabase()
    if not client:
        raise RuntimeError("Supabase unavailable")
    response = client.table("profiles").upsert(profile, on_conflict="id").execute()
    data = response.data or []
    return data[0] if data else profile


def get_profile(user_id: str = "default") -> dict[str, Any] | None:
    client = get_supabase()
    if not client:
        return None
    try:
        response = client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None
    except Exception:
        return None
