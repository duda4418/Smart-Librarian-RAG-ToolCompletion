import os
from collections import OrderedDict
from openai import OpenAI

# Import your existing retrieval function and the live Chroma collection
# (Both are set up in ingest_books_to_chroma.py)
from rag.ingest_books_to_chroma import get_book_recommendations  # uses the persisted 'books' collection

# --- OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "You are a helpful literary assistant for book recommendations. "
    "Use ONLY the provided RAG context (titles + summaries) to answer. "
    "If the context is insufficient, say so briefly. "
    "Recommend 1–2 books that best match the user's request and explain why, "
    "referring to themes/characters/plot. "
    "Answer in the user's language. "
    "Cite recommendations using the bracketed indices from the RAG context, e.g., [1], [2]."
)

def build_context_from_results(results, max_items=3):
    """Compact RAG context: de-dupe by title, add similarity, and format numbered blocks."""
    if not results or not results.get("documents"):
        return "", []

    docs, metas, dists = (results[k][0] for k in ("documents", "metadatas", "distances"))

    # De-dupe while preserving order
    by_title = OrderedDict()
    for doc, meta, dist in zip(docs, metas, dists):
        title = (meta.get("title") or "Untitled").strip() or "Untitled"
        if title not in by_title:
            by_title[title] = (doc, 1.0 - float(dist))
            if len(by_title) >= max_items:
                break

    rows = list(by_title.items())
    parts = [
        f"[{i}] Title: {title}\nSummary: {summary}\nSimilarity: {sim:.3f}"
        for i, (title, (summary, sim)) in enumerate(rows, 1)
    ]
    return "\n\n".join(parts), [title for title, _ in rows]

def answer_with_rag(user_query: str, *, n=3, k=3, temp=0.2, max_tokens=500, fallback_message=None):
    # Retrieve + build compact context
    results = get_book_recommendations(user_query, n=n)
    context_str, _ = build_context_from_results(results, max_items=k)

    if not context_str.strip():
        return fallback_message or (
            "I couldn't find any recommendations in my book set for this query. "
            "Try rephrasing or ask for a theme (e.g., dystopia, adventure, classic)."
        )

    # Single user content block, same Responses schema
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{
                "type": "input_text",
                "text": f"RAG CONTEXT:\n{context_str}\n\nUSER QUESTION:\n{user_query}"
            }]},
        ],
        temperature=temp,
        max_output_tokens=max_tokens,
        store=False,
    )
    return resp.output_text


def repl():
    print("📚 Book Recommender (RAG) — scrie 'exit' pentru a închide.")
    while True:
        try:
            q = input("\nTu: ").strip()
            if not q:
                continue
            if q.lower() in {"exit", "quit", "q"}:
                print("Bye!")
                break
            ans = answer_with_rag(q)
            print(f"\nAsistent:\n{ans}")
        except KeyboardInterrupt:
            print("\nBye!")
            break
repl()