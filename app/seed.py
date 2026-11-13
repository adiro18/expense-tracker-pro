"""`flask seed` - creates the demo user with realistic data (idempotent)."""
import random
from datetime import date, timedelta
from decimal import Decimal

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Account, Budget, Category, Transaction, User, ensure_default_categories

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo@1234"
TOTAL_TRANSACTIONS = 212
BATCH_SIZE = 50  # commit in small batches to keep memory low on small pods

# category -> (min, max) INR amount, relative weight, typical payment modes
EXPENSE_PROFILE = {
    "Food": (80, 1200, 35, ["upi", "card", "cash"]),
    "Transport": (40, 600, 20, ["upi", "cash"]),
    "Shopping": (300, 4500, 10, ["card", "upi"]),
    "Bills": (300, 2500, 6, ["bank", "upi"]),
    "Health": (150, 2000, 5, ["upi", "card"]),
    "Entertainment": (150, 1500, 8, ["card", "upi"]),
    "Education": (200, 3000, 3, ["bank", "card"]),
    "Other": (50, 800, 5, ["cash", "upi"]),
}
MODE_TO_ACCOUNT = {"bank": "HDFC Savings", "cash": "Cash Wallet",
                   "card": "ICICI Credit Card", "upi": "Paytm UPI"}
NOTES = {"Food": ["Swiggy order", "Groceries", "Lunch", "Cafe"],
         "Transport": ["Uber", "Metro card", "Petrol", "Auto"],
         "Shopping": ["Amazon", "Clothes", "Myntra"],
         "Bills": ["Electricity", "Mobile recharge", "Internet"],
         "Health": ["Pharmacy", "Doctor visit"],
         "Entertainment": ["Movie", "Netflix", "Concert"],
         "Education": ["Online course", "Books"], "Other": ["Gift", "Misc"]}


def create_demo_data(today=None, rng=None):
    """Returns the demo user, or None if it already exists."""
    today = today or date.today()
    rng = rng or random.Random(42)  # fixed seed -> same data every time
    if db.session.execute(db.select(User).filter_by(username=DEMO_USERNAME)).first():
        return None

    ensure_default_categories()
    cats = {c.name: c for c in db.session.execute(
        db.select(Category).filter(Category.user_id.is_(None))).scalars()}

    user = User(username=DEMO_USERNAME, email="demo@spendwise.local")
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()

    accounts = {}
    for name, acc_type, opening in [("HDFC Savings", "bank", 50000), ("Cash Wallet", "cash", 3000),
                                    ("ICICI Credit Card", "credit_card", 0), ("Paytm UPI", "upi", 2000)]:
        accounts[name] = Account(user_id=user.id, name=name, type=acc_type, opening_balance=opening)
    db.session.add_all(accounts.values())
    db.session.flush()

    def txn(kind, cat, amount, day, mode, note):
        return Transaction(user_id=user.id, account_id=accounts[MODE_TO_ACCOUNT[mode]].id,
                           category_id=cats[cat].id, type=kind, amount=Decimal(amount),
                           date=day, payment_mode=mode, note=note)

    # Fixed monthly items for the current month and the 2 previous ones
    start = today - timedelta(days=89)
    fixed = []
    for back in range(3):
        y, m = today.year, today.month - back
        if m <= 0:
            y, m = y - 1, m + 12
        for day_no, kind, cat, amount, mode, note in [
            (1, "income", "Salary", 85000, "bank", "Monthly salary"),
            (5, "expense", "Rent", 18000, "bank", "House rent"),
            (15, "income", "Freelance", rng.choice([6000, 8500, 12000]), "upi", "Freelance project"),
        ]:
            d = date(y, m, day_no)
            if start <= d <= today:
                fixed.append(txn(kind, cat, amount, d, mode, note))
    db.session.add_all(fixed)

    # Random everyday expenses to reach exactly TOTAL_TRANSACTIONS
    names = list(EXPENSE_PROFILE)
    weights = [EXPENSE_PROFILE[n][2] for n in names]
    for i in range(TOTAL_TRANSACTIONS - len(fixed)):
        cat = rng.choices(names, weights)[0]
        low, high, _, modes = EXPENSE_PROFILE[cat]
        amount = Decimal(rng.randint(low * 100, high * 100)) / 100
        day = start + timedelta(days=rng.randint(0, 89))
        db.session.add(txn("expense", cat, amount, day, rng.choice(modes), rng.choice(NOTES[cat])))
        if i % BATCH_SIZE == 0:
            db.session.flush()

    period = today.strftime("%Y-%m")
    for cat, limit in [("Food", 9000), ("Transport", 3500), ("Shopping", 6000),
                       ("Bills", 4000), ("Entertainment", 3000), ("Health", 2500)]:
        db.session.add(Budget(user_id=user.id, category_id=cats[cat].id, amount=limit, period=period))

    db.session.commit()
    return user


@click.command("seed")
@with_appcontext
def seed_command():
    """Create the demo user (demo / Demo@1234) with 212 transactions."""
    user = create_demo_data()
    if user is None:
        click.echo("Demo user already exists - nothing to do.")
    else:
        count = db.session.execute(
            db.select(db.func.count(Transaction.id)).filter_by(user_id=user.id)).scalar()
        click.echo(f"Seeded demo user '{DEMO_USERNAME}' with {count} transactions.")
