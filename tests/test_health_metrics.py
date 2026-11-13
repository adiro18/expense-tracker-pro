from unittest.mock import patch

from sqlalchemy.exc import OperationalError


def test_live(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200 and resp.get_json() == {"status": "alive"}


def test_ready(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200 and resp.get_json() == {"status": "ready"}


def test_ready_returns_503_when_db_down(client):
    # Simulate the database being unreachable
    with patch("app.health.db.session.execute",
               side_effect=OperationalError("SELECT 1", {}, Exception("connection refused"))):
        resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "unavailable"


def test_metrics_endpoint(client):
    client.get("/health/live")
    client.get("/does-not-exist")
    resp = client.get("/metrics")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    assert "http_requests_total" in body
    assert 'endpoint="health.live",method="GET",status="200"' in body
    assert 'endpoint="unmatched",method="GET",status="404"' in body
    assert "http_request_duration_seconds_bucket" in body
    assert 'endpoint="metrics"' not in body  # scrapes are not counted


def test_metrics_multiprocess_mode(client, tmp_path, monkeypatch):
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_error_pages(client):
    resp = client.get("/nope")
    assert resp.status_code == 404 and "Not found" in resp.get_data(as_text=True)
