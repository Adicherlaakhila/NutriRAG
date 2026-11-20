# NutriRAG Chatbot Log (Question 2 – LLM Pipeline)

Record of prompts given to the AI coding assistant for the notebook assignment.  
Earlier incomplete Cursor sessions for this workspace ended with usage-limit errors and are **not invented** here.

| # | Exact / summarized prompt | Relevant assistant response | Chatbot-generated content used? | What changed after verification |
|---|---------------------------|-----------------------------|----------------------------------|---------------------------------|
| 1 | Complete NutriRAG app brief (Q1): build Streamlit/FastAPI RAG app with profile, chat, meal planner, safety, deploy. | Built full app skeleton completion: TF-IDF RAG, prompts, FastAPI, Streamlit, tests. | Yes – app modules (`backend/prompt.py`, `backend/rag.py`, safety refusal text) were reused as design inspiration for the notebook. | Kept working app code; did not rebuild Streamlit for Q2. |
| 2 | Clarification: “do it from beginning.” | Locked plan to seed KB and implement features end-to-end. | Planning only. | Proceeded with full implementation plan. |
| 3 | “Implement the plan as specified.” | Executed Q1 implementation, local tests, screenshots, GitHub push, temporary public tunnels. | Yes – production pipeline patterns. | Confirmed medical refusal and soya-protein grounding before notebook work. |
| 4 | **Question 2 brief:** Create `NutriRAG_LLM_Pipeline.ipynb` with two system prompts, TF-IDF retrieval, Groq pipeline, 8 tests, refinements, plus Chatbot Log / Verification Table / Reflection. Do not require Streamlit/FastAPI to run the notebook. | Created self-contained notebook builder, 12 nutrition notes, chunking, TF-IDF `retrieve_top_k`, `system_prompt_v1`/`v2`, `nutrirag_pipeline`, executed all 8 tests, demonstrated threshold + grounding refinements, wrote submission markdowns. | Yes – notebook code structure and prompts. | Human verification found: (a) low similarity threshold returned irrelevant chunks for seaweed; fixed by raising threshold to **0.25**. (b) `system_prompt_v1` invented non-KB snacks and weak citations; improved with `system_prompt_v2` + allergy validation. Noted remaining limitation that even v2 can still mention foods outside the tiny KB. |
| 5 | Follow-up notifications about git push tasks. | Confirmed repo already synced with `origin/main`. | N/A | No notebook code change. |

### Notes for markers
- Chatbot-generated code was **run**, not trusted blindly.
- LLM provider in this environment used an OpenAI-format key stored as `GROQ_API_KEY` (`sk-...`), so the notebook auto-selects an OpenAI-compatible client while remaining Groq-ready for a `gsk_` key.
- All eight test outputs in the notebook are from actual execution cells, not fabricated.
