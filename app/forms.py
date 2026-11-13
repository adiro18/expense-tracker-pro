"""WTForms classes. Flask-WTF adds a CSRF token to every form automatically."""
from datetime import date
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (BooleanField, DateField, DecimalField, PasswordField,
                     SelectField, StringField, SubmitField)
from wtforms.validators import (DataRequired, EqualTo, Length, NumberRange,
                                Optional, Regexp, ValidationError)

from .extensions import db
from .models import (ACCOUNT_TYPES, PAYMENT_MODES, TRANSACTION_TYPES, Account,
                     Category)

MAX_AMOUNT = Decimal("9999999999.99")  # fits Numeric(12, 2)


def label(value):
    return value.replace("_", " ").title()


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(3, 64),
        Regexp(r"^[A-Za-z0-9_.]+$", message="Letters, numbers, dot and underscore only."),
    ])
    email = StringField("Email", validators=[
        DataRequired(), Length(max=120),
        Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Enter a valid email address."),
    ])
    password = PasswordField("Password", validators=[
        DataRequired(), Length(min=8, message="Password must be at least 8 characters."),
    ])
    confirm = PasswordField("Confirm password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match."),
    ])
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class AccountForm(FlaskForm):
    name = StringField("Account name", validators=[DataRequired(), Length(max=80)])
    type = SelectField("Type", choices=[(t, label(t)) for t in ACCOUNT_TYPES])
    opening_balance = DecimalField("Opening balance", places=2, default=0, validators=[
        Optional(), NumberRange(min=-MAX_AMOUNT, max=MAX_AMOUNT),
    ])
    submit = SubmitField("Save")


class UserScopedForm(FlaskForm):
    """Base form that knows which user is submitting, so it can validate ownership."""

    def __init__(self, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id

    def _check_category(self, category_id, kind=None):
        cat = db.session.get(Category, category_id) if category_id else None
        # Must exist AND be either a default category or the user's own
        if cat is None or cat.user_id not in (None, self.user_id):
            raise ValidationError("Choose a valid category.")
        if kind and cat.kind != kind:
            raise ValidationError(f"'{cat.name}' is an {cat.kind} category.")
        return cat


class TransactionForm(UserScopedForm):
    type = SelectField("Type", choices=[(t, label(t)) for t in TRANSACTION_TYPES])
    amount = DecimalField("Amount", places=2, validators=[
        DataRequired(message="Enter an amount."),
        NumberRange(min=Decimal("0.01"), max=MAX_AMOUNT, message="Amount must be a positive number."),
    ])
    date = DateField("Date", default=date.today, validators=[DataRequired(message="Enter a valid date.")])
    # validate_choice=False: ownership is checked explicitly below with a clear message
    account_id = SelectField("Account", coerce=int, validate_choice=False)
    category_id = SelectField("Category", coerce=int, validate_choice=False)
    payment_mode = SelectField("Payment mode", choices=[(m, label(m)) for m in PAYMENT_MODES])
    note = StringField("Note", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save")

    def validate_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Date cannot be in the future.")

    def validate_account_id(self, field):
        acc = db.session.get(Account, field.data) if field.data else None
        if acc is None or acc.user_id != self.user_id:
            raise ValidationError("Choose one of your accounts.")

    def validate_category_id(self, field):
        self._check_category(field.data, kind=self.type.data)


class BudgetForm(UserScopedForm):
    category_id = SelectField("Category", coerce=int, validate_choice=False)
    amount = DecimalField("Monthly limit", places=2, validators=[
        DataRequired(message="Enter an amount."),
        NumberRange(min=Decimal("0.01"), max=MAX_AMOUNT, message="Amount must be a positive number."),
    ])
    period = StringField("Month (YYYY-MM)", validators=[
        DataRequired(), Regexp(r"^\d{4}-(0[1-9]|1[0-2])$", message="Use the format YYYY-MM."),
    ])
    submit = SubmitField("Save")

    def validate_category_id(self, field):
        self._check_category(field.data, kind="expense")
