"""Prometheus telemetry.

Metric names are used verbatim by the Grafana dashboard - do not rename them:
  http_requests_total{endpoint, method, status}
  http_request_duration_seconds{endpoint, method}
"""
import os
import time

from flask import Response, g, request
from prometheus_client import (CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry,
                               Counter, Histogram, generate_latest, multiprocess)

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["endpoint", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["endpoint", "method"]
)


def _start_timer():
    g._start_time = time.perf_counter()


def _record(response):
    if request.path == "/metrics" or not hasattr(g, "_start_time"):
        return response  # don't count Prometheus scraping itself
    # Use the Flask endpoint name (e.g. "transactions.index") rather than the raw path,
    # so /transactions/1, /transactions/2 ... don't create thousands of label values.
    endpoint = request.endpoint or "unmatched"
    REQUEST_LATENCY.labels(endpoint, request.method).observe(time.perf_counter() - g._start_time)
    REQUEST_COUNT.labels(endpoint, request.method, str(response.status_code)).inc()
    return response


def metrics_view():
    # Under gunicorn each worker is a separate process. gunicorn.conf.py sets
    # PROMETHEUS_MULTIPROC_DIR so all workers' counters are merged here.
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)


def init_metrics(app):
    app.before_request(_start_timer)
    app.after_request(_record)
    app.add_url_rule("/metrics", "metrics", metrics_view, methods=["GET"])
