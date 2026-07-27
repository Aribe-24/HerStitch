import os
import sqlite3
from datetime import date
from flask import Flask, g, render_template, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "herstitch-secret"

DB_PATH = os.path.join(os.path.dirname(__file__), "herstitch.db")


def get_db():
    db = getattr(g, "db", None)
    if db is None:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        g.db = db
    return db


@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            event_date TEXT NOT NULL,
            details TEXT NOT NULL
        )
        """
    )
    db.commit()

    if db.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"] == 0:
        sample_products = [
            ("Blush Bouquet", "Bouquet", 64.0, "Romantic handmade crochet flower bouquet for weddings and gifting.", "https://images.unsplash.com/photo-1526047932273-341f2a7631f9?auto=format&fit=crop&w=900&q=80"),
            ("Golden Stem Set", "Single Stem", 22.0, "A cheerful set of handmade crochet stems for table styling.", "https://images.unsplash.com/photo-1518623489648-a173ef7824f3?auto=format&fit=crop&w=900&q=80"),
            ("Garden Arrangement", "Arrangement", 88.0, "Statement floral arrangement for home decor and events.", "https://images.unsplash.com/photo-1468327768560-75b778cbb551?auto=format&fit=crop&w=900&q=80"),
        ]
        db.executemany(
            "INSERT INTO products (name, category, price, description, image) VALUES (?, ?, ?, ?, ?)",
            sample_products,
        )
        db.commit()


with app.app_context():
    init_db()


def validate_custom_order(form_data):
    errors = {}
    name = (form_data.get("name") or "").strip()
    email = (form_data.get("email") or "").strip()
    event_date = (form_data.get("event_date") or "").strip()
    details = (form_data.get("details") or "").strip()

    if len(name) < 2:
        errors["name"] = "Please enter at least 2 characters"
    if "@" not in email or "." not in email:
        errors["email"] = "Please enter a valid email address"
    if not event_date:
        errors["event_date"] = "Please choose an event date"
    else:
        try:
            if date.fromisoformat(event_date) <= date.today():
                errors["event_date"] = "Please enter a future date"
        except ValueError:
            errors["event_date"] = "Please enter a valid date"
    if len(details) < 10:
        errors["details"] = "Please provide at least 10 characters"

    return errors


@app.route("/")
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id LIMIT 3").fetchall()
    return render_template("index.html", products=products, active_page="home")


@app.route("/shop")
def shop():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id").fetchall()
    return render_template("shop.html", products=products, active_page="shop")


@app.route("/about")
def about():
    return render_template("about.html", active_page="about")


@app.route("/custom-orders", methods=["GET", "POST"])
def custom_orders():
    form_data = request.form
    errors = {}

    if request.method == "POST":
        errors = validate_custom_order(form_data)
        if not errors:
            db = get_db()
            db.execute(
                "INSERT INTO custom_orders (name, email, event_date, details) VALUES (?, ?, ?, ?)",
                (form_data.get("name", ""), form_data.get("email", ""), form_data.get("event_date", ""), form_data.get("details", "")),
            )
            db.commit()
            return render_template("custom_orders.html", submitted=True, active_page="custom-orders")

    return render_template(
        "custom_orders.html",
        submitted=False,
        active_page="custom-orders",
        errors=errors,
        form_data=form_data,
    )


@app.route("/contact")
def contact():
    return render_template("contact.html", active_page="contact")


if __name__ == "__main__":
    app.run(debug=True)
