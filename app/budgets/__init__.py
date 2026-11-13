"""Monthly category budgets with spent-vs-limit progress bars."""
from datetime import date
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..forms import BudgetForm
from ..models import Budget, Transaction, categories_for, owned_or_404
from ..utils import month_bounds, parse_month

bp = Blueprint("budgets", __name__, url_prefix="/budgets")


def budget_progress(user_id, period):
    """For each budget in `period` return spent, remaining, percent and a status."""
    start, end = month_bounds(*parse_month(period))
    spent_by_cat = dict(db.session.execute(
        db.select(Transaction.category_id, func.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id, Transaction.type == "expense",
                Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.category_id)
    ).all())
    budgets = db.session.execute(
        db.select(Budget).filter_by(user_id=user_id, period=period).order_by(Budget.id)
    ).scalars().all()

    rows = []
    for b in budgets:
        limit = Decimal(b.amount)
        spent = Decimal(spent_by_cat.get(b.category_id) or 0)
        percent = float(spent / limit * 100) if limit else 0.0
        status = "over" if percent >= 100 else "warn" if percent >= 75 else "ok"
        rows.append({"budget": b, "spent": spent, "remaining": limit - spent,
                     "percent": round(percent, 1), "status": status})
    return rows


def _fill_choices(form, user_id):
    form.category_id.choices = [(c.id, c.name) for c in categories_for(user_id, kind="expense")]


@bp.route("/")
@login_required
def index():
    year, month = parse_month(request.args.get("month"))
    period = f"{year:04d}-{month:02d}"
    return render_template("budgets/index.html", rows=budget_progress(current_user.id, period),
                           period=period)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = BudgetForm(current_user.id)
    _fill_choices(form, current_user.id)
    if request.method == "GET":
        form.period.data = date.today().strftime("%Y-%m")
    if form.validate_on_submit():
        duplicate = db.session.execute(db.select(Budget).filter_by(
            user_id=current_user.id, category_id=form.category_id.data, period=form.period.data
        )).first()
        if duplicate:
            form.category_id.errors.append("A budget for this category and month already exists.")
        else:
            budget = Budget(user_id=current_user.id)
            form.populate_obj(budget)
            db.session.add(budget)
            db.session.commit()
            flash("Budget created.", "success")
            return redirect(url_for("budgets.index", month=budget.period))
    return render_template("budgets/form.html", form=form, title="New budget")


@bp.route("/<int:budget_id>/edit", methods=["GET", "POST"])
@login_required
def edit(budget_id):
    budget = owned_or_404(Budget, budget_id, current_user.id)
    form = BudgetForm(current_user.id, obj=budget)
    _fill_choices(form, current_user.id)
    if form.validate_on_submit():
        form.populate_obj(budget)
        budget.user_id = current_user.id
        db.session.commit()
        flash("Budget updated.", "success")
        return redirect(url_for("budgets.index", month=budget.period))
    return render_template("budgets/form.html", form=form, title="Edit budget")


@bp.route("/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete(budget_id):
    budget = owned_or_404(Budget, budget_id, current_user.id)
    period = budget.period
    db.session.delete(budget)
    db.session.commit()
    flash("Budget deleted.", "success")
    return redirect(url_for("budgets.index", month=period))
