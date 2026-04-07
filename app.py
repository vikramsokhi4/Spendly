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
    first_of_month = today.replace(day=1)

    # All expenses newest first
    all_expenses = (Expense.query
                    .filter_by(user_id=user_id)
                    .order_by(Expense.date.desc(), Expense.id.desc())
                    .all())

    monthly = [e for e in all_expenses if e.date >= first_of_month]

    total_this_month  = sum(e.amount for e in monthly)
    transaction_count = len(monthly)
    days_elapsed      = max(today.day, 1)
    daily_average     = total_this_month / days_elapsed

    # Category totals for the month
    cat_totals = {}
    for e in monthly:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

    top_category      = max(cat_totals, key=cat_totals.get) if cat_totals else "—"
    sorted_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    max_cat_amount    = sorted_categories[0][1] if sorted_categories else 1

    return render_template(
        "dashboard.html",
        expenses=all_expenses[:30],
        total_this_month=total_this_month,
        transaction_count=transaction_count,
        top_category=top_category,
        daily_average=daily_average,
        sorted_categories=sorted_categories,
        max_cat_amount=max_cat_amount,
        categories=CATEGORIES,
        today=today,
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
    return redirect(url_for("dashboard"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = db.get_or_404(Expense, id)
    if expense.user_id != session["user_id"]:
        return "Forbidden", 403

    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for("dashboard"))


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
        writer.writerow([e.date.strftime("%Y-%m-%d"), e.description, e.category, f"{e.amount:.2f}"])

    csv_content = output.getvalue()
    filename = f"spendly_expenses_{date.today()}.csv"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming soon"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
