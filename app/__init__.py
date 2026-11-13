"""Application factory: create_app() builds a configured Flask app."""
import os

from flask import Flask, render_template

from .config import CONFIGS
from .extensions import csrf, db, limiter, login_manager, migrate
from .metrics import init_metrics
from .utils import CURRENCY_SYMBOLS, format_money


def create_app(config_name=None):
    config_name = config_name or os.environ.get("APP_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])

    if config_name == "production" and not os.environ.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY environment variable is required in production")

    # --- extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)  # protects every POST form; /metrics and /health/* are GET-only
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from . import models  # noqa: F401  (registers models with SQLAlchemy / Alembic)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    # --- blueprints ---
    from .accounts import bp as accounts_bp
    from .auth import bp as auth_bp
    from .budgets import bp as budgets_bp
    from .dashboard import bp as dashboard_bp
    from .health import bp as health_bp
    from .transactions import bp as transactions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(health_bp)

    init_metrics(app)

    # --- CLI: `flask seed` ---
    from .seed import seed_command
    app.cli.add_command(seed_command)

    # --- templates helpers ---
    currency = app.config["DEFAULT_CURRENCY"]

    @app.template_filter("money")
    def money_filter(value):
        return format_money(value, currency)

    @app.context_processor
    def inject_currency():
        return {"currency_symbol": CURRENCY_SYMBOLS.get(currency, currency)}

    # --- error pages ---
    def error_page(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code

    app.register_error_handler(404, lambda e: error_page(404, "Not found", "That page doesn't exist."))
    app.register_error_handler(
        429, lambda e: error_page(429, "Too many requests", f"Slow down - limit is {e.description}."))
    app.register_error_handler(
        500, lambda e: error_page(500, "Server error", "Something went wrong. Please try again."))

    return app
