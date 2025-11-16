from flask import Flask, render_template, request, redirect, session, g
from flask_sqlalchemy import SQLAlchemy

# --- App Setup ---
app = Flask(__name__)
app.secret_key = "supersecretkey"  # replace later

# --- Database Config ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab8.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Import models AFTER db is created to avoid circular imports
from models import User, Course, Enrollment


# --- Load logged-in user before every request ---
@app.before_request
def load_user():
    g.user = None
    if "user_id" in session:
        g.user = User.query.get(session["user_id"])


# --- Home route (temporary for testing) ---
@app.route("/")
def home():
    return "<h2>Lab 8 server running successfully</h2>"


# --- Run the app ---
if __name__ == "__main__":
    app.run(debug=True)
