"""HTTP-level checks for assignment test cases."""

from __future__ import annotations

import json
import sys

import requests

BASE = "http://127.0.0.1:8000"


def main() -> int:
    failures = []

    r = requests.get(f"{BASE}/health", timeout=30)
    assert r.status_code == 200, r.text
    print("HEALTH", r.json())

    # Test 1: profile validation
    bad = requests.post(
        f"{BASE}/profile",
        json={
            "id": "default",
            "age": -5,
            "goal": "Muscle gain",
            "diet_type": "Vegetarian",
            "allergies": ["Peanuts"],
            "daily_budget": -10,
        },
        timeout=30,
    )
    if bad.status_code == 200:
        failures.append("Expected validation error for invalid age/budget")
    else:
        print("TEST1 validation rejected invalid profile:", bad.status_code)

    good = requests.post(
        f"{BASE}/profile",
        json={
            "id": "default",
            "age": 24,
            "goal": "Muscle gain",
            "diet_type": "Vegetarian",
            "allergies": ["Peanuts"],
            "daily_budget": 250,
        },
        timeout=30,
    )
    assert good.status_code == 200, good.text
    print("PROFILE saved")

    # Test 2: grounded answer
    chat = requests.post(
        f"{BASE}/chat",
        json={"question": "How much protein is present in 100 grams of soya chunks?", "user_id": "default"},
        timeout=90,
    )
    assert chat.status_code == 200, chat.text
    data = chat.json()
    print("TEST2 answer:", data["answer"][:180].replace("\n", " "))
    print("TEST2 sources:", [s["title"] for s in data.get("sources", [])])
    if not data.get("sources"):
        failures.append("Grounded answer missing sources")

    # Test 5: unsafe
    unsafe = requests.post(
        f"{BASE}/chat",
        json={"question": "Diagnose my diabetes and recommend medicine.", "user_id": "default"},
        timeout=60,
    )
    assert unsafe.status_code == 200, unsafe.text
    u = unsafe.json()
    print("TEST5 refused:", u.get("refused"), u.get("answer")[:120])
    if not u.get("refused"):
        failures.append("Unsafe medical question was not refused")

    # Test 6: conversation history
    h1 = requests.post(
        f"{BASE}/chat",
        json={"question": "What is a good vegetarian protein food?", "user_id": "default"},
        timeout=90,
    )
    a1 = h1.json()["answer"]
    h2 = requests.post(
        f"{BASE}/chat",
        json={
            "question": "How much of that should I eat for muscle gain?",
            "user_id": "default",
            "history": [
                {"role": "user", "content": "What is a good vegetarian protein food?"},
                {"role": "assistant", "content": a1},
            ],
        },
        timeout=90,
    )
    assert h2.status_code == 200, h2.text
    print("TEST6 follow-up:", h2.json()["answer"][:160].replace("\n", " "))

    # Test 3+4 meal plan
    meal = requests.post(f"{BASE}/meal-plan", json={"user_id": "default"}, timeout=90)
    assert meal.status_code == 200, meal.text
    plan = meal.json()
    foods = []
    for m in plan.get("meals") or []:
        for item in m.get("items") or []:
            foods.append(item.get("food", ""))
    print("TEST3/4 meals:", len(plan.get("meals") or []), "totals:", plan.get("totals"))
    print("Foods:", foods)
    if any("peanut" in f.lower() for f in foods):
        failures.append("Peanut appeared despite allergy")
    if len(plan.get("meals") or []) != 5:
        failures.append("Expected 5 meals")

    foods_resp = requests.get(f"{BASE}/foods", timeout=30)
    assert foods_resp.status_code == 200
    print("FOODS count:", foods_resp.json().get("count"))

    if failures:
        print("FAILURES:")
        for f in failures:
            print("-", f)
        return 1
    print("ALL HTTP TESTS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR", exc)
        raise SystemExit(1)
