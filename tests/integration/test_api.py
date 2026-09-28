from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.common.db.models import Prediction, PredictionDriver
from packages.common.db.session import get_db


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_prediction(db) -> Prediction:
    prediction = Prediction(
        created_at=datetime(2026, 6, 5, 21, 0, tzinfo=UTC),
        target_time=datetime(2026, 6, 8, 21, 0, tzinfo=UTC),
        horizon="weekend_to_monday_close",
        symbol="XAUUSD",
        regime="RATES_DOMINATED_BEARISH",
        probabilities={},
        risk_score=82.0,
        bias="bearish",
        confidence=0.74,
        confirmations=["XAUUSD closes below 4235"],
        contradictions=[],
        key_levels={"support": [4235.0], "resistance": [4300.0]},
        event_risks=[],
        invalidation=["real yields reverse lower"],
        model_versions={"calibrated": False},
        feature_snapshot_id=None,
        config_version="v1",
        code_commit=None,
    )
    db.add(prediction)
    db.flush()
    db.add(
        PredictionDriver(
            prediction_id=prediction.id,
            name="rates",
            category="rates",
            contribution=-12.5,
            description="real yields +25bp/5d",
        )
    )
    db.commit()
    db.refresh(prediction)
    return prediction


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prediction_current_not_found(client):
    response = client.get("/prediction/current")
    assert response.status_code == 404


def test_prediction_current_returns_latest(client, db):
    _seed_prediction(db)
    response = client.get("/prediction/current")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "XAUUSD"
    assert body["regime"] == "RATES_DOMINATED_BEARISH"
    assert body["risk_score"] == 82.0
    assert len(body["drivers"]) == 1


def test_prediction_history(client, db):
    _seed_prediction(db)
    response = client.get("/prediction/history")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_prediction_by_id(client, db):
    prediction = _seed_prediction(db)
    response = client.get(f"/prediction/{prediction.id}")
    assert response.status_code == 200
    assert response.json()["id"] == prediction.id


def test_prediction_by_id_not_found(client):
    response = client.get("/prediction/does-not-exist")
    assert response.status_code == 404


def test_regime_current(client, db):
    _seed_prediction(db)
    response = client.get("/regime/current")
    assert response.status_code == 200
    assert response.json()["regime"] == "RATES_DOMINATED_BEARISH"


def test_data_health_empty(client):
    response = client.get("/data/health")
    assert response.status_code == 200
    assert response.json() == []
