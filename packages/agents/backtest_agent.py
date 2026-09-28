"""Agent 8 -- Backtest Agent (plan section 50).

Responsibilities: walk-forward validation, performance reports,
calibration tests, regression tests. Wraps packages.backtesting +
packages.models.train so the orchestrator (and any future scheduled job)
has one entrypoint for "build a dataset and evaluate a candidate model"
without reaching into those modules directly.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from packages.agents.base import AgentResult
from packages.backtesting.dataset import build_dataset, dataset_metadata
from packages.models.train import train_and_register, walk_forward_evaluate


async def evaluate(
    session: Session,
    symbol: str,
    as_of_dates: list[datetime],
    model_type: str,
    *,
    label_col: str = "label_down_5d",
) -> AgentResult:
    """Builds a dataset over `as_of_dates` and walk-forward evaluates
    `model_type` on it, without registering anything."""
    df = build_dataset(session, symbol, as_of_dates)
    metrics = walk_forward_evaluate(df, model_type, label_col=label_col)

    status = "ok" if metrics["folds"] > 0 else "unavailable"
    detail = (
        f"{metrics['folds']} walk-forward fold(s), AUC={metrics['auc']}, Brier={metrics['brier']}"
        if status == "ok"
        else "not enough point-in-time history for a full walk-forward window yet"
    )
    return AgentResult(
        agent="backtest",
        status=status,
        detail=detail,
        data={"dataset": dataset_metadata(df), "metrics": metrics},
    )


async def train(
    session: Session,
    symbol: str,
    as_of_dates: list[datetime],
    model_type: str,
    *,
    name: str,
    label_col: str = "label_down_5d",
) -> AgentResult:
    """Builds a dataset, trains `model_type` on it, and registers it as a
    candidate ModelVersion (never active -- promotion is a separate, deliberate
    decision after a human reviews the metrics, plan section 86)."""
    df = build_dataset(session, symbol, as_of_dates)
    version = train_and_register(session, df, model_type, name=name, label_col=label_col)

    return AgentResult(
        agent="backtest",
        status="ok",
        detail=f"registered candidate model {version.name} ({version.model_type}), id={version.id}",
        data={"model_version_id": version.id, "metrics": version.metrics},
    )
