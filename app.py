import csv
import io
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-before-deployment'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spendly.db'

db = SQLAlchemy(app)

CATEGORIES = [
    'Food & Dining',
    'Transport',
    'Bills & Utilities',
    'Health',
    'Shopping',
    'Entertainment',
    'Education',
    'Other',
]


# ------------------------------------------------------------------ #
# Models                                                              #
# ------------------------------------------------------------------ #

class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    expenses      = db.relationship('Expense', backref='owner', lazy=True,
                                    cascade='all, delete-orphan')


class Expense(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount      = db.Column(db.Float, nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def prev_month(month, year):
    if month == 1:
        return 12, year - 1
    return month - 1, year


def next_month(month, year):
    if month == 12:
        return 1, year + 1
    return month + 1, year


def days_in_month(month, year):
    nm, ny = next_month(month, year)
    return (date(ny, nm, 1) - date(year, month, 1)).days


# ------------------------------------------------------------------ #
# Auth routes                                                         #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        if len(password) < 8:
            return render_template("register.html",
                                   error="Password must be at least 8 characters.")

        if User.query.filter_by(email=email).first():
            return render_template("register.html",
                                   error="An account with that email already exists.")

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        session["user_id"]   = user.id
        session["user_name"] = user.name
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return render_template("login.html",
                                   error="Incorrect email or password.")

        session["user_id"]   = user.id
        session["user_name"] = user.name
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    return redirect(url_for("dashboard"))


# ------------------------------------------------------------------ #
# Dashboard                                                           #
# ------------------------------------------------------------------ #

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today   = date.today()

    # Resolve selected month from query params, default to current month
    try:
        month = int(request.args.get("month", today.month))
        year  = int(request.args.get("year",  today.year))
        # Clamp: no future months
        if date(year, month, 1) > today.replace(day=1):
            month, year = today.month, today.year
        selected = date(year, month, 1)
    except (ValueError, TypeError):
        return redirect(url_for("dashboard"))

    first_of_month = date(year, month, 1)
    nm, ny = next_month(month, year)
    last_of_month  = date(ny, nm, 1) - timedelta(days=1)

    # Expenses for the selected month
    monthly_expenses = (Expense.query
                        .filter_by(user_id=user_id)
                        .filter(Expense.date >= first_of_month,
                                Expense.date <= last_of_month)
                        .order_by(Expense.date.desc(), Expense.id.desc())
                        .all())

    total             = sum(e.amount for e in monthly_expenses)
    transaction_count = len(monthly_expenses)

    is_current = (year == today.year and month == today.month)
    elapsed    = today.day if is_current else days_in_month(month, year)
    daily_avg  = total / max(elapsed, 1)

    cat_totals = {}
    for e in monthly_expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

    top_category      = max(cat_totals, key=cat_totals.get) if cat_totals else "—"
    sorted_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    max_cat_amount    = sorted_categories[0][1] if sorted_categories else 1

    pm, py = prev_month(month, year)

    return render_template(
        "dashboard.html",
        expenses=monthly_expenses,
        total_this_month=total,
        transaction_count=transaction_count,
        top_category=top_category,
        daily_average=daily_avg,
        sorted_categories=sorted_categories,
        max_cat_amount=max_cat_amount,
        categories=CATEGORIES,
        today=today,
        selected=selected,
        is_current=is_current,
        prev_month=pm, prev_year=py,
        next_month=nm, next_year=ny,
    )


# ------------------------------------------------------------------ #
# Expense routes                                                      #
# ------------------------------------------------------------------ #

@app.route("/expenses/add", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    amount      = float(request.form["amount"])
    category    = request.form["category"]
    exp_date    = date.fromisoformat(request.form["date"])
    description = request.form["description"].strip()

    expense = Expense(
        user_id=session["user_id"],
        amount=amount,
        category=category,
        date=exp_date,
        description=description,
    )
    db.session.add(expense)
    db.session.commit()
    flash("Expense added successfully.", "success")
    return redirect(url_for("dashboard",
                            month=exp_date.month, year=exp_date.year))


@app.route("/expenses/<int:id>/edit", methods=["POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = db.get_or_404(Expense, id)
    if expense.user_id != session["user_id"]:
        return "Forbidden", 403

    expense.amount      = float(request.form["amount"])
    expense.category    = request.form["category"]
    expense.date        = date.fromisoformat(request.form["date"])
    expense.description = request.form["description"].strip()
    db.session.commit()

    flash("Expense updated.", "success")
    return redirect(url_for("dashboard",
                            month=expense.date.month, year=expense.date.year))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = db.get_or_404(Expense, id)
    if expense.user_id != session["user_id"]:
        return "Forbidden", 403

    exp_month, exp_year = expense.date.month, expense.date.year
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("dashboard", month=exp_month, year=exp_year))


@app.route("/expenses/export")
def export_expenses():
    if "user_id" not in session:
        return redirect(url_for("login"))

    expenses = (Expense.query
                .filter_by(user_id=session["user_id"])
                .order_by(Expense.date.desc(), Expense.id.desc())
                .all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Amount (€)"])
    for e in expenses:
        writer.writerow([e.date.strftime("%Y-%m-%d"), e.description,
                         e.category, f"{e.amount:.2f}"])

    filename = f"spendly_expenses_{date.today()}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
