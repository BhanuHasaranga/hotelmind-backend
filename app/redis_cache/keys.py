DASHBOARD_OCCUPANCY = "dashboard:occupancy"
DASHBOARD_REVENUE = "dashboard:revenue"
DASHBOARD_BOOKING_COUNT = "dashboard:booking_count"
DASHBOARD_RESTAURANT_SALES = "dashboard:restaurant_sales"
DASHBOARD_SUMMARY = "dashboard:summary"

DASHBOARD_UPDATES_CHANNEL = "dashboard:updates"


def forecast_key(forecast_type: str, branch_id: str) -> str:
    return f"dashboard:forecast:{forecast_type}:{branch_id}"


def ai_insight_key(insight_id: str) -> str:
    return f"dashboard:ai_insight:{insight_id}"


def event_seen_key(event_id: str) -> str:
    return f"event:seen:{event_id}"


def summary_key(branch_id: str) -> str:
    return f"{DASHBOARD_SUMMARY}:{branch_id}"


def occupancy_key(branch_id: str) -> str:
    return f"{DASHBOARD_OCCUPANCY}:{branch_id}"


def revenue_key(branch_id: str) -> str:
    return f"{DASHBOARD_REVENUE}:{branch_id}"


def booking_count_key(branch_id: str) -> str:
    return f"{DASHBOARD_BOOKING_COUNT}:{branch_id}"


def restaurant_sales_key(branch_id: str) -> str:
    return f"{DASHBOARD_RESTAURANT_SALES}:{branch_id}"
