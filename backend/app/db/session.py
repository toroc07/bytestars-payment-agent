from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _normalize_db_url(url: str) -> str:
    # SQLAlchemy 2.1 picks psycopg (v3) for a bare "postgresql://", but requirements.txt installs psycopg2.
    # Neon hands out "postgresql://...", Heroku-style URLs use "postgres://": pin both to psycopg2.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


db_url = _normalize_db_url(settings.DATABASE_URL)
connect_args = {"check_same_thread": False, "timeout": 30.0} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)



class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
