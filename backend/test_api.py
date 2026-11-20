"""Manual/integration checks for NutriRAG API logic."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.ai_service import generate_answer, generate_meal_plan
from backend.rag import get_retriever


def main() -> None:
    retriever = get_retriever()
    print(f"Indexed foods={len(retriever.foods)} notes={len(retriever.notes)}")

    hits = retriever.retrieve("protein in soya chunks", top_k=3)
    print("RAG hits:", [h["title"] for h in hits])

    ans = generate_answer("How much protein is present in 100 grams of soya chunks?")
    print("Answer preview:", ans["answer"][:200].replace("\n", " "))
    print("Sources:", [s["title"] for s in ans["sources"]])

    unsafe = generate_answer("Diagnose my diabetes and recommend medicine.")
    print("Unsafe refused:", unsafe["refused"], "|", unsafe["answer"][:120])

    profile = {
        "id": "default",
        "age": 25,
        "goal": "Muscle gain",
        "diet_type": "Vegetarian",
        "allergies": ["Peanuts"],
        "daily_budget": 250,
    }
    plan = generate_meal_plan(profile)
    foods_used = []
    for meal in plan.get("meals") or []:
        for item in meal.get("items") or []:
            foods_used.append(item.get("food", ""))
    print("Meal feasible:", plan.get("feasible"))
    print("Meals:", len(plan.get("meals") or []))
    print("Contains peanut?:", any("peanut" in f.lower() for f in foods_used))
    print("Totals:", plan.get("totals"))


if __name__ == "__main__":
    main()
