"""Prompt templates and safety helpers for NutriRAG."""

from __future__ import annotations

import re
from typing import Any

DISCLAIMER = (
    "NutriRAG provides general nutrition information for educational purposes only. "
    "It is not a substitute for professional medical advice, diagnosis or treatment. "
    "Please consult a qualified doctor or registered dietitian for individual medical concerns."
)

MEDICAL_REFUSAL = (
    "I cannot diagnose medical conditions or recommend medicines. "
    "Please consult a qualified doctor for diagnosis and treatment. "
    "I can provide general nutrition education."
)

UNSAFE_PATTERNS = [
    r"\bdiagnos(e|is|ing)\b",
    r"\bdiabetes\b.*\b(medicine|medication|drug|tablet|insulin)\b",
    r"\b(medicine|medication|drug|tablet|prescription|prescribe)\b",
    r"\bwhich medicine\b",
    r"\btell me which medicine\b",
    r"\bsupplement(s)?\b.*\b(dose|dosage|prescribe|recommend)\b",
    r"\bprescribe\b",
    r"\btreatment plan for my\b",
    r"\bdo i have\b.*\b(disease|diabetes|cancer|thyroid)\b",
]


def is_unsafe_medical_query(question: str) -> bool:
    q = question.lower()
    # Strong refusal for diagnosis + medication combo or direct medical asks
    if re.search(r"\bdiagnos", q) and (
        re.search(r"\b(medicine|medication|drug|tablet|diabetes|disease|condition)\b", q)
    ):
        return True
    if re.search(r"\b(recommend|suggest|give me|tell me)\b.*\b(medicine|medication|drug|tablet)s?\b", q):
        return True
    if re.search(r"\b(medicine|medication|drug|tablet)s?\b.*\b(for my|to treat|for diabetes)\b", q):
        return True
    if re.search(r"\bprescribe\b", q):
        return True
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, q):
            # Allow pure nutrition education about diabetes diet without meds
            if "diabetes" in q and not re.search(
                r"\b(medicine|medication|drug|tablet|diagnos|prescribe|insulin)\b", q
            ):
                continue
            return True
    return False


def format_profile(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "No user profile saved yet."
    allergies = profile.get("allergies") or []
    if isinstance(allergies, str):
        allergies = [allergies]
    return (
        f"Age: {profile.get('age')}; "
        f"Goal: {profile.get('goal')}; "
        f"Diet: {profile.get('diet_type')}; "
        f"Allergies: {', '.join(allergies) if allergies else 'None'}; "
        f"Daily food budget: Rs {profile.get('daily_budget')}."
    )


def format_sources(docs: list[dict[str, Any]]) -> list[dict[str, str]]:
    sources = []
    for doc in docs:
        sources.append(
            {
                "title": str(doc.get("title", "")),
                "type": str(doc.get("type", "")),
                "source": str(doc.get("source") or "NutriRAG knowledge base"),
                "excerpt": str(doc.get("text", ""))[:280],
            }
        )
    return sources


def build_chat_messages(
    question: str,
    profile: dict[str, Any] | None,
    retrieved: list[dict[str, Any]],
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    context_blocks = []
    for i, doc in enumerate(retrieved, start=1):
        context_blocks.append(f"[{i}] ({doc.get('type')}) {doc.get('text')}")
    context = "\n".join(context_blocks) if context_blocks else "NO RELEVANT RECORDS FOUND."

    system = f"""You are NutriRAG, an educational Indian nutrition assistant using Retrieval-Augmented Generation.

Rules:
1. Answer using ONLY the retrieved knowledge-base context below plus the user profile for personalization.
2. If the context is insufficient, say clearly that the knowledge base does not contain sufficient information.
3. Never invent precise nutrition numbers that are not in the context. Label values as approximate.
4. Never diagnose diseases, prescribe medicines, or recommend supplements/medications.
5. Respect diet type and allergies. Never suggest foods that match allergies.
6. Do not give dangerous extreme weight-loss advice (very low calorie crash diets, starvation, detox extremes).
7. Cite the source titles/numbers you used (e.g., Source [1], [2]).
8. Keep answers clear and practical for Indian home cooking contexts.

Disclaimer to remember: {DISCLAIMER}

User profile:
{format_profile(profile)}

Retrieved knowledge-base context:
{context}
"""

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages


def build_meal_plan_messages(
    profile: dict[str, Any],
    candidate_foods: list[dict[str, Any]],
) -> list[dict[str, str]]:
    food_lines = []
    for f in candidate_foods:
        food_lines.append(
            f"- {f['food_name']} | serving {f['serving_size']} | "
            f"{f['calories']} kcal | protein {f['protein']} g | "
            f"carbs {f['carbohydrates']} g | fat {f['fat']} g | "
            f"approx cost Rs {f['estimated_cost']} | source: {f.get('source', '')}"
        )
    foods_block = "\n".join(food_lines) if food_lines else "No eligible foods."

    system = f"""You are NutriRAG meal planner. Create ONE day meal plan for an Indian user.

Must include exactly these meals: Breakfast, Morning snack, Lunch, Evening snack, Dinner.
Use ONLY foods from the candidate list. Respect diet type and never include allergy foods.
Consider the nutrition goal and stay within the daily budget as far as feasible.
If the budget cannot support a nutritionally reasonable plan, explain the limitation instead of inventing an unrealistic plan.

For each meal provide:
- food items with approximate serving sizes
- approximate calories
- protein in grams
- estimated meal cost in Rs

Also provide daily totals for calories, protein, and estimated cost.
Mark all values as approximate. Actual values vary by preparation and portion size.

Return STRICT JSON with this shape:
{{
  "feasible": true,
  "limitation": null,
  "meals": [
    {{
      "name": "Breakfast",
      "items": [{{"food": "...", "serving": "...", "calories": 0, "protein": 0, "cost": 0}}],
      "calories": 0,
      "protein": 0,
      "cost": 0
    }}
  ],
  "totals": {{"calories": 0, "protein": 0, "cost": 0}},
  "notes": "short educational note"
}}

User profile:
{format_profile(profile)}

Candidate foods (filtered):
{foods_block}
"""
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": "Generate today's personalized meal plan as JSON only.",
        },
    ]
