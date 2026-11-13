"""Configuration classes. Every setting comes from environment variables (12-factor)."""
import os
from urllib.parse import quote_plus


def build_database_uri():
    """MySQL (via PyMySQL) when DB_HOST is set, otherwise a local SQLite file."""
    host = os.environ.get("DB_HOST", "").strip()
    if not host:
        return "sqlite:///spendwise.db"
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "spendwise")
    user = quote_plus(os.environ.get("DB_USER", ""))
    password = quote_plus(os.environ.get("DB_PASSWORD", ""))
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


class Config:
    # Only a dev fallback - production refuses to start without a real SECRET_KEY
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # pre_ping + recycle avoid "MySQL server has gone away" on idle RDS connections
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "INR")
    # memory:// is per gunicorn worker; point this at redis://... to share limits across workers/pods
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    TRANSACTIONS_PER_PAGE = 25


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
