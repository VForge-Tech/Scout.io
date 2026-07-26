from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid4()))
        span_id = str(uuid4())[:16]

        request.state.trace_id = trace_id
        request.state.span_id = span_id

        response: Response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        return response


def setup_tracing(app: FastAPI):
    app.add_middleware(TracingMiddleware)
