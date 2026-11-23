
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router


app = FastAPI(
    title="Enterprise RAG Knowledge Assistant",
    description=(
        "Enterprise document retrieval and "
        "AI-powered question answering"
    ),
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Enterprise RAG Knowledge Assistant API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(rag_router)
