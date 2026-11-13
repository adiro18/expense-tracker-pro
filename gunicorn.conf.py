"""Gunicorn picks this file up automatically from the working directory (/app).

It only exists to make Prometheus metrics correct with several workers: each worker
writes its counters to a shared directory and /metrics merges them.
Bind address / workers / timeout are given on the command line (see Dockerfile CMD).
"""
import os
import shutil

MULTIPROC_DIR = os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/spendwise-metrics")


def on_starting(server):
    # Start every container with a clean metrics directory
    shutil.rmtree(MULTIPROC_DIR, ignore_errors=True)
    os.makedirs(MULTIPROC_DIR, exist_ok=True)


def child_exit(server, worker):
    from prometheus_client import multiprocess
    multiprocess.mark_process_dead(worker.pid)
