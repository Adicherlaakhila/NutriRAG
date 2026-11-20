"""NutriRAG Streamlit frontend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
USER_ID = "default"

DISCLAIMER = (
    "NutriRAG provides general nutrition information for educational purposes only. "
    "It is not a substitute for professional medical advice, diagnosis or treatment. "
    "Please consult a qualified doctor or registered dietitian for individual medical concerns."
)

GOALS = [
    "Weight loss",
    "Weight gain",
    "Muscle gain",
    "Maintain weight",
    "General healthy eating",
]
DIETS = ["Vegetarian", "Vegan", "Eggetarian", "Non-vegetarian"]
ALLERGIES = ["Peanuts", "Milk", "Soy", "Gluten", "Eggs", "Other"]

st.set_page_config(
    page_title="NutriRAG",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Fraunces:wght@600;700&display=swap');
html, body, [class*="css"]  { font-family: 'DM Sans', sans-serif; }
.main-title { font-family: 'Fraunces', serif; font-size: 2.4rem; color: #1b4332; margin-bottom: 0.2rem; }
.subtitle { color: #52796f; font-size: 1.05rem; margin-bottom: 1.2rem; }
.card {
  background: linear-gradient(145deg, #f8fff9 0%, #e9f5ee 100%);
  border: 1px solid #d8e8de;
  border-radius: 16px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.8rem;
}
.metric-row { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.metric {
  background: #ffffff;
  border-radius: 12px;
  padding: 0.75rem 1rem;
  border: 1px solid #dde8e1;
  min-width: 120px;
}
.disclaimer {
  background: #fff8e8;
  border-left: 4px solid #e9c46a;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: #5c4a1f;
  font-size: 0.92rem;
  margin: 0.8rem 0 1.2rem 0;
}
.source-box {
  background: #f4f7f5;
  border-radius: 10px;
  padding: 0.6rem 0.8rem;
  margin-top: 0.4rem;
  font-size: 0.85rem;
  color: #345;
}
.hero {
  background: radial-gradient(circle at top left, #d8f3dc, #f1faee 45%, #ffffff);
  border-radius: 20px;
  padding: 1.6rem 1.8rem;
  border: 1px solid #cfe3d6;
  margin-bottom: 1rem;
}
@media (max-width: 768px) {
  .main-title { font-size: 1.8rem; }
  .hero { padding: 1.1rem; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def api_get(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BACKEND_URL}{path}", timeout=60, **kwargs)


def api_post(path: str, payload: dict[str, Any]) -> requests.Response:
    return requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=90)


def show_disclaimer() -> None:
    st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "page": "Home",
        "profile": None,
        "chat_history": [],
        "meal_plan": None,
        "foods": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def nav() -> str:
    st.sidebar.markdown("## NutriRAG")
    st.sidebar.caption("AI nutrition assistant")
    page = st.sidebar.radio(
        "Navigate",
        [
            "Home",
            "My Profile",
            "Nutrition Chat",
            "Meal Planner",
            "Food Knowledge Base",
            "About NutriRAG",
        ],
        index=[
            "Home",
            "My Profile",
            "Nutrition Chat",
            "Meal Planner",
            "Food Knowledge Base",
            "About NutriRAG",
        ].index(st.session_state.page)
        if st.session_state.page
        in [
            "Home",
            "My Profile",
            "Nutrition Chat",
            "Meal Planner",
            "Food Knowledge Base",
            "About NutriRAG",
        ]
        else 0,
    )
    st.session_state.page = page
    try:
        health = api_get("/health")
        if health.ok:
            data = health.json()
            st.sidebar.success(
                f"API online · {data.get('foods_indexed', 0)} foods indexed"
            )
        else:
            st.sidebar.error("API unreachable")
    except Exception:
        st.sidebar.error("API offline — start FastAPI backend")
    st.sidebar.markdown(f"`{BACKEND_URL}`")
    return page


def page_home() -> None:
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">NutriRAG</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Personalized Indian nutrition answers, grounded in a food knowledge base.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    show_disclaimer()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><b>1. Save your profile</b><br/>Age, goal, diet, allergies, budget.</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><b>2. Ask nutrition questions</b><br/>RAG answers with visible sources.</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><b>3. Get a one-day meal plan</b><br/>Calories, protein, and estimated ₹ cost.</div>', unsafe_allow_html=True)

    if st.button("Get started — My Profile", type="primary"):
        st.session_state.page = "My Profile"
        st.rerun()


def page_profile() -> None:
    st.markdown('<div class="main-title">My Profile</div>', unsafe_allow_html=True)
    st.caption("Required for personalized chat and meal planning.")
    show_disclaimer()

    existing = st.session_state.profile or {}
    with st.form("profile_form"):
        age = st.number_input("Age", min_value=0, max_value=150, value=int(existing.get("age") or 25), step=1)
        goal = st.selectbox("Nutrition goal", GOALS, index=GOALS.index(existing["goal"]) if existing.get("goal") in GOALS else 4)
        diet_type = st.selectbox("Diet type", DIETS, index=DIETS.index(existing["diet_type"]) if existing.get("diet_type") in DIETS else 0)
        allergies = st.multiselect("Food allergies", ALLERGIES, default=existing.get("allergies") or [])
        daily_budget = st.number_input(
            "Daily food budget (₹)",
            min_value=-1000.0,
            value=float(existing.get("daily_budget") or 200.0),
            step=10.0,
        )
        submitted = st.form_submit_button("Save profile", type="primary")

    if submitted:
        errors = []
        if age < 1 or age > 120:
            errors.append("Please enter a valid age between 1 and 120.")
        if daily_budget < 0:
            errors.append("Daily budget cannot be negative.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            payload = {
                "id": USER_ID,
                "age": int(age),
                "goal": goal,
                "diet_type": diet_type,
                "allergies": allergies,
                "daily_budget": float(daily_budget),
            }
            try:
                with st.spinner("Saving profile..."):
                    resp = api_post("/profile", payload)
                if resp.ok:
                    st.session_state.profile = resp.json().get("profile", payload)
                    st.success("Profile saved successfully.")
                else:
                    detail = resp.json().get("detail", resp.text)
                    st.error(f"Could not save profile: {detail}")
            except Exception as exc:
                st.error(f"Backend error while saving profile: {exc}")

    if st.session_state.profile:
        p = st.session_state.profile
        st.markdown("#### Saved profile")
        st.markdown(
            f'<div class="card">Age <b>{p.get("age")}</b> · Goal <b>{p.get("goal")}</b> · '
            f'Diet <b>{p.get("diet_type")}</b> · Allergies <b>{", ".join(p.get("allergies") or []) or "None"}</b> · '
            f'Budget <b>₹{p.get("daily_budget")}</b></div>',
            unsafe_allow_html=True,
        )


def page_chat() -> None:
    st.markdown('<div class="main-title">Nutrition Chat</div>', unsafe_allow_html=True)
    show_disclaimer()

    if not st.session_state.profile:
        st.warning("Save your profile first for personalized answers.")
        if st.button("Go to My Profile"):
            st.session_state.page = "My Profile"
            st.rerun()

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("Clear chat"):
            st.session_state.chat_history = []
            st.rerun()

    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn.get("sources"):
                with st.expander("Sources used"):
                    for src in turn["sources"]:
                        st.markdown(
                            f'<div class="source-box"><b>{src.get("title")}</b> '
                            f'({src.get("type")})<br/>{src.get("source")}<br/>'
                            f'<i>{src.get("excerpt")}</i></div>',
                            unsafe_allow_html=True,
                        )

    prompt = st.chat_input("Ask a nutrition question...")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt, "sources": []})
        history_payload = [
            {"role": t["role"], "content": t["content"]}
            for t in st.session_state.chat_history[:-1]
            if t["role"] in ("user", "assistant")
        ]
        with st.spinner("Retrieving knowledge and generating answer..."):
            try:
                resp = api_post(
                    "/chat",
                    {
                        "question": prompt,
                        "user_id": USER_ID,
                        "history": history_payload,
                    },
                )
                if resp.ok:
                    data = resp.json()
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": data.get("answer", ""),
                            "sources": data.get("sources") or [],
                        }
                    )
                else:
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": f"Error: {resp.text}",
                            "sources": [],
                        }
                    )
            except Exception as exc:
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": f"Could not reach the API: {exc}",
                        "sources": [],
                    }
                )
        st.rerun()


def page_meal_planner() -> None:
    st.markdown('<div class="main-title">Meal Planner</div>', unsafe_allow_html=True)
    st.caption("One-day plan: breakfast, snacks, lunch, and dinner.")
    show_disclaimer()

    if not st.session_state.profile:
        st.warning("Save your profile before generating a meal plan.")
        if st.button("Go to My Profile", key="meal_to_profile"):
            st.session_state.page = "My Profile"
            st.rerun()
        return

    p = st.session_state.profile
    st.info(
        f"Planning for {p.get('diet_type')} · {p.get('goal')} · "
        f"allergies: {', '.join(p.get('allergies') or []) or 'None'} · budget ₹{p.get('daily_budget')}"
    )

    if st.button("Generate one-day meal plan", type="primary"):
        with st.spinner("Building a personalized meal plan..."):
            try:
                resp = api_post("/meal-plan", {"user_id": USER_ID})
                if resp.ok:
                    st.session_state.meal_plan = resp.json()
                else:
                    st.error(resp.text)
            except Exception as exc:
                st.error(f"API error: {exc}")

    plan = st.session_state.meal_plan
    if not plan:
        return

    if plan.get("limitation"):
        st.warning(plan["limitation"])

    totals = plan.get("totals") or {}
    m1, m2, m3 = st.columns(3)
    m1.metric("Total calories (approx)", f"{totals.get('calories', 0)}")
    m2.metric("Total protein (g)", f"{totals.get('protein', 0)}")
    m3.metric("Estimated cost (₹)", f"{totals.get('cost', 0)}")

    for meal in plan.get("meals") or []:
        with st.container():
            st.markdown(
                f'<div class="card"><b>{meal.get("name")}</b> · '
                f'{meal.get("calories")} kcal · {meal.get("protein")} g protein · ₹{meal.get("cost")}</div>',
                unsafe_allow_html=True,
            )
            for item in meal.get("items") or []:
                st.write(
                    f"- **{item.get('food')}** ({item.get('serving')}) — "
                    f"{item.get('calories')} kcal, {item.get('protein')} g protein, ₹{item.get('cost')}"
                )

    if plan.get("notes"):
        st.caption(plan["notes"])


def page_foods() -> None:
    st.markdown('<div class="main-title">Food Knowledge Base</div>', unsafe_allow_html=True)
    st.caption("Indian food nutrition records used for RAG retrieval.")
    q = st.text_input("Search foods", placeholder="e.g. soya, paneer, dal")
    try:
        with st.spinner("Loading foods..."):
            resp = api_get("/foods", params={"q": q} if q else None)
        if not resp.ok:
            st.error(resp.text)
            return
        foods = resp.json().get("foods") or []
    except Exception as exc:
        st.error(f"Could not load foods: {exc}")
        return

    st.write(f"{len(foods)} foods")
    for food in foods:
        with st.expander(food.get("food_name", "Food")):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Calories", food.get("calories"))
            c2.metric("Protein (g)", food.get("protein"))
            c3.metric("Carbs (g)", food.get("carbohydrates"))
            c4.metric("Fat (g)", food.get("fat"))
            st.write(f"Serving: {food.get('serving_size')} · Approx cost: ₹{food.get('estimated_cost')}")
            st.caption(food.get("source") or "Source not listed")
            allergies = food.get("allergens") or []
            if allergies:
                st.write("Allergens:", ", ".join(allergies))


def page_about() -> None:
    st.markdown('<div class="main-title">About NutriRAG</div>', unsafe_allow_html=True)
    show_disclaimer()
    st.markdown(
        """
NutriRAG is a Retrieval-Augmented Generation (RAG) app for educational nutrition support.

**How answers are grounded**
1. Your saved profile is loaded.
2. Relevant food records and nutrition notes are retrieved with TF-IDF.
3. Retrieved context + profile are sent to the Groq LLM.
4. The assistant answers from that context and shows sources.

**Safety**
- No medical diagnosis
- No medicine or medication recommendations
- Allergy and diet constraints are applied to recommendations
"""
    )


def main() -> None:
    init_state()
    # Sync profile from API if available
    if st.session_state.profile is None:
        try:
            resp = api_get("/profile", params={"user_id": USER_ID})
            if resp.ok:
                st.session_state.profile = resp.json().get("profile")
        except Exception:
            pass

    page = nav()
    if page == "Home":
        page_home()
    elif page == "My Profile":
        page_profile()
    elif page == "Nutrition Chat":
        page_chat()
    elif page == "Meal Planner":
        page_meal_planner()
    elif page == "Food Knowledge Base":
        page_foods()
    else:
        page_about()


if __name__ == "__main__":
    main()
