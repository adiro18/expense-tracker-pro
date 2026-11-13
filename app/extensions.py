"""Flask extensions are created here (unbound) and attached in create_app()."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
# In-memory storage: limits are per gunicorn worker (fine for a demo; use Redis in real prod)
limiter = Limiter(key_func=get_remote_address, default_limits=[])
