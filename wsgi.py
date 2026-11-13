"""WSGI entry point used by gunicorn (wsgi:app) and by `flask` CLI (FLASK_APP=wsgi.py)."""
from dotenv import load_dotenv

load_dotenv()  # reads .env for local development if present (no-op in containers)

from app import create_app  # noqa: E402

app = create_app()
