"""Database models. Every user-owned row carries user_id so queries can be scoped."""
from datetime import datetime, timezone

from flask import abort
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ACCOUNT_TYPES = ["bank", "cash", "credit_card", "debit_card", "upi"]
TRANSACTION_TYPES = ["income", "expense"]
PAYMENT_MODES = ["bank", "cash", "card", "upi"]

DEFAULT_CATEGORIES = [
    ("Food", "expense"), ("Transport", "expense"), ("Rent", "expense"),
    ("Shopping", "expense"), ("Bills", "expense"), ("Health", "expense"),
    ("Entertainment", "expense"), ("Education", "expense"),
    ("Salary", "income"), ("Freelance", "income"), ("Other", "expense"),
]


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Account(db.Model):
    __tablename__ = "accounts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    opening_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    # NULL user_id = a default category shared by everyone
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # expense | income


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    type = db.Column(db.String(10), nullable=False)  # income | expense
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    payment_mode = db.Column(db.String(10), nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    account = db.relationship("Account")
    category = db.relationship("Category")

    # Dashboard and filters always query "this user's transactions in a date range"
    __table_args__ = (db.Index("ix_transactions_user_date", "user_id", "date"),)


class Budget(db.Model):
    __tablename__ = "budgets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    period = db.Column(db.String(7), nullable=False)  # YYYY-MM

    category = db.relationship("Category")

    __table_args__ = (
        db.UniqueConstraint("user_id", "category_id", "period", name="uq_budget_user_cat_period"),
    )


# ---------- helpers ----------

def owned_or_404(model, obj_id, user_id):
    """Fetch a row only if it belongs to user_id. Another user's id gives 404, never 403,
    so we don't even reveal that the row exists."""
    obj = db.session.execute(
        db.select(model).filter_by(id=obj_id, user_id=user_id)
    ).scalar_one_or_none()
    if obj is None:
        abort(404)
    return obj


def ensure_default_categories():
    """Insert the shared default categories once (idempotent)."""
    exists = db.session.execute(
        db.select(Category.id).filter(Category.user_id.is_(None)).limit(1)
    ).first()
    if not exists:
        db.session.add_all(Category(name=n, kind=k, user_id=None) for n, k in DEFAULT_CATEGORIES)
        db.session.commit()


def categories_for(user_id, kind=None):
    """Default categories + the user's own ones."""
    stmt = db.select(Category).filter(
        db.or_(Category.user_id.is_(None), Category.user_id == user_id)
    )
    if kind:
        stmt = stmt.filter(Category.kind == kind)
    return db.session.execute(stmt.order_by(Category.kind, Category.name)).scalars().all()
