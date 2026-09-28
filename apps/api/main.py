from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import data_health, health, model_health, predictions, regime
from packages.common.config import get_settings
from packages.common.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Gold Prediction Model API",
    description="Gold Market Intelligence & Prediction System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(predictions.router)
app.include_router(regime.router)
app.include_router(data_health.router)
app.include_router(model_health.router)
