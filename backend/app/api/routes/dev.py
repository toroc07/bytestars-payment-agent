import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.seed import reset_database, seed_database
from app.db.session import get_db

router = APIRouter(prefix="/api/dev", tags=["dev"])

_LAST_CALL_BY_IP: dict[str, float] = {}
RATE_LIMIT_SECONDS = 5.0


def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    last = _LAST_CALL_BY_IP.get(ip, 0.0)
    if now - last < RATE_LIMIT_SECONDS:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes a endpoints de demo. Espera unos segundos.")
    _LAST_CALL_BY_IP[ip] = now


@router.post("/seed")
def seed_endpoint(request: Request, db: Session = Depends(get_db)) -> dict[str, int]:
    _check_rate_limit(request)
    loaded = seed_database(db)
    return {"loaded": loaded}


@router.post("/reset")
def reset_endpoint(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    _check_rate_limit(request)
    reset_database(db)
    seed_database(db)
    return {"ok": True}
