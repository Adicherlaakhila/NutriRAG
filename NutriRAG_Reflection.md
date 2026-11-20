# NutriRAG Reflection (Question 2)

While building the NutriRAG notebook pipeline, I found that AI-generated code was useful as a starting point but needed careful checking. Two clear problems showed up when I ran the cells myself.

First, TF-IDF retrieval looked “successful” even when the question was outside the knowledge base. For the rare seaweed protein question, a low similarity threshold still returned paneer, chicken and egg chunks with weak scores. That was dangerous because the pipeline could pretend those notes were relevant. I identified this by printing similarity scores and reading the chunk topics. The fix was to raise the relevance threshold to 0.25 so weak matches are rejected and the system openly says the knowledge base is insufficient.

Second, the basic system prompt allowed unsupported answers. On the peanut-free snack question, Version 1 suggested Greek yogurt and hummus and even cited a vague “General nutrition knowledge” source that was not in our notes. Version 2 reduced that behaviour by forcing chunk-ID citations and stronger grounding, and I also added a simple allergy validation check. Even after that, the model can still mention foods that are not in the tiny notebook knowledge base, which taught me that prompt rules alone are not enough.

Overall, I learned that prompt engineering and RAG work best together: retrieval must be filtered, prompts must demand evidence, and humans must verify outputs. An AI nutrition assistant should not be trusted for diagnosis, medication, disease-specific dosing, or any answer when retrieved evidence is weak or missing.
