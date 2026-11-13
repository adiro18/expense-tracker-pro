"""Config, utils, seed command and app factory."""
from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.config import build_database_uri
from app.extensions import db
from app.models import Budget, Transaction, User
from app.seed import create_demo_data
from app.utils import format_money, month_bounds, parse_month, shift_month


def test_database_uri_sqlite_fallback(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    assert build_database_uri() == "sqlite:///spendwise.db"


def test_database_uri_mysql(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_USER", "admin")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:word")
    uri = build_database_uri()
    assert uri.startswith("mysql+pymysql://admin:p%40ss%3Aword@db.example.com:3306/spendwise")


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app("production")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    assert create_app("production").config["DEBUG"] is False


def test_utils():
    assert parse_month("2025-02") == (2025, 2)
    assert parse_month("bad", today=date(2024, 6, 1)) == (2024, 6)
    assert month_bounds(2024, 12) == (date(2024, 12, 1), date(2025, 1, 1))
    assert shift_month(2025, 1, -1) == (2024, 12)
    assert format_money(Decimal("1234567.5")) == "₹12,34,567.50"
    assert format_money(-50) == "-₹50.00"
    assert format_money(1234567, "USD") == "$1,234,567.00"


def test_seed_creates_demo_data_and_is_idempotent(app):
    user = create_demo_data(today=date(2025, 3, 20))
    assert user is not None
    count = db.session.execute(
        db.select(db.func.count(Transaction.id)).filter_by(user_id=user.id)).scalar()
    assert count == 212
    assert db.session.execute(db.select(db.func.count(Budget.id))).scalar() == 6
    assert user.check_password("Demo@1234")
    latest = db.session.execute(db.select(db.func.max(Transaction.date))).scalar()
    assert latest <= date(2025, 3, 20)  # nothing in the future
    assert create_demo_data() is None  # second run does nothing
    assert db.session.execute(db.select(db.func.count(User.id))).scalar() == 1


def test_seed_cli_command(app):
    runner = app.test_cli_runner()
    assert "Seeded demo user" in runner.invoke(args=["seed"]).output
    assert "already exists" in runner.invoke(args=["seed"]).output
