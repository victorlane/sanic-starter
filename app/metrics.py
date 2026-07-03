"""Optional Prometheus metrics.

Toggle with the ``METRICS_ENABLED`` env var: set it truthy and a ``/metrics``
endpoint is exposed with request count/latency (and memory) metrics; leave it
unset and this module is inert (the ``sanic_prometheus`` package is never
imported). Install the dependency with:  uv sync --extra metrics

``METRICS_PER_WORKER`` (default: true) additionally records per-worker
request count/latency series (``sanic_worker_request_*``, labeled with the
Sanic worker name) so you can deep-dive into a specific worker on top of the
aggregates. When running multiple workers, point ``PROMETHEUS_MULTIPROC_DIR``
at an empty directory so the workers' metrics are aggregated.

Usage (in the app factory)::

    from app.metrics import install_metrics
    install_metrics(app)  # no-op unless METRICS_ENABLED is set
"""

from __future__ import annotations

from os import getenv

from sanic import Sanic
from sanic.log import logger


def install_metrics(app: Sanic) -> None:
    """Expose Prometheus metrics iff ``METRICS_ENABLED`` is configured.

    Safe to call unconditionally: without ``METRICS_ENABLED`` it does nothing
    and the ``sanic_prometheus`` package is never imported.
    """
    if not _bool(getenv("METRICS_ENABLED"), False):
        return

    try:
        from sanic_prometheus import monitor
    except ImportError:
        logger.warning(
            "METRICS_ENABLED is set but sanic-prometheus is not installed; "
            "run `uv sync --extra metrics` to enable the /metrics endpoint"
        )
        return

    monitor(
        app,
        per_worker_metrics=_bool(getenv("METRICS_PER_WORKER"), True),
    ).expose_endpoint()


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")
