"""TF-IDF retrieval over Indian food nutrients and nutrition notes."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent


def _parse_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if str(v).strip()]
    text = str(value)
    parts = re.split(r"[|,;]", text)
    return [p.strip().lower() for p in parts if p.strip()]


def load_foods_local() -> list[dict[str, Any]]:
    path = BASE_DIR / "data" / "food_nutrients.csv"
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                {
                    "food_name": raw["food_name"].strip(),
                    "serving_size": raw["serving_size"].strip(),
                    "calories": float(raw["calories"]),
                    "protein": float(raw["protein"]),
                    "carbohydrates": float(raw["carbohydrates"]),
                    "fat": float(raw["fat"]),
                    "estimated_cost": float(raw["estimated_cost"]),
                    "source": (raw.get("source") or "").strip(),
                    "diet_tags": _parse_list_field(raw.get("diet_tags")),
                    "allergens": _parse_list_field(raw.get("allergens")),
                }
            )
    return rows


def load_notes_local() -> list[dict[str, Any]]:
    path = BASE_DIR / "data" / "nutrition_notes.txt"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    notes = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        topic = content = source = ""
        for line in block.splitlines():
            if line.startswith("TOPIC:"):
                topic = line[len("TOPIC:") :].strip()
            elif line.startswith("CONTENT:"):
                content = line[len("CONTENT:") :].strip()
            elif line.startswith("SOURCE:"):
                source = line[len("SOURCE:") :].strip()
            elif content and not line.startswith(("TOPIC:", "SOURCE:")):
                content = f"{content} {line.strip()}"
        if topic and content:
            notes.append({"topic": topic, "content": content, "source": source})
    return notes


def _first_number(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if row.get(key) is not None and row.get(key) != "":
            try:
                return float(row[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def _normalize_food_row(row: dict[str, Any]) -> dict[str, Any]:
    serving = row.get("serving_size") or row.get("food_state") or "100 g"
    if serving and not str(serving).endswith(("g", "ml", "piece", "pieces")) and str(serving).lower() in {
        "raw",
        "cooked",
        "boiled",
    }:
        serving = f"100 g ({serving})"
    return {
        "food_name": str(row.get("food_name", "")).strip(),
        "serving_size": str(serving).strip(),
        "calories": _first_number(row, "calories", "calories_kcal"),
        "protein": _first_number(row, "protein", "protein_g"),
        "carbohydrates": _first_number(row, "carbohydrates", "carbohydrates_g", "carbs", "carbs_g"),
        "fat": _first_number(row, "fat", "fat_g"),
        "estimated_cost": _first_number(
            row, "estimated_cost", "estimated_price_inr_per_100g", "price", "cost"
        ),
        "source": str(row.get("source") or "").strip(),
        "diet_tags": _parse_list_field(row.get("diet_tags")),
        "allergens": _parse_list_field(row.get("allergens")),
    }


class NutriRetriever:
    """In-memory TF-IDF index for foods and nutrition notes."""

    def __init__(self) -> None:
        self.foods: list[dict[str, Any]] = []
        self.notes: list[dict[str, Any]] = []
        self.documents: list[dict[str, Any]] = []
        self._corpus: list[str] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    def load(self) -> None:
        foods: list[dict[str, Any]] = []
        notes: list[dict[str, Any]] = []
        try:
            from database.supabase_client import fetch_all_foods, fetch_all_notes

            foods = [_normalize_food_row(r) for r in (fetch_all_foods() or [])]
            notes = fetch_all_notes() or []
        except Exception:
            foods, notes = [], []

        local_foods = load_foods_local()
        local_notes = load_notes_local()

        # Prefer Supabase when nutrient fields are populated; otherwise use local CSV.
        if foods and any(f.get("calories", 0) > 0 or f.get("protein", 0) > 0 for f in foods):
            # Merge any local-only foods missing from Supabase
            existing = {f["food_name"].lower() for f in foods}
            for lf in local_foods:
                if lf["food_name"].lower() not in existing:
                    foods.append(lf)
        else:
            foods = local_foods

        if not notes:
            notes = local_notes
        else:
            # Ensure local educational notes are available even if Supabase has others
            existing_topics = {str(n.get("topic", "")).lower() for n in notes}
            for ln in local_notes:
                if ln["topic"].lower() not in existing_topics:
                    notes.append(ln)

        self.foods = foods
        self.notes = notes
        self._build_index()

    def _build_index(self) -> None:
        docs: list[dict[str, Any]] = []
        corpus: list[str] = []

        for food in self.foods:
            text = (
                f"Food: {food['food_name']}. Serving: {food['serving_size']}. "
                f"Calories: {food['calories']} kcal. Protein: {food['protein']} g. "
                f"Carbohydrates: {food['carbohydrates']} g. Fat: {food['fat']} g. "
                f"Estimated cost: Rs {food['estimated_cost']}. "
                f"Source: {food['source']}. "
                f"Diet tags: {', '.join(food['diet_tags'])}. "
                f"Allergens: {', '.join(food['allergens']) or 'none'}."
            )
            docs.append(
                {
                    "type": "food",
                    "title": food["food_name"],
                    "text": text,
                    "source": food["source"],
                    "raw": food,
                }
            )
            corpus.append(text)

        for note in self.notes:
            topic = str(note.get("topic") or note.get("title") or "Note")
            content = str(note.get("content", ""))
            source = str(note.get("source", ""))
            text = f"Topic: {topic}. {content} Source: {source}."
            docs.append(
                {
                    "type": "note",
                    "title": topic,
                    "text": text,
                    "source": source,
                    "raw": note,
                }
            )
            corpus.append(text)

        self.documents = docs
        self._corpus = corpus
        if not corpus:
            self._vectorizer = None
            self._matrix = None
            return

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 4, min_score: float = 0.05) -> list[dict[str, Any]]:
        if not query.strip() or self._vectorizer is None or self._matrix is None:
            return []

        q = self._vectorizer.transform([query])
        scores = cosine_similarity(q, self._matrix).flatten()
        ranked = scores.argsort()[::-1]

        results: list[dict[str, Any]] = []
        for idx in ranked[:top_k]:
            score = float(scores[idx])
            if score < min_score:
                continue
            doc = dict(self.documents[idx])
            doc["score"] = round(score, 4)
            results.append(doc)
        return results

    def get_foods(
        self,
        query: str | None = None,
        diet_type: str | None = None,
        allergies: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        allergies = [a.lower() for a in (allergies or [])]
        diet = (diet_type or "").lower().replace(" ", "-")
        # normalize common labels
        diet_map = {
            "vegetarian": "vegetarian",
            "vegan": "vegan",
            "eggetarian": "eggetarian",
            "non-vegetarian": "non-vegetarian",
            "non vegetarian": "non-vegetarian",
        }
        diet = diet_map.get(diet, diet)

        foods = list(self.foods)
        if diet:
            foods = [f for f in foods if diet in f.get("diet_tags", []) or not f.get("diet_tags")]
        if allergies:
            filtered = []
            for f in foods:
                allergens = set(f.get("allergens") or [])
                name = f.get("food_name", "").lower()
                blocked = False
                for allergy in allergies:
                    a = allergy.lower().strip()
                    if a in ("other", ""):
                        continue
                    if a in allergens or a in name:
                        blocked = True
                        break
                if not blocked:
                    filtered.append(f)
            foods = filtered

        if query:
            q = query.lower().strip()
            foods = [f for f in foods if q in f.get("food_name", "").lower()]
        return foods


_retriever: NutriRetriever | None = None


def get_retriever() -> NutriRetriever:
    global _retriever
    if _retriever is None:
        _retriever = NutriRetriever()
        _retriever.load()
    return _retriever


def reload_retriever() -> NutriRetriever:
    global _retriever
    _retriever = NutriRetriever()
    _retriever.load()
    return _retriever
