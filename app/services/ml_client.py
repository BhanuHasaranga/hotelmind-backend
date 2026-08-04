import httpx

from app.core.config import settings


class MLServiceError(Exception):
    """Raised when the ML service is unreachable or returns an error.

    Routers map this to 502 so ML downtime degrades the dashboard gracefully
    instead of the request hard-failing with a raw connection error.
    """


class MLClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self._base_url = base_url or settings.ML_BASE_URL
        self._timeout = timeout or settings.ML_REQUEST_TIMEOUT_SECONDS

    async def _post(self, path: str, json: dict) -> dict:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.post(path, json=json)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise MLServiceError(f"ML service returned {exc.response.status_code} for {path}") from exc
        except httpx.HTTPError as exc:
            raise MLServiceError(f"ML service unreachable for {path}: {exc}") from exc

    async def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise MLServiceError(f"ML service returned {exc.response.status_code} for {path}") from exc
        except httpx.HTTPError as exc:
            raise MLServiceError(f"ML service unreachable for {path}: {exc}") from exc

    async def predict_pricing(
        self,
        ml_branch_id: int,
        ml_room_type_id: int,
        date: str,
        current_occupancy_pct: float,
        current_revenue: float,
        revenue_7day_avg: float,
        total_rooms: int,
    ) -> dict:
        return await self._post(
            "/predict/pricing",
            {
                "branch_id": ml_branch_id,
                "room_type_id": ml_room_type_id,
                "date": date,
                "current_occupancy_pct": current_occupancy_pct,
                "current_revenue": current_revenue,
                "revenue_7day_avg": revenue_7day_avg,
                "total_rooms": total_rooms,
            },
        )

    async def predict_occupancy(self, ml_branch_id: int, horizon_days: int | None) -> dict:
        payload = {"branch_id": ml_branch_id}
        if horizon_days is not None:
            payload["horizon_days"] = horizon_days
        return await self._post("/predict/occupancy", payload)

    async def predict_restaurant(
        self,
        ml_branch_id: int,
        date: str,
        recent_total_orders_lag_1: float,
        recent_total_orders_lag_7: float,
        recent_total_orders_rolling_mean_7: float,
        avg_item_value: float,
    ) -> dict:
        return await self._post(
            "/predict/restaurant",
            {
                "branch_id": ml_branch_id,
                "date": date,
                "recent_total_orders_lag_1": recent_total_orders_lag_1,
                "recent_total_orders_lag_7": recent_total_orders_lag_7,
                "recent_total_orders_rolling_mean_7": recent_total_orders_rolling_mean_7,
                "avg_item_value": avg_item_value,
            },
        )

    async def predict_staff(
        self,
        ml_branch_id: int,
        department: str,
        date: str,
        scheduled_employees: int,
        present_employees_lag_7: float,
        present_employees_rolling_mean_7: float,
    ) -> dict:
        return await self._post(
            "/predict/staff",
            {
                "branch_id": ml_branch_id,
                "department": department,
                "date": date,
                "scheduled_employees": scheduled_employees,
                "present_employees_lag_7": present_employees_lag_7,
                "present_employees_rolling_mean_7": present_employees_rolling_mean_7,
            },
        )

    async def predict_churn(self, guest_id: str) -> dict:
        return await self._post("/predict/churn", {"guest_id": guest_id})

    async def rag_query(self, query: str, persona: str, session_id: str | None) -> dict:
        return await self._post(
            "/rag/query",
            {"query": query, "persona": persona, "session_id": session_id, "stream": False},
        )

    async def get_insights(self, category: str | None = None, min_severity: str | None = None) -> dict:
        params = {k: v for k, v in {"category": category, "min_severity": min_severity}.items() if v is not None}
        return await self._get("/insights", params=params)

    async def get_executive_insights(self) -> dict:
        return await self._get("/insights/executive")

    async def get_insight_recommendations(self) -> dict:
        return await self._get("/insights/recommendations")

    async def get_anomalies(self) -> dict:
        return await self._get("/insights/anomalies")

    async def get_reviews_summary(self) -> dict:
        return await self._get("/reviews/summary")

    async def get_reviews_topics(self) -> dict:
        return await self._get("/reviews/topics")

    async def get_reviews_complaints(self) -> dict:
        return await self._get("/reviews/complaints")

    async def get_reviews_trends(self, grain: str = "weekly") -> dict:
        return await self._get("/reviews/trends", params={"grain": grain})
