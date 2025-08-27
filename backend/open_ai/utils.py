import os
from collections import OrderedDict
from openai import OpenAI

# Import your existing retrieval function and the live Chroma collection
# (Both are set up in ingest_books_to_chroma.py)
from rag.ingest_books_to_chroma import get_book_recommendations  # uses the persisted 'books' collection
import json
from pathlib import Path

# Local JSON data source used by the tool
SCRIPT_DIR = Path(__file__).resolve().parent
JSON_PATH = SCRIPT_DIR.parent / "data" / "book_summaries.json"

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

# utils.py (replace the whole answer_with_rag function)
def answer_with_rag(user_query: str, *, n=3, k=3, temp=0.2, max_tokens=500, fallback_message=None):
    """
    Chat Completions version (tool-calls supported widely across SDKs):
      1) Retrieve similar books and build compact RAG context (titles + short summaries).
      2) Ask the model to pick ONE title and call get_summary_by_title via tools.
      3) Execute tool calls locally; send a 'tool' role message back; get final composed answer.
      4) Never return an empty string (defensive fallback included).
    """
    # ---------- Stage 1: Retrieve + build context ----------
    results = get_book_recommendations(user_query, n=n)
    context_str, titles = build_context_from_results(results, max_items=k)

    if not context_str.strip():
        return fallback_message or (
            "I couldn't find any recommendations in my book set for this query. "
            "Try rephrasing or ask for a theme (e.g., dystopia, adventure, classic)."
        )

    system_text = (
        f"{SYSTEM_PROMPT}\n\n"
        "Process:\n"
        "1) Choose ONE exact title (prefer one present in the RAG context).\n"
        "2) Call get_summary_by_title(title) to fetch the FULL summary.\n"
        "3) Finally answer with:\n"
        "- **Title**\n"
        "- One-sentence rationale for why it matches the user's request\n"
        "- The FULL summary from the tool\n"
        "If the exact title isn't in local summaries, present your rationale and state the tool couldn't find it."
    )

    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": f"RAG CONTEXT:\n{context_str}\n\nUSER QUESTION:\n{user_query}"},
    ]

    # ---------- Stage 1: Ask model; allow tool calls ----------
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4o" / "gpt-4.1-mini" if available in your account
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=temp,
        max_tokens=max_tokens,
    )

    # Extract the assistant message
    choice = (resp.choices or [None])[0]
    assistant_msg = choice.message if choice else None

    # ---------- Stage 1.5: Execute tool calls locally ----------
    tool_messages = []
    chosen_title = ""

    if assistant_msg and getattr(assistant_msg, "tool_calls", None):
        for tc in assistant_msg.tool_calls:
            if tc.type == "function":
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                if fn_name == "get_summary_by_title":
                    chosen_title = (args.get("title") or "").strip()
                    summary_out = get_summary_by_title(chosen_title)
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": summary_out if summary_out else "Title not found in local summaries."
                    })

    # If no tool call was made, fabricate a sane default so we can still compose a final answer
    if not tool_messages:
        if not chosen_title:
            chosen_title = (titles[0] if titles else "").strip()
        summary_out = get_summary_by_title(chosen_title) if chosen_title else "Title not found in local summaries."
        # Create a synthetic assistant tool-call to keep the flow uniform
        synthetic_tool_call_id = "local_fallback"
        assistant_msg = assistant_msg or {"role": "assistant", "content": ""}
        tool_messages.append({
            "role": "tool",
            "tool_call_id": synthetic_tool_call_id,
            "content": summary_out if summary_out else "Title not found in local summaries."
        })

    # ---------- Stage 2: Compose final answer with the tool results ----------
    compose_system = {
        "role": "system",
        "content": (
            f"{SYSTEM_PROMPT}\n\n"
            "You have received the tool result containing the FULL summary. "
            "Write the final answer in this exact format:\n"
            f"- **Title:** {chosen_title or 'Unknown'}\n"
            "- One-sentence rationale (why it matches the user request)\n"
            "- The FULL summary (exactly as provided by the tool)"
        )
    }

    messages2 = [
        compose_system,
        # Reuse original user context so the assistant can reference RAG evidence if needed
        messages[1],
        # Include the assistant's tool-call message (or synthetic)
        (assistant_msg if isinstance(assistant_msg, dict) else assistant_msg.model_dump()),
        # Then the tool results
        *tool_messages
    ]

    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages2,
        temperature=temp,
        max_tokens=max_tokens,
    )

    final_choice = (final.choices or [None])[0]
    final_text = (final_choice.message.content if final_choice and final_choice.message else "") or ""

    # ---------- Defensive fallback: never return empty text ----------
    if not final_text.strip():
        full_summary = tool_messages[0]["content"] if tool_messages else "No tool result."
        rationale = "Picked based on highest similarity and thematic match in the RAG context."
        return f"- **Title:** {chosen_title or 'Unknown'}\n- {rationale}\n- {full_summary}"

    return final_text


def _load_book_summaries():
    if not JSON_PATH.exists():
        return {}
    with JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect list of {"title": "...", "summary": "..."}
    return {item["title"]: item["summary"] for item in data if "title" in item and "summary" in item}

def get_summary_by_title(title: str) -> str:
    """Return the full summary for an exact book title from local JSON."""
    db = _load_book_summaries()
    if not db:
        return "Local summaries not found."
    # Exact match first, then a trimmed fallback
    if title in db:
        return db[title]
    key = title.strip()
    return db.get(key, "Title not found in local summaries.")

# utils.py (add below the get_summary_by_title)
TOOLS = [
    {
        "type": "function",
        "name": "get_summary_by_title",             # ← add top-level name (compat)
        "function": {
            "name": "get_summary_by_title",         # ← keep nested name (standard)
            "description": "Return the full summary for an exact book title from the local dataset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Exact title to look up."
                    }
                },
                "required": ["title"]
            }
        }
    }
]


