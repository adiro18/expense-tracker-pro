from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Category, Transaction

from .conftest import category, make_account, make_txn, make_user


def form_data(account, **overrides):
    data = {"type": "expense", "amount": "123.45", "date": date.today().isoformat(),
            "account_id": account.id, "category_id": category("Food").id,
            "payment_mode": "upi", "note": "Lunch"}
    data.update(overrides)
    return data


def test_create_transaction(auth_client, user, account):
    assert auth_client.get("/transactions/new").status_code == 200
    resp = auth_client.post("/transactions/new", data=form_data(account))
    assert resp.status_code == 302
    txn = db.session.execute(db.select(Transaction)).scalar_one()
    assert txn.user_id == user.id and txn.amount == Decimal("123.45")


def test_new_transaction_without_account_redirects(auth_client):
    resp = auth_client.get("/transactions/new")
    assert resp.status_code == 302 and "/accounts/new" in resp.headers["Location"]


def test_negative_amount_rejected(auth_client, account):
    resp = auth_client.post("/transactions/new", data=form_data(account, amount="-50"))
    assert resp.status_code == 200
    assert "Amount must be a positive number." in resp.get_data(as_text=True)
    assert db.session.execute(db.select(Transaction)).first() is None


def test_zero_and_text_amount_rejected(auth_client, account):
    for bad in ["0", "abc"]:
        resp = auth_client.post("/transactions/new", data=form_data(account, amount=bad))
        assert resp.status_code == 200
    assert db.session.execute(db.select(Transaction)).first() is None


def test_future_date_rejected(auth_client, account):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    resp = auth_client.post("/transactions/new", data=form_data(account, date=tomorrow))
    assert "Date cannot be in the future." in resp.get_data(as_text=True)


def test_invalid_date_rejected(auth_client, account):
    resp = auth_client.post("/transactions/new", data=form_data(account, date="2025-13-45"))
    assert "Enter a valid date." in resp.get_data(as_text=True)


def test_category_kind_must_match_type(auth_client, account):
    resp = auth_client.post("/transactions/new", data=form_data(account, category_id=category("Salary").id))
    assert "is an income category" in resp.get_data(as_text=True)


def test_cannot_use_other_users_category_or_account(auth_client, account):
    mallory = make_user("mallory")
    private_cat = Category(user_id=mallory.id, name="Secret", kind="expense")
    db.session.add(private_cat)
    db.session.commit()
    other_acc = make_account(mallory)
    html = auth_client.post("/transactions/new",
                            data=form_data(account, category_id=private_cat.id)).get_data(as_text=True)
    assert "Choose a valid category." in html
    html = auth_client.post("/transactions/new",
                            data=form_data(account, account_id=other_acc.id)).get_data(as_text=True)
    assert "Choose one of your accounts." in html
    html = auth_client.post("/transactions/new",
                            data=form_data(account, category_id=99999)).get_data(as_text=True)
    assert "Choose a valid category." in html


def test_list_and_filters(auth_client, user, account):
    second = make_account(user, name="Wallet", acc_type="cash")
    make_txn(user, account, "Food", "10", day=date(2025, 1, 10))
    make_txn(user, second, "Transport", "20", day=date(2025, 2, 10))
    html = auth_client.get("/transactions/").get_data(as_text=True)
    assert "2 transactions" in html
    assert "1 transaction<" in auth_client.get("/transactions/?month=2025-01").get_data(as_text=True)
    html = auth_client.get(f"/transactions/?category={category('Transport').id}").get_data(as_text=True)
    assert "1 transaction<" in html and "Transport" in html
    html = auth_client.get(f"/transactions/?account={second.id}").get_data(as_text=True)
    assert "1 transaction<" in html


def test_pagination(auth_client, user, account, app):
    app.config["TRANSACTIONS_PER_PAGE"] = 2
    for _ in range(3):
        make_txn(user, account)
    html = auth_client.get("/transactions/").get_data(as_text=True)
    assert "Page 1 of 2" in html and "Next" in html
    assert "Prev" in auth_client.get("/transactions/?page=2").get_data(as_text=True)


def test_edit_transaction(auth_client, user, account):
    txn = make_txn(user, account)
    assert auth_client.get(f"/transactions/{txn.id}/edit").status_code == 200
    resp = auth_client.post(f"/transactions/{txn.id}/edit", data=form_data(account, amount="999.99"))
    assert resp.status_code == 302
    assert db.session.get(Transaction, txn.id).amount == Decimal("999.99")


def test_delete_transaction(auth_client, user, account):
    txn = make_txn(user, account)
    assert auth_client.post(f"/transactions/{txn.id}/delete").status_code == 302
    assert db.session.get(Transaction, txn.id) is None


def test_user_isolation(client, app):
    """User B must not see, edit or delete user A's transaction -> 404."""
    alice = make_user("alice")
    alice_txn = make_txn(alice, make_account(alice), amount="4242.00")
    make_user("bob", "Bob@12345")
    client.post("/auth/login", data={"username": "bob", "password": "Bob@12345"})

    assert "4,242.00" not in client.get("/transactions/").get_data(as_text=True)
    assert client.get(f"/transactions/{alice_txn.id}/edit").status_code == 404
    assert client.post(f"/transactions/{alice_txn.id}/edit", data={"amount": "1"}).status_code == 404
    assert client.post(f"/transactions/{alice_txn.id}/delete").status_code == 404
    assert db.session.get(Transaction, alice_txn.id).amount == Decimal("4242.00")  # unchanged
    assert "4242.00" not in client.get("/reports/transactions.csv").get_data(as_text=True)
