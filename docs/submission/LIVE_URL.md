# NutriRAG – Live Application Link

## Public demo URL (no login)

**NutriRAG UI:** https://raise-what-nested-aimed.trycloudflare.com

**API health:** https://supplied-foundations-demand-solo.trycloudflare.com/health

These Cloudflare quick tunnels forward to the local Streamlit + FastAPI processes. Keep those processes running while the demo is needed. For a permanent class submission link, redeploy to Streamlit Community Cloud + Render using the repo below.

## Source repository

https://github.com/Adicherlaakhila/NutriRAG

## Permanent hosting checklist

1. **Render (API)**  
   - Repo: `Adicherlaakhila/NutriRAG`  
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`  
   - Env: `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`

2. **Streamlit Community Cloud (UI)**  
   - Main file: `frontend/app.py`  
   - Secret: `BACKEND_URL = https://<your-render-service>.onrender.com`
