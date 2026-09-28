from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.schemas import ModelVersionOut
from packages.common.db.models import ModelVersion
from packages.common.db.session import get_db

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/health", response_model=list[ModelVersionOut])
def get_model_health(db: Session = Depends(get_db)) -> list[ModelVersion]:
    """All registered model versions (plan section 48), most recently trained first.
    At most one has ``status="active"`` -- see packages/models/ensemble.py."""
    stmt = select(ModelVersion).order_by(ModelVersion.trained_at.desc()).limit(50)
    return list(db.execute(stmt).scalars().all())
