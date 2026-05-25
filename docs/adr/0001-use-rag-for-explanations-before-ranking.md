# Use RAG for explanations before ranking

We will first add RAG as an explanation layer over the existing hybrid recommender, not as part of ranking. This preserves the current recommendation pipeline while improving explainability; natural-language movie search can be added later, but RAG ranking is intentionally deferred because it is harder to evaluate and would destabilize the current architecture.
