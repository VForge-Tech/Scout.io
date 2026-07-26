import json
import logging
import sys
import uuid
from datetime import datetime, timezone


class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "organization_id"):
            log_entry["organization_id"] = record.organization_id

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    for logger_name in ("uvicorn", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False

    return root_logger


def get_logger(name: str, trace_id: str | None = None, user_id: str | None = None, org_id: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if trace_id:
        logger = logging.LoggerAdapter(logger, {"trace_id": trace_id})
    if user_id:
        logger = logging.LoggerAdapter(logger, {"user_id": user_id})
    if org_id:
        logger = logging.LoggerAdapter(logger, {"organization_id": org_id})
    return logger
