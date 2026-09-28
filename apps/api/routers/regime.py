from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.schemas import RegimeOut
from packages.common.db.models import RegimeSnapshot
from packages.common.db.session import get_db

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/current", response_model=RegimeOut)
def get_current_regime(symbol: str = "XAUUSD", db: Session = Depends(get_db)) -> RegimeSnapshot:
    """Latest regime classification (plan section 21), persisted by the Regime
    Agent -- see packages/agents/regime_agent.py."""
    stmt = (
        select(RegimeSnapshot)
        .where(RegimeSnapshot.symbol == symbol)
        .order_by(RegimeSnapshot.as_of.desc())
        .limit(1)
    )
    snapshot = db.execute(stmt).scalars().first()
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"no regime data for symbol {symbol!r}")
    return snapshot
