"""Income / expense transactions with month, category and account filters."""
from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..forms import TransactionForm
from ..models import Account, Transaction, categories_for, owned_or_404
from ..utils import month_bounds, parse_month

bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def _fill_choices(form, user_id):
    accounts = db.session.execute(
        db.select(Account).filter_by(user_id=user_id).order_by(Account.name)
    ).scalars().all()
    form.account_id.choices = [(a.id, a.name) for a in accounts]
    form.category_id.choices = [
        (c.id, f"{c.name} ({c.kind})") for c in categories_for(user_id)
    ]
    return accounts


def filtered_query(user_id, args):
    """Build the transaction query for the current user from ?month=&category=&account=."""
    stmt = (db.select(Transaction)
            .options(joinedload(Transaction.category), joinedload(Transaction.account))  # avoid N+1
            .filter(Transaction.user_id == user_id))
    month = args.get("month")
    if month:
        start, end = month_bounds(*parse_month(month))
        stmt = stmt.filter(Transaction.date >= start, Transaction.date < end)
    if args.get("category", type=int):
        stmt = stmt.filter(Transaction.category_id == args.get("category", type=int))
    if args.get("account", type=int):
        stmt = stmt.filter(Transaction.account_id == args.get("account", type=int))
    return stmt.order_by(Transaction.date.desc(), Transaction.id.desc())


@bp.route("/")
@login_required
def index():
    page = db.paginate(
        filtered_query(current_user.id, request.args),
        page=request.args.get("page", 1, type=int),
        per_page=current_app.config["TRANSACTIONS_PER_PAGE"],
        error_out=False,
    )
    accounts = db.session.execute(
        db.select(Account).filter_by(user_id=current_user.id).order_by(Account.name)
    ).scalars().all()
    return render_template(
        "transactions/index.html", page=page, accounts=accounts,
        categories=categories_for(current_user.id), filters=request.args,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = TransactionForm(current_user.id)
    if not _fill_choices(form, current_user.id):
        flash("Create an account first.", "info")
        return redirect(url_for("accounts.create"))
    if form.validate_on_submit():
        txn = Transaction(user_id=current_user.id)
        form.populate_obj(txn)
        db.session.add(txn)
        db.session.commit()
        flash("Transaction added.", "success")
        return redirect(url_for("transactions.index"))
    return render_template("transactions/form.html", form=form, title="New transaction")


@bp.route("/<int:txn_id>/edit", methods=["GET", "POST"])
@login_required
def edit(txn_id):
    txn = owned_or_404(Transaction, txn_id, current_user.id)
    form = TransactionForm(current_user.id, obj=txn)
    _fill_choices(form, current_user.id)
    if form.validate_on_submit():
        form.populate_obj(txn)
        txn.user_id = current_user.id  # never let a form change the owner
        db.session.commit()
        flash("Transaction updated.", "success")
        return redirect(url_for("transactions.index"))
    return render_template("transactions/form.html", form=form, title="Edit transaction")


@bp.route("/<int:txn_id>/delete", methods=["POST"])
@login_required
def delete(txn_id):
    txn = owned_or_404(Transaction, txn_id, current_user.id)
    db.session.delete(txn)
    db.session.commit()
    flash("Transaction deleted.", "success")
    return redirect(url_for("transactions.index"))
