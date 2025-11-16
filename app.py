from flask import Flask, render_template, request, redirect, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


# App Setup 
app = Flask(__name__)
app.secret_key = "supersecretkey"  # replace later


# Database Config 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab8.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Import models AFTER db initialization
from models import User, Course, Enrollment



# Secure Admin-Only Access
class AdminOnlyView(ModelView):
    def is_accessible(self):
        # Must be logged in AND user_type must be admin
        return g.user and g.user.user_type == "admin"

    def inaccessible_callback(self, name, **kwargs):
        # Redirect non-admin users to login page
        return redirect("/login")


# Flask-Admin Setup 
admin = Admin(app, name='Admin Dashboard', template_mode='bootstrap4')


# Register views
admin.add_view(AdminOnlyView(User, db.session))
admin.add_view(AdminOnlyView(Course, db.session))
admin.add_view(AdminOnlyView(Enrollment, db.session))


# Load logged-in user before every request
@app.before_request
def load_user():
    g.user = None
    if "user_id" in session:
        g.user = User.query.get(session["user_id"])


# Temporary Home Route 
@app.route("/")
def home():
    return "<h2>Lab 8 server running successfully</h2>"


# Login Route (will need this for admin protection to work) 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id

            # Redirect by user type
            if user.user_type == "student":
                return redirect("/student")
            if user.user_type == "teacher":
                return redirect("/teacher")
            if user.user_type == "admin":
                return redirect("/admin")

        return "Invalid username or password."

    return render_template("login.html")


# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# Run the app 
if __name__ == "__main__":
    app.run(debug=True)
