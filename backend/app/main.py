from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agreements, approvals, beneficiaries, chat, dev, invoices, rules
from app.config import settings
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Payments Agent API - Blinka Challenge",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat.router)
app.include_router(invoices.router)
app.include_router(approvals.router)
app.include_router(rules.router)
app.include_router(beneficiaries.router)
app.include_router(agreements.router)
app.include_router(dev.router)
