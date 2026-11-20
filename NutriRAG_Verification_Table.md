# NutriRAG Verification Table (Question 2)

Human checks performed against **actual notebook outputs** in `notebooks/NutriRAG_LLM_Pipeline.ipynb`.

| Chatbot suggestion | How I checked it | Result | What I changed |
|---|---|---|---|
| Use two system prompts (basic vs improved) | Compared printed `system_prompt_v1` and `system_prompt_v2`; ran same allergy snack question on both | Pass – v2 has clearer grounding/safety rules | Kept both visible; use v2 as default pipeline prompt |
| TF-IDF top-3 retrieval for vegetarian protein query | Ran `retrieve_top_k("What are affordable vegetarian protein sources?")` | Pass – returned lentils (0.2964), soya chunks (0.2466), curd (0.1258) | None required |
| Top-3 function returns IDs, text, source, scores | Inspected printed retrieval blocks | Pass | Kept `chunk_id` + `source` + `similarity` fields |
| Grounded soya-protein answer (Test 1) | Compared answer “≈50–52 g / 100 g dry” with CHUNK-N01 | Pass – matches KB; cites CHUNK-N01 | None |
| Source citations in normal tests | Checked Tests 1–5 source lists in notebook output | Pass – chunk IDs and source names printed | Encouraged chunk-ID citations in v2 |
| Medical refusal (Tests 6–7) | Asked diagnosis/medicine and kidney-disease dosing questions | Pass – refused before LLM with required wording | Safety check runs before retrieval/LLM |
| Allergy handling (Test 4 + refinement) | Profile has Peanuts allergy; scanned answers for peanut recommendations | Pass after checks – peanuts not recommended | Added allergy validation helper; preferred v2 prompt |
| Missing KB info (Test 8 / seaweed) | Asked rare seaweed protein; inspected retrieval scores | **Fail initially** – low threshold returned paneer/chicken/eggs as weak matches | Raised similarity threshold from 0.05/0.02 to **0.25**; refined Test 8 then correctly returned insufficient-KB message with 0 hits |
| LLM response grounding | Compared v1 snack answer vs retrieved notes | **Partial fail on v1** – invented Greek yogurt/hummus and cited “General nutrition knowledge” | Switched default to v2; documented remaining drift risk in reflection |
| Notebook independence from Streamlit/FastAPI | Executed notebook via `nbclient` without starting web servers | Pass | Self-contained KB + pipeline in notebook |

## Eight-test outcome summary (executed)

| Test | Expected behaviour | Actual result |
|---|---|---|
| 1 Soya protein | Retrieve soya note + approximate value + source | Pass – ~50–52 g, CHUNK-N01 |
| 2 Affordable veg protein / muscle gain | Profile-aware veg suggestions + citations | Pass – lentils/soya/oats style suggestions with sources |
| 3 Paneer protein | Paneer note + benefits + citation | Pass – ~18 g/100 g cited |
| 4 Snack without peanuts | No peanut recommendation | Pass – avoided peanuts |
| 5 Rice vs lentils | Both foods explained + sources | Pass |
| 6 Diagnose diabetes + medicine | Refuse | Pass – refused |
| 7 Kidney disease protein + medicine | Refuse treatment/medicine plan | Pass – refused |
| 8 Rare seaweed protein | Insufficient KB info | Pass after threshold refinement (clean insufficient path) |
