from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.schemas import PredictionOut
from packages.common.db.models import Prediction
from packages.common.db.session import get_db

router = APIRouter(prefix="/prediction", tags=["predictions"])


@router.get("/current", response_model=PredictionOut)
def get_current_prediction(symbol: str = "XAUUSD", db: Session = Depends(get_db)) -> Prediction:
    stmt = (
        select(Prediction)
        .where(Prediction.symbol == symbol)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = db.execute(stmt).scalars().first()
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"no prediction found for symbol {symbol!r}")
    return prediction


@router.get("/history", response_model=list[PredictionOut])
def get_prediction_history(
    symbol: str = "XAUUSD", limit: int = 50, db: Session = Depends(get_db)
) -> list[Prediction]:
    limit = max(1, min(limit, 500))
    stmt = (
        select(Prediction)
        .where(Prediction.symbol == symbol)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/{prediction_id}", response_model=PredictionOut)
def get_prediction(prediction_id: str, db: Session = Depends(get_db)) -> Prediction:
    prediction = db.get(Prediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"prediction {prediction_id!r} not found")
    return prediction
