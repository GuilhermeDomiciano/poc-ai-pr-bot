import logging
import os
import time
import uuid
import asyncio
import json
from collections.abc import Awaitable, Callable
from queue import Empty
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response, StreamingResponse

from infrastructure.http.errors import to_http_exception
from infrastructure.http.schemas import RunWorkflowRequest, RunWorkflowResponse
from infrastructure.http.workflow_service import execute_workflow
from infrastructure.observability.context import reset_request_id, set_request_id
from infrastructure.observability.event_stream import subscribe_request_events
from infrastructure.observability.logging_utils import configure_logging, log_event


configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="POC AI PR Bot API")


def _resolve_cors_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def _format_sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.middleware("http")
async def request_observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)

    method = request.method
    path = request.url.path
    start_time = time.perf_counter()
    log_event(logger, logging.INFO, "http.request.start", method=method, path=path)

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_event(
            logger,
            logging.INFO,
            "http.request.end",
            method=method,
            path=path,
            status=status_code,
            duration_ms=f"{duration_ms:.2f}",
        )
        reset_request_id(token)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/workflow/stream/{request_id}")
async def stream_workflow_logs(request_id: str, request: Request) -> StreamingResponse:
    event_queue, history, unsubscribe = subscribe_request_events(request_id)

    async def event_generator():
        try:
            for history_event in history:
                yield _format_sse_data(history_event)

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_payload = await asyncio.to_thread(event_queue.get, True, 15.0)
                except Empty:
                    yield _format_sse_data({"type": "ping"})
                    continue
                yield _format_sse_data(event_payload)
        finally:
            unsubscribe()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/workflow/run", response_model=RunWorkflowResponse, status_code=status.HTTP_200_OK)
def run_workflow(payload: RunWorkflowRequest, request: Request) -> RunWorkflowResponse:
    request_id = getattr(request.state, "request_id", None)
    token = set_request_id(request_id) if request_id else None
    try:
        return execute_workflow(payload)
    except Exception as error:
        log_event(logger, logging.ERROR, "http.workflow.endpoint_failed", error=str(error))
        raise to_http_exception(error)
    finally:
        if token is not None:
            reset_request_id(token)
