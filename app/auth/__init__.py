"""Registration, login (rate-limited) and logout."""
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, limiter
from ..forms import LoginForm, RegisterForm
from ..models import User, ensure_default_categories

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(target):
    """Only allow redirects to paths on this site (prevents open-redirect attacks)."""
    if target and urlparse(target).netloc == "" and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("dashboard.home")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.execute(db.select(User).filter_by(username=form.username.data)).first():
            form.username.errors.append("That username is taken.")
        elif db.session.execute(db.select(User).filter_by(email=form.email.data.lower())).first():
            form.email.errors.append("That email is already registered.")
        else:
            user = User(username=form.username.data, email=form.email.data.lower())
            user.set_password(form.password.data)  # stored as a salted hash, never plain text
            db.session.add(user)
            db.session.commit()
            ensure_default_categories()
            login_user(user)
            flash("Welcome to Spendwise! Start by adding an account.", "success")
            return redirect(url_for("accounts.create"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])  # brute-force protection
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data)
        ).scalar_one_or_none()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(_safe_next(request.args.get("next")))
        # Same message for unknown user and wrong password (don't leak which one)
        flash("Invalid username or password.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
