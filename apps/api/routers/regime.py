from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.schemas import RegimeOut
from packages.common.db.models import Prediction
from packages.common.db.session import get_db

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/current", response_model=RegimeOut)
def get_current_regime(symbol: str = "XAUUSD", db: Session = Depends(get_db)) -> RegimeOut:
    """Derived from the latest prediction until a dedicated regime feed exists."""
    stmt = (
        select(Prediction)
        .where(Prediction.symbol == symbol)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = db.execute(stmt).scalars().first()
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"no regime data for symbol {symbol!r}")
    return RegimeOut(
        symbol=prediction.symbol,
        as_of=prediction.created_at,
        regime=prediction.regime,
        scores={d.name: d.contribution for d in prediction.drivers},
    )
