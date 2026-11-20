"""Seed Supabase foods + nutrition_notes from local data files."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.supabase_client import clear_notes, get_supabase, upsert_foods, upsert_notes


def load_foods_from_csv() -> list[dict]:
    path = BASE_DIR / "data" / "food_nutrients.csv"
    rows = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            diet_tags = [t.strip() for t in (raw.get("diet_tags") or "").split("|") if t.strip()]
            allergens = [a.strip() for a in (raw.get("allergens") or "").split("|") if a.strip()]
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
                    "diet_tags": diet_tags,
                    "allergens": allergens,
                }
            )
    return rows


def load_notes_from_txt() -> list[dict]:
    path = BASE_DIR / "data" / "nutrition_notes.txt"
    text = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    notes = []
    for block in blocks:
        topic = content = source = ""
        for line in block.splitlines():
            if line.startswith("TOPIC:"):
                topic = line[len("TOPIC:") :].strip()
            elif line.startswith("CONTENT:"):
                content = line[len("CONTENT:") :].strip()
            elif line.startswith("SOURCE:"):
                source = line[len("SOURCE:") :].strip()
            elif content and not line.startswith("SOURCE:"):
                content = f"{content} {line.strip()}"
        if topic and content:
            notes.append({"topic": topic, "content": content, "source": source})
    return notes


def main() -> None:
    client = get_supabase()
    if not client:
        print("Supabase not configured — local CSV/notes will still be used as fallback.")
        return

    foods = load_foods_from_csv()
    notes = load_notes_from_txt()
    print(f"Loaded {len(foods)} foods and {len(notes)} notes from disk.")

    clear_notes()
    n_foods = upsert_foods(foods)
    n_notes = upsert_notes(notes)
    print(f"Upserted foods: {n_foods}; inserted notes: {n_notes}")


if __name__ == "__main__":
    main()
