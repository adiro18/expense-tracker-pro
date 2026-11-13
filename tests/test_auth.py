from app.extensions import db
from app.models import User

from .conftest import login


def test_register_creates_user_and_logs_in(client, app):
    resp = client.post("/auth/register", data={
        "username": "bob", "email": "Bob@Example.com", "password": "Password1", "confirm": "Password1",
    })
    assert resp.status_code == 302
    assert "/accounts/new" in resp.headers["Location"]
    user = db.session.execute(db.select(User).filter_by(username="bob")).scalar_one()
    assert user.email == "bob@example.com"
    assert user.password_hash != "Password1"  # stored hashed
    assert client.get("/").status_code == 200  # logged in


def test_register_validation_errors(client):
    resp = client.post("/auth/register", data={
        "username": "x", "email": "not-an-email", "password": "short", "confirm": "different",
    })
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Enter a valid email address." in html
    assert "at least 8 characters" in html
    assert "Passwords must match." in html


def test_register_duplicate_username_and_email(client, user):
    resp = client.post("/auth/register", data={
        "username": "alice", "email": "new@example.com", "password": "Password1", "confirm": "Password1"})
    assert "That username is taken." in resp.get_data(as_text=True)
    resp = client.post("/auth/register", data={
        "username": "alice2", "email": "alice@example.com", "password": "Password1", "confirm": "Password1"})
    assert "already registered" in resp.get_data(as_text=True)


def test_login_success_and_logout(client, user):
    resp = login(client)
    assert resp.status_code == 302
    assert client.get("/").status_code == 200
    resp = client.post("/auth/logout")
    assert resp.status_code == 302
    # after logout the dashboard redirects to the login page
    resp = client.get("/")
    assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_login_wrong_password(client, user):
    resp = login(client, password="wrong-password")
    assert resp.status_code == 200
    assert "Invalid username or password." in resp.get_data(as_text=True)
    assert client.get("/").status_code == 302


def test_login_redirects_to_safe_next_only(client, user):
    resp = client.post("/auth/login?next=/budgets/", data={"username": "alice", "password": "Secret@123"})
    assert resp.headers["Location"].endswith("/budgets/")
    client.post("/auth/logout")
    resp = client.post("/auth/login?next=https://evil.example.com/",
                       data={"username": "alice", "password": "Secret@123"})
    assert "evil" not in resp.headers["Location"]


def test_authenticated_user_skips_login_and_register(auth_client):
    assert auth_client.get("/auth/login").status_code == 302
    assert auth_client.get("/auth/register").status_code == 302


def test_login_rate_limited(client, user):
    for _ in range(5):
        assert login(client, password="bad").status_code == 200
    resp = login(client, password="bad")
    assert resp.status_code == 429
    assert "Too many requests" in resp.get_data(as_text=True)


def test_protected_pages_require_login(client):
    for url in ["/", "/transactions/", "/accounts/", "/budgets/", "/reports/transactions.csv"]:
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]
