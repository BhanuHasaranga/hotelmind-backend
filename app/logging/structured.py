import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
event_id_var: ContextVar[str | None] = ContextVar("event_id", default=None)
consumer_var: ContextVar[str | None] = ContextVar("consumer", default=None)
topic_var: ContextVar[str | None] = ContextVar("topic", default=None)
processing_time_var: ContextVar[float | None] = ContextVar("processing_time", default=None)

_CONTEXT_VARS: dict[str, ContextVar] = {
    "trace_id": trace_id_var,
    "correlation_id": correlation_id_var,
    "event_id": event_id_var,
    "consumer": consumer_var,
    "topic": topic_var,
    "processing_time": processing_time_var,
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for name, var in _CONTEXT_VARS.items():
            value = var.get()
            if value is not None:
                payload[name] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)


def bind_context(**kwargs: Any) -> list:
    tokens = []
    for key, value in kwargs.items():
        var = _CONTEXT_VARS.get(key)
        if var is not None:
            tokens.append((var, var.set(value)))
    return tokens


def reset_context(tokens: list) -> None:
    for var, token in tokens:
        var.reset(token)
