"""Shared pytest fixtures: a fresh app + in-memory SQLite DB for every test."""
from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import Account, Category, Transaction, User, ensure_default_categories


@pytest.fixture
def app():
    app = create_app("testing")  # SQLite in-memory, CSRF disabled
    with app.app_context():
        db.create_all()
        ensure_default_categories()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(username="alice", password="Secret@123"):
    user = User(username=username, email=f"{username}@example.com")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def make_account(user, name="Main Bank", acc_type="bank", opening=1000):
    acc = Account(user_id=user.id, name=name, type=acc_type, opening_balance=opening)
    db.session.add(acc)
    db.session.commit()
    return acc


def category(name):
    return db.session.execute(db.select(Category).filter_by(name=name, user_id=None)).scalar_one()


def make_txn(user, account, cat_name="Food", amount="100.00", kind="expense", day=None, mode="upi"):
    txn = Transaction(user_id=user.id, account_id=account.id, category_id=category(cat_name).id,
                      type=kind, amount=Decimal(amount), date=day or date.today(),
                      payment_mode=mode, note="test")
    db.session.add(txn)
    db.session.commit()
    return txn


def login(client, username="alice", password="Secret@123"):
    return client.post("/auth/login", data={"username": username, "password": password})


@pytest.fixture
def user(app):
    return make_user()


@pytest.fixture
def account(user):
    return make_account(user)


@pytest.fixture
def auth_client(client, user):
    """A test client already logged in as 'alice'."""
    login(client)
    return client
