# Spendly — Personal Expense Tracker

A web app to log, track, and understand your personal spending.
Built with Python (Flask) and SQLite. No frameworks, no complexity.

---

## What it does

- Register and log in securely
- Add expenses with amount, category, date, and description
- View a dashboard with monthly stats and category breakdown
- Browse expenses by month using prev/next navigation
- Edit or delete any expense
- Export all expenses to a CSV (Excel-compatible) file

---

## Tech Stack

| Layer | Technology | What it does |
|---|---|---|
| Language | Python 3 | Runs the backend logic |
| Web framework | Flask | Handles URLs, forms, and templates |
| Database | SQLite | Stores users and expenses in a single file |
| ORM | Flask-SQLAlchemy | Lets us write Python instead of raw SQL |
| Passwords | Werkzeug | Hashes passwords so they're never stored as plain text |
| Frontend | HTML + CSS + Vanilla JS | No React, no frameworks — just plain web |
| Fonts | Google Fonts (DM Sans, DM Serif Display) | Typography |
| Hosting | Render | Free tier, auto-deploys from GitHub |

---

## Project Structure

```
expense-tracker/
│
├── app.py                  # Main file — all routes and logic live here
├── requirements.txt        # Python packages needed to run the app
│
├── templates/              # HTML pages (Jinja2 templates)
│   ├── base.html           # Shared layout — navbar, footer, flash messages
│   ├── landing.html        # Home page (before login)
│   ├── register.html       # Sign up form
│   ├── login.html          # Sign in form
│   ├── dashboard.html      # Main app page (after login)
│   ├── terms.html          # Terms and Conditions page
│   └── privacy.html        # Privacy Policy page
│
├── static/
│   └── css/
│       ├── style.css       # Global styles used on all pages
│       ├── landing.css     # Styles only for the landing page
│       └── dashboard.css   # Styles only for the dashboard
│
└── instance/
    └── spendly.db          # SQLite database file (auto-created, not in GitHub)
```

---

## How Flask Works

Flask is a **web framework** — it listens for requests (someone visiting a URL) and decides what to send back.

```
User visits /dashboard
      ↓
Flask matches it to the dashboard() function in app.py
      ↓
The function fetches expenses from the database
      ↓
Flask fills in dashboard.html with that data
      ↓
The final HTML is sent back to the browser
```

Every URL in the app is defined with `@app.route(...)` above a function in `app.py`.

---

## How the Database Works

The database has two tables:

**user**
```
id | name   | email            | password_hash
1  | Vikram | vikram@gmail.com | scrypt:32768...
```

**expense**
```
id | user_id | amount | category      | date       | description
1  | 1       | 24.50  | Food & Dining | 2026-04-07 | Grocery run
2  | 1       | 8.00   | Transport     | 2026-04-07 | Bus ticket
```

- `user_id` in the expense table links each expense back to the user who created it
- Passwords are never stored as plain text — Werkzeug hashes them before saving
- The database file (`spendly.db`) is created automatically when you first run the app

---

## How Sessions Work

When a user logs in, Flask stores their `user_id` and `user_name` in a **session** (a secure cookie in the browser). This is how the app knows who is logged in across pages.

```python
session["user_id"]   = user.id
session["user_name"] = user.name
```

On logout, the session is cleared:
```python
session.clear()
```

Every protected page checks for the session at the top:
```python
if "user_id" not in session:
    return redirect(url_for("login"))
```

---

## Routes Reference

| Method | URL | What it does |
|---|---|---|
| GET | `/` | Landing page |
| GET | `/register` | Show sign up form |
| POST | `/register` | Create new account |
| GET | `/login` | Show sign in form |
| POST | `/login` | Authenticate user |
| GET | `/logout` | Clear session, go to landing |
| GET | `/dashboard` | Main dashboard (requires login) |
| POST | `/expenses/add` | Save a new expense |
| POST | `/expenses/<id>/edit` | Update an existing expense |
| POST | `/expenses/<id>/delete` | Delete an expense |
| GET | `/expenses/export` | Download all expenses as CSV |
| GET | `/terms` | Terms and Conditions page |
| GET | `/privacy` | Privacy Policy page |

---

## Running Locally

```bash
# 1. Install dependencies
py -m pip install -r requirements.txt

# 2. Start the app
py app.py

# 3. Open in browser
http://localhost:5001
```

The database file is created automatically on first run.

---

## Deploying to Render

1. Push code to GitHub
2. Connect repo on render.com → New Web Service
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variable: `SECRET_KEY` = any long random string
6. Every future `git push` auto-redeploys the app

> **Note:** Render's free tier uses an ephemeral filesystem — the SQLite database resets on every redeploy. Fine for demos; switch to PostgreSQL for a real production app.

---

## Wishlist (not built yet)

- Receipt scanning with GPT-4o vision
- ML spending projection / forecasting
- Budget limits per category
- Charts (pie/donut via Chart.js)
- Account settings (change name, email, password)
- Search and filter expenses
- Persistent database (PostgreSQL)
- Custom 404 page
