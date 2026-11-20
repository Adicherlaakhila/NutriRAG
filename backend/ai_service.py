"""Groq LLM + RAG orchestration for NutriRAG."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.prompt import (
    MEDICAL_REFUSAL,
    build_chat_messages,
    build_meal_plan_messages,
    format_sources,
    is_unsafe_medical_query,
)
from backend.rag import get_retriever

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _api_key() -> str:
    key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if not key:
        raise ValueError("GROQ_API_KEY (or OPENAI_API_KEY fallback) not found in environment.")
    return key


def llm_provider() -> str:
    key = _api_key()
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("sk-"):
        return "openai"
    # Default to Groq for assignment-compatible keys
    return "groq"


def _chat_completion(messages: list[dict[str, str]], temperature: float = 0.3) -> str:
    key = _api_key()
    provider = llm_provider()

    if provider == "groq":
        from groq import Groq

        client = Groq(api_key=key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    # OpenAI-compatible fallback when an sk- key is stored in GROQ_API_KEY
    from openai import OpenAI

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


def generate_answer(
    question: str,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """RAG chat answer with sources and safety refusal."""
    if is_unsafe_medical_query(question):
        return {
            "answer": MEDICAL_REFUSAL,
            "sources": [],
            "refused": True,
        }

    retriever = get_retriever()
    retrieved = retriever.retrieve(question, top_k=4)

    if not retrieved:
        return {
            "answer": (
                "The knowledge base does not contain sufficient information to answer "
                "this question reliably. Please try asking about foods or nutrition topics "
                "listed in the Food Knowledge Base."
            ),
            "sources": [],
            "refused": False,
        }

    messages = build_chat_messages(question, profile, retrieved, history)
    try:
        answer = _chat_completion(messages)
    except Exception as exc:  # noqa: BLE001
        return {
            "answer": (
                "Sorry, I could not reach the AI service right now. "
                f"Please try again shortly. ({type(exc).__name__})"
            ),
            "sources": format_sources(retrieved),
            "refused": False,
        }

    return {
        "answer": answer,
        "sources": format_sources(retrieved),
        "refused": False,
    }


def _goal_targets(profile: dict[str, Any]) -> dict[str, float]:
    goal = str(profile.get("goal", "")).lower()
    age = int(profile.get("age") or 25)
    # Simple educational defaults (not medical RDAs)
    base_cal = 2000 if age >= 18 else 1800
    if "loss" in goal:
        return {"calories": base_cal - 300, "protein": 70}
    if "muscle" in goal:
        return {"calories": base_cal + 250, "protein": 100}
    if "gain" in goal:
        return {"calories": base_cal + 300, "protein": 80}
    return {"calories": float(base_cal), "protein": 60}


def _deterministic_meal_plan(
    profile: dict[str, Any],
    foods: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rule-based planner used as primary or fallback."""
    budget = float(profile.get("daily_budget") or 0)
    targets = _goal_targets(profile)

    if budget < 40:
        return {
            "feasible": False,
            "limitation": (
                f"A daily food budget of Rs {budget:.0f} is too low to build a "
                "nutritionally reasonable one-day plan with the foods in our knowledge base. "
                "Please increase the budget (often Rs 120+ helps for a basic balanced day) "
                "or consult a dietitian for constrained budgets."
            ),
            "meals": [],
            "totals": {"calories": 0, "protein": 0, "cost": 0},
            "notes": "Budget limitation — no unrealistic plan generated.",
        }

    # Prefer higher protein foods for muscle/gain goals
    ranked = sorted(foods, key=lambda f: (float(f["protein"]), -float(f["estimated_cost"])), reverse=True)
    if not ranked:
        return {
            "feasible": False,
            "limitation": "No foods remain after applying diet and allergy filters.",
            "meals": [],
            "totals": {"calories": 0, "protein": 0, "cost": 0},
            "notes": "",
        }

    def pick(*names: str) -> dict[str, Any] | None:
        lower_names = [n.lower() for n in names]
        for food in ranked:
            fname = food["food_name"].lower()
            if any(n in fname or fname in n for n in lower_names):
                return food
        return None

    templates = [
        ("Breakfast", ["Oats", "Banana", "Milk", "Curd", "Idli", "Poha"]),
        ("Morning snack", ["Peanuts", "Apple", "Cucumber", "Moong sprouts", "Banana"]),
        ("Lunch", ["Cooked rice", "Dal", "Rajma", "Chickpeas", "Mixed vegetables", "Roti", "Curd"]),
        ("Evening snack", ["Soya chunks", "Curd", "Besan", "Peanuts", "Banana"]),
        ("Dinner", ["Roti", "Paneer", "Dal", "Mixed vegetables", "Chicken", "Fish", "Tofu", "Spinach"]),
    ]

    meals = []
    total_cal = total_pro = total_cost = 0.0
    used: set[str] = set()

    for meal_name, preferences in templates:
        items = []
        meal_cal = meal_pro = meal_cost = 0.0
        for pref in preferences:
            food = pick(pref)
            if not food:
                continue
            key = food["food_name"]
            if key in used and len(items) > 0:
                continue
            # Skip peanut snack preference if somehow present
            items.append(
                {
                    "food": food["food_name"],
                    "serving": food["serving_size"],
                    "calories": round(float(food["calories"]), 1),
                    "protein": round(float(food["protein"]), 1),
                    "cost": round(float(food["estimated_cost"]), 1),
                }
            )
            meal_cal += float(food["calories"])
            meal_pro += float(food["protein"])
            meal_cost += float(food["estimated_cost"])
            used.add(key)
            if len(items) >= 2:
                break
        if not items:
            food = ranked[0]
            items.append(
                {
                    "food": food["food_name"],
                    "serving": food["serving_size"],
                    "calories": round(float(food["calories"]), 1),
                    "protein": round(float(food["protein"]), 1),
                    "cost": round(float(food["estimated_cost"]), 1),
                }
            )
            meal_cal = float(food["calories"])
            meal_pro = float(food["protein"])
            meal_cost = float(food["estimated_cost"])

        meals.append(
            {
                "name": meal_name,
                "items": items,
                "calories": round(meal_cal, 1),
                "protein": round(meal_pro, 1),
                "cost": round(meal_cost, 1),
            }
        )
        total_cal += meal_cal
        total_pro += meal_pro
        total_cost += meal_cost

    if total_cost > budget * 1.15:
        return {
            "feasible": False,
            "limitation": (
                f"Estimated minimum reasonable plan cost is about Rs {total_cost:.0f}, "
                f"which exceeds your daily budget of Rs {budget:.0f}. "
                "Increase the budget slightly or simplify goals; we will not invent an unrealistic underfunded plan."
            ),
            "meals": meals,
            "totals": {
                "calories": round(total_cal, 1),
                "protein": round(total_pro, 1),
                "cost": round(total_cost, 1),
            },
            "notes": "Showing a reference plan that exceeds budget for transparency.",
        }

    return {
        "feasible": True,
        "limitation": None,
        "meals": meals,
        "totals": {
            "calories": round(total_cal, 1),
            "protein": round(total_pro, 1),
            "cost": round(total_cost, 1),
        },
        "notes": (
            f"Approximate educational plan toward ~{targets['calories']:.0f} kcal and "
            f"~{targets['protein']:.0f} g protein. Actual values vary by preparation and portion size."
        ),
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def generate_meal_plan(profile: dict[str, Any]) -> dict[str, Any]:
    retriever = get_retriever()
    allergies = profile.get("allergies") or []
    if isinstance(allergies, str):
        allergies = [allergies]
    foods = retriever.get_foods(diet_type=profile.get("diet_type"), allergies=allergies)

    # Always compute deterministic plan for reliability / allergy safety
    plan = _deterministic_meal_plan(profile, foods)

    # Optionally enrich notes via Groq (non-fatal)
    try:
        messages = build_meal_plan_messages(profile, foods[:25])
        raw = _chat_completion(messages, temperature=0.2)
        llm_plan = _extract_json(raw)
        if llm_plan and llm_plan.get("meals") and llm_plan.get("feasible") is not False:
            # Validate no allergy foods slipped in
            allergy_set = {a.lower() for a in allergies if a and a.lower() != "other"}
            bad = False
            for meal in llm_plan.get("meals", []):
                for item in meal.get("items", []):
                    name = str(item.get("food", "")).lower()
                    if any(a in name for a in allergy_set):
                        bad = True
                        break
            if not bad:
                # Prefer LLM plan only if cost within budget or same feasibility
                totals = llm_plan.get("totals") or {}
                cost = float(totals.get("cost") or 0)
                budget = float(profile.get("daily_budget") or 0)
                if budget <= 0 or cost <= budget * 1.15:
                    llm_plan.setdefault(
                        "notes",
                        "Approximate values; actual values vary by preparation and portion size.",
                    )
                    return llm_plan
    except Exception:
        pass

    return plan


# Backwards-compatible wrapper used by older test script
def generate_answer_legacy(question: str, food_name: str | None = None) -> str:
    q = question
    if food_name:
        q = f"{question} (food focus: {food_name})"
    result = generate_answer(q)
    return result["answer"]
