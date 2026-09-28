from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.schemas import ProviderHealthOut
from packages.common.db.models import ProviderHealth
from packages.common.db.session import get_db

router = APIRouter(prefix="/data", tags=["data-quality"])


@router.get("/health", response_model=list[ProviderHealthOut])
def get_data_health(hours: int = 48, db: Session = Depends(get_db)) -> list[ProviderHealth]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    stmt = (
        select(ProviderHealth)
        .where(ProviderHealth.checked_at >= since)
        .order_by(ProviderHealth.checked_at.desc())
        .limit(500)
    )
    return list(db.execute(stmt).scalars().all())
