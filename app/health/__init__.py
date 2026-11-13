"""Kubernetes probes.

/health/live  - liveness: the process is up (never touches the DB, so a DB outage
                doesn't make Kubernetes restart healthy pods).
/health/ready - readiness: the DB answers SELECT 1; otherwise 503 and the pod is
                removed from the Service until the DB is back.
"""
from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from ..extensions import db

bp = Blueprint("health", __name__, url_prefix="/health")


@bp.get("/live")
def live():
    return jsonify(status="alive"), 200


@bp.get("/ready")
def ready():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ready"), 200
    except Exception as exc:  # any DB error means "not ready"
        db.session.rollback()
        current_app.logger.warning("Readiness check failed: %s", exc.__class__.__name__)
        return jsonify(status="unavailable", reason="database unreachable"), 503
