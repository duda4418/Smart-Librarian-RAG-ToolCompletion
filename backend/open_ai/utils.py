import os
import json
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI

# Import your existing retrieval function and the live Chroma collection
# (Both are set up in ingest_books_to_chroma.py)
from rag.ingest_books_to_chroma import get_book_recommendations  # uses the persisted 'books' collection

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

def _load_book_summaries() -> Dict[str, str]:
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
    if not title:
        return "Title not found in local summaries."
    # Exact match first, then trimmed fallback
    if title in db:
        return db[title]
    key = title.strip()
    return db.get(key, "Title not found in local summaries.")

def build_context_from_results(results: Dict[str, Any], max_items: int = 3):
    """Compact RAG context: de-dupe by title, add similarity, and format numbered blocks."""
    if not results or not results.get("documents"):
        return "", []

    docs, metas, dists = (results[k][0] for k in ("documents", "metadatas", "distances"))

    # De-dupe while preserving order
    by_title: "OrderedDict[str, Any]" = OrderedDict()
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

# ---- Tools schema (aligns with official docs) ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_summary_by_title",
            "description": "Return the full summary for an exact book title from the local dataset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Exact title to look up."
                    }
                },
                "required": ["title"],
                "additionalProperties": False
            }
        }
    }
]

def _safe_json_loads(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}

def _execute_tool_call(name: str, args: Dict[str, Any]) -> str:
    if name == "get_summary_by_title":
        return get_summary_by_title((args.get("title") or "").strip())
    # Future: add more tools here
    return "Unknown tool."

def answer_with_rag(
    user_query: str,
    *,
    n: int = 3,
    k: int = 3,
    temp: float = 0.2,
    max_tokens: int = 500,
    fallback_message: str | None = None
) -> str:
    """
    Chat Completions function-calling (per docs):
      1) Retrieve similar books and build compact RAG context (titles + short summaries).
      2) Ask the model with `tools` enabled; capture tool calls.
      3) Execute tool calls locally; send back `tool` role messages keyed by tool_call_id.
      4) Get final composed answer.

    If the context is empty, return a friendly fallback.
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

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": f"RAG CONTEXT:\n{context_str}\n\nUSER QUESTION:\n{user_query}"},
    ]

    # ---------- Stage 1: Ask model; allow tool calls ----------
    first = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=temp,
        max_tokens=max_tokens,
    )

    choice = (first.choices or [None])[0]
    assistant_msg = getattr(choice, "message", None)

    tool_msgs: List[Dict[str, Any]] = []
    chosen_title = ""

    # ---------- Stage 1.5: Execute any/all tool calls locally ----------
    if assistant_msg and getattr(assistant_msg, "tool_calls", None):
        for tc in assistant_msg.tool_calls:
            if tc.type != "function":
                continue
            fn_name = getattr(tc.function, "name", "")
            args = _safe_json_loads(getattr(tc.function, "arguments", "") or "{}")

            if fn_name == "get_summary_by_title":
                chosen_title = (args.get("title") or "").strip()

            result_text = _execute_tool_call(fn_name, args)
            tool_msgs.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text
            })

    # ---------- Decide path: with or without tool calls ----------
    has_tool_calls = bool(assistant_msg and getattr(assistant_msg, "tool_calls", None))

    if not has_tool_calls:
        # No tools requested -> DO NOT send any role:"tool" messages.
        # If the first reply already has content, return it directly.
        first_content = ""
        if assistant_msg:
            if hasattr(assistant_msg, "model_dump"):
                first_content = assistant_msg.model_dump().get("content") or ""
            else:
                first_content = (assistant_msg.get("content") if isinstance(assistant_msg, dict) else "") or ""

        if first_content and str(first_content).strip():
            return first_content

        # Otherwise, compose a minimal local answer (no second API call).
        # Pick the top title (if any) and include its local summary.
        local_title = (titles[0] if titles else "").strip()
        full_summary = get_summary_by_title(local_title) if local_title else "No matching titles in local summaries."
        rationale = "Picked based on highest similarity in the RAG context."
        return f"- **Title:** {local_title or 'Unknown'}\n- {rationale}\n- {full_summary}"

    # ---------- Stage 1.5: Execute any/all tool calls locally ----------
    tool_msgs: List[Dict[str, Any]] = []
    chosen_title = ""
    for tc in assistant_msg.tool_calls:
        if tc.type != "function":
            continue
        fn_name = getattr(tc.function, "name", "")
        args = _safe_json_loads(getattr(tc.function, "arguments", "") or "{}")
        if fn_name == "get_summary_by_title":
            chosen_title = (args.get("title") or "").strip()
        result_text = _execute_tool_call(fn_name, args)
        tool_msgs.append({
            "role": "tool",
            "tool_call_id": tc.id,  # IMPORTANT: must match the assistant's tool_call id
            "content": result_text
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
        ),
    }

    # Normalize assistant message
    if hasattr(assistant_msg, "model_dump"):
        assistant_payload = assistant_msg.model_dump()
    else:
        assistant_payload = assistant_msg if isinstance(assistant_msg, dict) else {"role": "assistant", "content": ""}

    second_messages: List[Dict[str, Any]] = [
        compose_system,
        messages[1],  # original user+context message
        assistant_payload,  # assistant message that requested the tools
        *tool_msgs  # tool outputs with matching tool_call_id(s)
    ]

    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=second_messages,
        temperature=temp,
        max_tokens=max_tokens,
    )

    final_choice = (final.choices or [None])[0]
    final_text = ""
    if final_choice and getattr(final_choice, "message", None):
        if hasattr(final_choice.message, "model_dump"):
            final_text = final_choice.message.model_dump().get("content") or ""
        else:
            final_text = getattr(final_choice.message, "content", "") or ""

    if not final_text or not str(final_text).strip():
        # Defensive fallback
        full_summary = tool_msgs[0]["content"] if tool_msgs else "No tool result."
        rationale = "Picked based on highest similarity and thematic match in the RAG context."
        return f"- **Title:** {chosen_title or 'Unknown'}\n- {rationale}\n- {full_summary}"

    return final_text

