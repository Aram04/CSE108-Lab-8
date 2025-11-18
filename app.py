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

# Import models after db initialization
from models import User, Course, Enrollment



#  Admin-Only Access
class AdminOnlyView(ModelView):
    def is_accessible(self):
        # Must be logged in and user_type must be admin
        return g.user and g.user.user_type == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return redirect("/login")


# Custom Course View
# Enables selecting a teacher in Flask-Admin
class AdminCourseView(AdminOnlyView):
    # Columns to display in the list page
    column_list = ["name", "max_students", "time", "teacher"]

    # Fields allowed in the create/edit form
    form_columns = ["name", "max_students", "time", "teacher"]

    # Make teacher selectable by username
    form_ajax_refs = {
        "teacher": {
            "fields": [User.username],
            "page_size": 10
        }
    }

# Flask-Admin Setup 
admin = Admin(app, name='Admin Dashboard', template_mode='bootstrap4')

admin.add_view(AdminOnlyView(User, db.session))
admin.add_view(AdminCourseView(Course, db.session))       # <-- teacher dropdown works now
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


# Login Route 
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


# Student Dashboard
@app.route("/student")
def student_dashboard():
    if not g.user or g.user.user_type != "student":
        return redirect("/login")

    courses = Course.query.all()
    my_enrollments = Enrollment.query.filter_by(student_id=g.user.id).all()

    return render_template(
        "student_dashboard.html",
        courses=courses,
        my_enrollments=my_enrollments
    )


# Enroll in a course
@app.route("/enroll/<int:course_id>")
def enroll(course_id):
    if not g.user or g.user.user_type != "student":
        return redirect("/login")

    exists = Enrollment.query.filter_by(
        student_id=g.user.id,
        course_id=course_id
    ).first()

    if exists:
        return redirect("/student")

    new_enroll = Enrollment(student_id=g.user.id, course_id=course_id, grade="N/A")
    db.session.add(new_enroll)
    db.session.commit()

    return redirect("/student")


# Teacher Dashboard
@app.route("/teacher")
def teacher_dashboard():
    if not g.user or g.user.user_type != "teacher":
        return redirect("/login")

    courses = Course.query.filter_by(teacher_id=g.user.id).all()

    return render_template("teacher_dashboard.html", courses=courses)


# Teacher Course Detail Page
@app.route("/teacher/course/<int:course_id>")
def teacher_course_detail(course_id):
    if not g.user or g.user.user_type != "teacher":
        return redirect("/login")

    course = Course.query.get(course_id)

    # Safety check: teacher cannot view courses that are not theirs
    if not course or course.teacher_id != g.user.id:
        return redirect("/teacher")

    enrollments = Enrollment.query.filter_by(course_id=course.id).all()

    return render_template(
        "teacher_course_detail.html",
        course=course,
        enrollments=enrollments
    )


# Teacher Grade Update
@app.route("/teacher/grade/<int:enrollment_id>", methods=["POST"])
def update_grade(enrollment_id):
    if not g.user or g.user.user_type != "teacher":
        return redirect("/login")

    enrollment = Enrollment.query.get(enrollment_id)

    # Safety check: ensure teacher owns this course
    if not enrollment or enrollment.course.teacher_id != g.user.id:
        return redirect("/teacher")

    new_grade = request.form["grade"]
    enrollment.grade = new_grade
    db.session.commit()

    return redirect(f"/teacher/course/{enrollment.course_id}")


# Run App
if __name__ == "__main__":
    app.run(debug=True)
