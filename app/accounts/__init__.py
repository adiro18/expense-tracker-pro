"""Accounts (bank, cash, cards, UPI) with live balances."""
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func

from ..extensions import db
from ..forms import AccountForm
from ..models import Account, Transaction, owned_or_404

bp = Blueprint("accounts", __name__, url_prefix="/accounts")


def account_balances(user_id):
    """Opening balance + income - expense, per account, in a single query."""
    signed = case((Transaction.type == "income", Transaction.amount), else_=-Transaction.amount)
    rows = db.session.execute(
        db.select(Account, func.coalesce(func.sum(signed), 0))
        .outerjoin(Transaction, Transaction.account_id == Account.id)
        .filter(Account.user_id == user_id)
        .group_by(Account.id)
        .order_by(Account.name)
    ).all()
    return [(acc, Decimal(acc.opening_balance or 0) + Decimal(delta)) for acc, delta in rows]


@bp.route("/")
@login_required
def index():
    balances = account_balances(current_user.id)
    total = sum((bal for _, bal in balances), Decimal("0"))
    return render_template("accounts/index.html", balances=balances, total=total)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = AccountForm()
    if form.validate_on_submit():
        acc = Account(user_id=current_user.id, name=form.name.data, type=form.type.data,
                      opening_balance=form.opening_balance.data or 0)
        db.session.add(acc)
        db.session.commit()
        flash(f"Account '{acc.name}' created.", "success")
        return redirect(url_for("accounts.index"))
    return render_template("accounts/form.html", form=form, title="New account")


@bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
@login_required
def edit(account_id):
    acc = owned_or_404(Account, account_id, current_user.id)
    form = AccountForm(obj=acc)
    if form.validate_on_submit():
        form.populate_obj(acc)
        acc.opening_balance = form.opening_balance.data or 0
        db.session.commit()
        flash("Account updated.", "success")
        return redirect(url_for("accounts.index"))
    return render_template("accounts/form.html", form=form, title="Edit account")


@bp.route("/<int:account_id>/delete", methods=["POST"])
@login_required
def delete(account_id):
    acc = owned_or_404(Account, account_id, current_user.id)
    in_use = db.session.execute(
        db.select(Transaction.id).filter_by(account_id=acc.id).limit(1)
    ).first()
    if in_use:
        flash("This account has transactions. Delete or move them first.", "warning")
    else:
        db.session.delete(acc)
        db.session.commit()
        flash("Account deleted.", "success")
    return redirect(url_for("accounts.index"))
