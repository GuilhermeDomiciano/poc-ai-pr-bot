import queue
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any, Callable


_MAX_HISTORY_PER_REQUEST = 300
_SUBSCRIBER_QUEUE_SIZE = 500
_HISTORY_TTL_SECONDS = 60 * 30

_lock = Lock()
_history_by_request_id: dict[str, deque[dict[str, Any]]] = {}
_last_seen_by_request_id: dict[str, float] = {}
_subscribers_by_request_id: dict[str, list[queue.Queue[dict[str, Any]]]] = defaultdict(list)


def _cleanup_expired_requests(now: float) -> None:
    expired_request_ids = []
    for request_id, last_seen in _last_seen_by_request_id.items():
        has_subscribers = bool(_subscribers_by_request_id.get(request_id))
        if has_subscribers:
            continue
        if now - last_seen > _HISTORY_TTL_SECONDS:
            expired_request_ids.append(request_id)

    for request_id in expired_request_ids:
        _history_by_request_id.pop(request_id, None)
        _last_seen_by_request_id.pop(request_id, None)
        _subscribers_by_request_id.pop(request_id, None)


def publish_runtime_event(event_payload: dict[str, Any]) -> None:
    request_id = event_payload.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        return

    now = time.time()
    with _lock:
        _cleanup_expired_requests(now)

        history = _history_by_request_id.setdefault(
            request_id,
            deque(maxlen=_MAX_HISTORY_PER_REQUEST),
        )
        history.append(event_payload)
        _last_seen_by_request_id[request_id] = now

        subscribers = list(_subscribers_by_request_id.get(request_id, []))

    for subscriber_queue in subscribers:
        try:
            subscriber_queue.put_nowait(event_payload)
        except queue.Full:
            continue


def subscribe_request_events(
    request_id: str,
) -> tuple[queue.Queue[dict[str, Any]], list[dict[str, Any]], Callable[[], None]]:
    subscriber_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=_SUBSCRIBER_QUEUE_SIZE)
    now = time.time()

    with _lock:
        _cleanup_expired_requests(now)
        _subscribers_by_request_id[request_id].append(subscriber_queue)
        history_snapshot = list(_history_by_request_id.get(request_id, []))
        _last_seen_by_request_id[request_id] = now

    def unsubscribe() -> None:
        with _lock:
            subscribers = _subscribers_by_request_id.get(request_id)
            if not subscribers:
                return
            if subscriber_queue in subscribers:
                subscribers.remove(subscriber_queue)
            if not subscribers:
                _subscribers_by_request_id.pop(request_id, None)
                _last_seen_by_request_id[request_id] = time.time()

    return subscriber_queue, history_snapshot, unsubscribe
