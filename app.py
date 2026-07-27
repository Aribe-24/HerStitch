import base64
import json
import os
import smtplib
import sqlite3
import urllib.request
from datetime import date
from email.message import EmailMessage
from urllib.parse import urlencode

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


def send_notification(message_data):
    name = (message_data.get("name") or "").strip()
    email = (message_data.get("email") or "").strip()
    details = (message_data.get("details") or "").strip()
    subject = f"New HerStitch enquiry from {name or 'a visitor'}"
    body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{details}"

    email_sent = False
    whatsapp_sent = False

    smtp_server = os.getenv("MAIL_SERVER")
    smtp_port = int(os.getenv("MAIL_PORT", "587"))
    smtp_username = os.getenv("MAIL_USERNAME")
    smtp_password = os.getenv("MAIL_PASSWORD")
    recipient = os.getenv("MAIL_RECIPIENT", "herstitch24@gmail.com")
    sender = os.getenv("MAIL_DEFAULT_SENDER", smtp_username or "no-reply@herstitch.local")

    if smtp_server and smtp_username and smtp_password:
        try:
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = sender
            message["To"] = recipient
            message.set_content(body)
            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(message)
            email_sent = True
        except Exception as exc:
            app.logger.exception("Email notification failed: %s", exc)
    else:
        app.logger.info("Email notification skipped because SMTP settings are not configured")

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_WHATSAPP_FROM")
    twilio_to = os.getenv("TWILIO_WHATSAPP_TO")

    if twilio_sid and twilio_token and twilio_from and twilio_to:
        try:
            payload = urlencode(
                {
                    "To": twilio_to,
                    "From": twilio_from,
                    "Body": f"New HerStitch enquiry from {name}: {details[:160]}",
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                data=payload,
                headers={
                    "Authorization": "Basic " + base64.b64encode(f"{twilio_sid}:{twilio_token}".encode("utf-8")).decode("utf-8"),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(request) as response:
                response.read()
            whatsapp_sent = True
        except Exception as exc:
            app.logger.exception("WhatsApp notification failed: %s", exc)
    else:
        app.logger.info("WhatsApp notification skipped because Twilio settings are not configured")

    return {"email_sent": email_sent, "whatsapp_sent": whatsapp_sent}


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


def validate_contact_message(form_data):
    errors = {}
    name = (form_data.get("name") or "").strip()
    email = (form_data.get("email") or "").strip()
    message = (form_data.get("message") or "").strip()

    if len(name) < 2:
        errors["name"] = "Please enter at least 2 characters"
    if "@" not in email or "." not in email:
        errors["email"] = "Please enter a valid email address"
    if len(message) < 10:
        errors["message"] = "Please provide at least 10 characters"

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
            send_notification(
                {
                    "name": form_data.get("name", ""),
                    "email": form_data.get("email", ""),
                    "details": (
                        f"Custom order request for {form_data.get('event_date', '')}: {form_data.get('details', '')}"
                    ),
                }
            )
            return render_template("custom_orders.html", submitted=True, active_page="custom-orders")

    return render_template(
        "custom_orders.html",
        submitted=False,
        active_page="custom-orders",
        errors=errors,
        form_data=form_data,
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form_data = request.form
    errors = {}
    submitted = False

    if request.method == "POST":
        errors = validate_contact_message(form_data)
        if not errors:
            send_notification(
                {
                    "name": form_data.get("name", ""),
                    "email": form_data.get("email", ""),
                    "details": form_data.get("message", ""),
                }
            )
            submitted = True

    return render_template(
        "contact.html",
        active_page="contact",
        errors=errors,
        form_data=form_data,
        submitted=submitted,
    )


if __name__ == "__main__":
    app.run(debug=True)
