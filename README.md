# NutriRAG

AI-powered Indian nutrition assistant using **Retrieval-Augmented Generation (RAG)**.

- **Frontend:** Streamlit  
- **Backend:** FastAPI  
- **Database:** Supabase  
- **LLM:** Groq (with OpenAI-compatible fallback if an `sk-` key is provided)  
- **Retrieval:** TF-IDF over foods + nutrition notes  

## Features

1. User profile (age, goal, diet, allergies, daily ₹ budget)
2. Personalized nutrition chatbot with conversation history
3. Grounded RAG answers with visible sources
4. One-day meal planner (5 meals + totals)
5. Medical-safety refusals + educational disclaimer
6. Food knowledge base browser

## Quick start (local)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your keys
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Preferred LLM key (`gsk_...` for Groq). An `sk-...` OpenAI key also works as fallback. |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon/publishable key |
| `BACKEND_URL` | Frontend → API base URL (`http://127.0.0.1:8000` locally) |

### Database

Run [`database/schema.sql`](database/schema.sql) in the Supabase SQL editor if you need fresh tables.  
This project also works with the existing Supabase `foods` / `nutrition_notes` schemas and falls back to local CSV/TXT data.

Optional seed:

```bash
python backend/seed_db.py
```

### Run API

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Run Streamlit UI

```bash
streamlit run frontend/app.py
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + index status |
| POST | `/profile` | Save profile |
| GET | `/profile` | Load profile |
| POST | `/chat` | RAG chat |
| POST | `/meal-plan` | One-day meal plan |
| GET | `/foods` | List/search foods |

## Deployment

### Backend (Render)

1. Connect this GitHub repo to Render.
2. Use `render.yaml` or create a Web Service:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Set env vars: `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`.

### Frontend (Streamlit Community Cloud)

1. Deploy `frontend/app.py` from this repo.
2. In Streamlit secrets / env, set:
   ```toml
   BACKEND_URL = "https://YOUR-RENDER-API.onrender.com"
   ```

## Disclaimer

NutriRAG provides general nutrition information for educational purposes only. It is not a substitute for professional medical advice, diagnosis or treatment. Please consult a qualified doctor or registered dietitian for individual medical concerns.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
