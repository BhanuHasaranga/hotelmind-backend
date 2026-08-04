import json
import logging

from redis.asyncio import Redis

from app.redis_cache.dashboard_cache import publish_dashboard_update
from app.redis_cache.keys import ai_insight_key, forecast_key

logger = logging.getLogger(__name__)

_FORECAST_EVENT_TYPES = {"OccupancyForecastReady", "RestaurantForecastReady", "StaffForecastReady"}


async def handle_ml_event(redis: Redis, event: dict) -> None:
    event_type = event.get("event_type")
    payload = event.get("payload", {})

    if event_type in _FORECAST_EVENT_TYPES:
        branch_id = str(payload.get("branch_id", "global"))
        forecast_type = event_type.replace("Ready", "")
        await redis.set(forecast_key(forecast_type, branch_id), json.dumps(payload, default=str), ex=3600)
        await publish_dashboard_update(
            redis, {"type": "forecast", "forecast_type": forecast_type, "branch_id": branch_id, "data": payload}
        )
    elif event_type == "AIInsightGenerated":
        insight_id = str(payload.get("insight_id"))
        await redis.set(ai_insight_key(insight_id), json.dumps(payload, default=str), ex=86400)
        await publish_dashboard_update(redis, {"type": "ai_insight", "insight_id": insight_id, "data": payload})
    elif event_type == "PriceRecommendationReady":
        await publish_dashboard_update(redis, {"type": "price_recommendation", "data": payload})
    elif event_type == "ChurnPredictionReady":
        await publish_dashboard_update(redis, {"type": "churn_prediction", "data": payload})
