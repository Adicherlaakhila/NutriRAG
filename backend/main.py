"""FastAPI backend for NutriRAG."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

from backend.ai_service import generate_answer, generate_meal_plan
from backend.prompt import DISCLAIMER
from backend.rag import get_retriever, reload_retriever

app = FastAPI(title="NutriRAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_GOALS = {
    "Weight loss",
    "Weight gain",
    "Muscle gain",
    "Maintain weight",
    "General healthy eating",
}
VALID_DIETS = {"Vegetarian", "Vegan", "Eggetarian", "Non-vegetarian"}
VALID_ALLERGIES = {"Peanuts", "Milk", "Soy", "Gluten", "Eggs", "Other"}


class ProfileRequest(BaseModel):
    id: str = "default"
    age: int
    goal: str
    diet_type: str
    allergies: list[str] = Field(default_factory=list)
    daily_budget: float

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("Age must be between 1 and 120.")
        return v

    @field_validator("daily_budget")
    @classmethod
    def validate_budget(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Daily budget cannot be negative.")
        return v

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        if v not in VALID_GOALS:
            raise ValueError(f"Invalid goal. Choose from: {', '.join(sorted(VALID_GOALS))}")
        return v

    @field_validator("diet_type")
    @classmethod
    def validate_diet(cls, v: str) -> str:
        if v not in VALID_DIETS:
            raise ValueError(f"Invalid diet type. Choose from: {', '.join(sorted(VALID_DIETS))}")
        return v

    @field_validator("allergies")
    @classmethod
    def validate_allergies(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            if item not in VALID_ALLERGIES:
                raise ValueError(f"Invalid allergy: {item}")
            cleaned.append(item)
        return cleaned


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    user_id: str = "default"
    history: list[ChatMessage] = Field(default_factory=list)
    food_name: str | None = None  # legacy optional field


class MealPlanRequest(BaseModel):
    user_id: str = "default"
    profile: ProfileRequest | None = None


# In-memory profile fallback when Supabase is unavailable
_PROFILE_STORE: dict[str, dict[str, Any]] = {}


def _load_profile(user_id: str) -> dict[str, Any] | None:
    if user_id in _PROFILE_STORE:
        return _PROFILE_STORE[user_id]
    try:
        from database.supabase_client import get_profile

        row = get_profile(user_id)
        if row:
            _PROFILE_STORE[user_id] = row
            return row
    except Exception:
        pass
    return None


def _save_profile(data: dict[str, Any]) -> dict[str, Any]:
    _PROFILE_STORE[data["id"]] = data
    try:
        from database.supabase_client import save_profile

        return save_profile(data)
    except Exception:
        return data


@app.on_event("startup")
def startup() -> None:
    get_retriever()


@app.get("/")
def home():
    return {"message": "NutriRAG API is running!", "disclaimer": DISCLAIMER}


@app.get("/health")
def health():
    retriever = get_retriever()
    llm_ok = bool(os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY"))
    provider = None
    try:
        from backend.ai_service import llm_provider

        provider = llm_provider() if llm_ok else None
    except Exception:
        provider = None
    supabase_ok = False
    try:
        from database.supabase_client import get_supabase

        supabase_ok = get_supabase() is not None
    except Exception:
        supabase_ok = False
    return {
        "status": "ok",
        "foods_indexed": len(retriever.foods),
        "notes_indexed": len(retriever.notes),
        "llm_configured": llm_ok,
        "llm_provider": provider,
        "supabase_configured": supabase_ok,
    }


@app.post("/profile")
def create_profile(request: ProfileRequest):
    payload = request.model_dump()
    saved = _save_profile(payload)
    return {"ok": True, "profile": saved}


@app.get("/profile")
def read_profile(user_id: str = Query(default="default")):
    profile = _load_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please save your profile first.")
    return {"profile": profile}


@app.post("/chat")
def chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if request.food_name:
        question = f"{question} (related food: {request.food_name})"

    profile = _load_profile(request.user_id)
    history = [m.model_dump() for m in request.history][-8:]
    result = generate_answer(question, profile=profile, history=history)
    return result


@app.post("/meal-plan")
def meal_plan(request: MealPlanRequest):
    if request.profile is not None:
        profile = request.profile.model_dump()
        _save_profile(profile)
    else:
        profile = _load_profile(request.user_id)
        if not profile:
            raise HTTPException(
                status_code=400,
                detail="No profile found. Save your profile before generating a meal plan.",
            )
    plan = generate_meal_plan(profile)
    return plan


@app.get("/foods")
def list_foods(q: str | None = None):
    retriever = get_retriever()
    foods = retriever.get_foods(query=q)
    return {"count": len(foods), "foods": foods}


@app.post("/reload-index")
def reload_index():
    retriever = reload_retriever()
    return {
        "ok": True,
        "foods_indexed": len(retriever.foods),
        "notes_indexed": len(retriever.notes),
    }
