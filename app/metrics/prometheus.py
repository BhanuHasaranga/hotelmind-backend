from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

registry = CollectorRegistry()

events_produced_total = Counter(
    "events_produced_total",
    "Total number of events published to Kafka",
    ["topic", "event_type"],
    registry=registry,
)

events_consumed_total = Counter(
    "events_consumed_total",
    "Total number of events consumed from Kafka",
    ["topic", "consumer"],
    registry=registry,
)

consumer_errors_total = Counter(
    "consumer_errors_total",
    "Total number of consumer processing errors",
    ["topic", "consumer"],
    registry=registry,
)

consumer_retry_total = Counter(
    "consumer_retry_total",
    "Total number of consumer message retries",
    ["topic", "consumer"],
    registry=registry,
)

consumer_lag = Gauge(
    "consumer_lag",
    "Approximate consumer lag (messages behind)",
    ["topic", "consumer"],
    registry=registry,
)

consumer_processing_seconds = Histogram(
    "consumer_processing_seconds",
    "Time spent processing a single message",
    ["topic", "consumer"],
    registry=registry,
)

redis_cache_hits = Counter(
    "redis_cache_hits_total",
    "Total number of Redis cache hits",
    ["key_prefix"],
    registry=registry,
)

redis_cache_misses = Counter(
    "redis_cache_misses_total",
    "Total number of Redis cache misses",
    ["key_prefix"],
    registry=registry,
)

websocket_connections = Gauge(
    "websocket_connections",
    "Current number of connected WebSocket clients",
    registry=registry,
)

messages_sent = Counter(
    "websocket_messages_sent_total",
    "Total number of WebSocket messages broadcast",
    registry=registry,
)
