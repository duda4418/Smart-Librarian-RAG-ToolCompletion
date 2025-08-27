from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from open_ai.openAI import openai_router
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(openai_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)