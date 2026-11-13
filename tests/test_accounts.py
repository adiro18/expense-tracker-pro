from decimal import Decimal

from app.accounts import account_balances
from app.extensions import db
from app.models import Account

from .conftest import make_account, make_txn, make_user


def test_create_account(auth_client, user):
    resp = auth_client.post("/accounts/new", data={"name": "Cash", "type": "cash", "opening_balance": "500"})
    assert resp.status_code == 302
    acc = db.session.execute(db.select(Account).filter_by(user_id=user.id)).scalar_one()
    assert acc.name == "Cash" and acc.opening_balance == Decimal("500.00")


def test_create_account_requires_name(auth_client):
    resp = auth_client.post("/accounts/new", data={"name": "", "type": "bank"})
    assert resp.status_code == 200
    assert "This field is required." in resp.get_data(as_text=True)


def test_list_accounts_shows_balance(auth_client, user, account):
    make_txn(user, account, "Food", "200", "expense")
    make_txn(user, account, "Salary", "1500", "income")
    html = auth_client.get("/accounts/").get_data(as_text=True)
    assert "Main Bank" in html
    assert "₹2,300.00" in html  # 1000 opening + 1500 - 200


def test_account_balances_function(app, user, account):
    make_txn(user, account, "Food", "250.50", "expense")
    [(acc, balance)] = account_balances(user.id)
    assert balance == Decimal("749.50")


def test_edit_account(auth_client, account):
    assert auth_client.get(f"/accounts/{account.id}/edit").status_code == 200
    resp = auth_client.post(f"/accounts/{account.id}/edit",
                            data={"name": "Renamed", "type": "upi", "opening_balance": "10"})
    assert resp.status_code == 302
    assert db.session.get(Account, account.id).name == "Renamed"


def test_delete_account(auth_client, account):
    resp = auth_client.post(f"/accounts/{account.id}/delete")
    assert resp.status_code == 302
    assert db.session.get(Account, account.id) is None


def test_cannot_delete_account_with_transactions(auth_client, user, account):
    make_txn(user, account)
    resp = auth_client.post(f"/accounts/{account.id}/delete", follow_redirects=True)
    assert "has transactions" in resp.get_data(as_text=True)
    assert db.session.get(Account, account.id) is not None


def test_other_users_account_is_404(auth_client):
    other = make_account(make_user("mallory"), name="Mallory Bank")
    assert auth_client.get(f"/accounts/{other.id}/edit").status_code == 404
    assert auth_client.post(f"/accounts/{other.id}/delete").status_code == 404
    assert "Mallory Bank" not in auth_client.get("/accounts/").get_data(as_text=True)
