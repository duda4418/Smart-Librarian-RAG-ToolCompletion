from fastapi import APIRouter, HTTPException
from utils import answer_with_rag

openai_router = APIRouter()

@openai_router.post("/api/openai/response")
def get_openai_response(user_query: str):
    if not user_query or not user_query.strip():
        raise HTTPException(status_code=400, detail="user_query parameter is required and cannot be empty.")

    return answer_with_rag(user_query, n=3, k=3, temp=0.2, max_tokens=500, fallback_message=None)