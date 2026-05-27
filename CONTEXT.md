# Movie Recommendation

This context defines the domain language for the movie recommendation product. Use these terms when discussing user inputs, recommendation results, and explanation semantics.

## Language

**Seed Movie**:
A movie explicitly selected by the user to guide a recommendation request.
_Avoid_: Input movie, picked movie, selected movie

**Seed Set**:
The collection of one to five **Seed Movies** used together in a single recommendation request.
_Avoid_: Seed list, inputs, picks

**Anchor Movie**:
The single movie used as the reference point for an explanation or similarity comparison. It is usually chosen from the **Seed Set**, but it is not the same thing as the full **Seed Set**.
_Avoid_: Seed, input, representative movie

**Anchor Vector**:
A non-movie reference point representing the combined taste signal of a **Seed Set**. It is used to compare candidate movies against the user's selected group, but it should not be described as a movie.
_Avoid_: Anchor movie, seed, average movie

**Movie**:
A film entity identified by movie metadata such as title, genre, and movie identifier.
_Avoid_: Recommendation, result

**Recommendation**:
A ranked result item returned by the system for a user request. It references one **Movie** and includes recommendation-specific signals such as score.
_Avoid_: Recommended movie, result movie

**Recommendation List**:
The ordered collection of **Recommendations** returned for a request.
_Avoid_: Movie list, results

**Explanation**:
A response that explains a recommendation request and its **Recommendation List**. It describes the context and signals behind the list, not a standalone explanation for only one **Recommendation**.
_Avoid_: Recommendation detail, single-item explanation

**Score Contribution**:
A per-**Recommendation** signal that shows how a scoring source contributes to the final recommendation score.
_Avoid_: Explanation, metric

**Similar Movie**:
A movie shown as similar to an **Anchor Movie** for explanation purposes. It is not necessarily a **Recommendation**.
_Avoid_: Recommendation, top result

**Collaborative Signal**:
A recommendation signal based on user-movie interaction patterns. The current implementation uses NCF, but the domain term should not be tied to one model architecture.
_Avoid_: NCF signal, rating model

**Content Signal**:
A recommendation signal based on movie content similarity, such as title and genre similarity.
_Avoid_: Embedding score, content embedding

**Hybrid Score**:
The final recommendation score created by combining the **Collaborative Signal** and **Content Signal**.
_Avoid_: Final score, model score

**RAG Explanation**:
A natural-language explanation generated from retrieved movie and recommendation context. It explains a **Recommendation List** after ranking has already happened; it does not decide the ranking.
_Avoid_: RAG ranking, LLM recommendation, chatbot answer

**Natural-Language Movie Search**:
A later search capability where the user describes movie preferences in ordinary language instead of selecting exact titles or genres.
_Avoid_: RAG explanation, ranking

**RAG Evidence**:
The structured, traceable context that a **RAG Explanation** is allowed to use. It can include the **Seed Set**, **Recommendation List**, **Score Contributions**, movie metadata, and **Similar Movies**, but it must not include unsupported movie facts invented by the language model.
_Avoid_: LLM knowledge, generated facts, freeform movie knowledge

**Structured Explanation**:
A **RAG Explanation** format that includes a natural-language summary plus structured item-level reasons and evidence references.
_Avoid_: Freeform explanation, paragraph-only response

**Deterministic Explanation**:
The non-RAG explanation data produced from recommendation scores, signal contributions, seed context, and similarity data.
_Avoid_: RAG explanation, generated explanation

**RAG Explanation Endpoint**:
A separate API surface for generating **Structured Explanations** from **RAG Evidence**. It should not replace the deterministic explanation endpoint until the RAG behavior is stable.
_Avoid_: Explanations endpoint, ranking endpoint

**Deterministic Fallback**:
A non-generated explanation response used when **RAG Explanation** is unavailable. It keeps the user experience functional without changing the **Recommendation List**.
_Avoid_: RAG failure, backup ranking, silent failure

**Seed Ranker**:
The module that owns the shared pipeline for turning a **Seed Set** into a ranked **Recommendation List** using content embeddings. It validates seeds, builds the **Anchor Vector**, scores candidates, and returns a `RankedList` together with **Similar Movies** for the **Anchor Movie**. Both the recommendations endpoint and the explanations endpoint delegate to the Seed Ranker rather than duplicating this logic.
_Avoid_: Recommendation service, ranking handler, scoring util

**Catalog**:
An immutable snapshot of the movie catalog data (movie titles, popularity-ordered IDs, and candidate pool size) passed to the **Seed Ranker** at request time. It is built once at startup from the CSV data loaded by the API.
_Avoid_: Database, data store, global state

**Ranked List**:
The structured result produced by the **Seed Ranker**: an ordered list of `RankedItem` values plus the validated **Seed Set**, the **Anchor Movie** ID, and **Similar Movies**. Callers format this into endpoint-specific responses.
_Avoid_: Recommendation List (the domain term for the user-facing ordered output; Ranked List is the internal module output before formatting)

## Example dialogue

Developer: "The user chose five Seed Movies. Which one should the explanation compare against?"

Domain expert: "Use one Anchor Movie for the explanation, but keep the full Seed Set visible because the recommendations came from all selected Seed Movies."

Developer: "Can I say the recommendations are based on the Anchor Movie?"

Domain expert: "No. The recommendations are based on the Anchor Vector from the Seed Set. The Anchor Movie is only the movie shown as the explanation reference."

Developer: "Is each item in the top-10 just a Movie?"

Domain expert: "No. Each item is a Recommendation because it has ranking meaning and score information. The Movie is the thing being recommended."

Developer: "Does Explanation mean each Recommendation has its own detail page?"

Domain expert: "No. Explanation means the request-level explanation for the Recommendation List. Individual Recommendations can show Score Contributions inside that explanation."

Developer: "Should the UI say this came from NCF?"

Domain expert: "Use Collaborative Signal in product language. NCF is the current implementation behind that signal, not the domain concept."

Developer: "Is RAG going to choose which movies to recommend?"

Domain expert: "No. First use RAG for RAG Explanation after the Recommendation List exists. Natural-Language Movie Search can come later, but ranking remains separate for now."

Developer: "Can the explanation mention plot details if they sound right?"

Domain expert: "Only if those details are part of RAG Evidence. The explanation must be grounded in retrieved or structured data, not the model's memory."

Developer: "Can the RAG service just return one paragraph?"

Domain expert: "No. Use a Structured Explanation so the UI, tests, and debugging can inspect the summary, item reasons, and evidence references separately."

Developer: "Should we replace the existing explanation endpoint with RAG?"

Domain expert: "No. Keep Deterministic Explanation separate and add a RAG Explanation Endpoint so generated explanations can evolve without breaking existing behavior."

Developer: "If the language model fails, should recommendations fail too?"

Domain expert: "No. Use a Deterministic Fallback for explanation text. RAG improves the explanation experience, but it must not control or break ranking."
