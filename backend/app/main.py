from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cases, auth, ai, evidence, causes

app = FastAPI(title="工会劳动维权 AI 引导系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(evidence.router)
app.include_router(causes.router)

@app.get("/")
def root():
    return {"message": "工会劳动维权 AI 引导系统 API"}

@app.get("/health")
def health():
    return {"status": "healthy"}
