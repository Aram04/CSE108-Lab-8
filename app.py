from flask import Flask, render_template, request, redirect, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView # Import AdminIndexView
from flask_admin.contrib.sqla import ModelView
from extensions import db
from sqlalchemy import event
from werkzeug.security import generate_password_hash
# from werkzeug.security import check_password_hash # Assuming this is in your User model

# App Setup 
app = Flask(__name__)
app.secret_key = "supersecretkey" # replace later

# Database Config 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab8.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Import models after db initialization
with app.app_context():
    from models import User, Course, Enrollment
    # NOTE: Ensure your User model has a `check_password` method
    db.create_all()

# --- Flask-Admin Setup ---

# Define a custom index view to override the base template (The Fix!)
class CustomAdminIndexView(AdminIndexView):
    # Set the path to your custom template file
    admin_base_template = 'admin/my_custom_base.html'
    
    def is_accessible(self):
        return g.user and g.user.user_type == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return redirect("/login")

# Admin-Only Access for Model Views
class AdminOnlyView(ModelView):
    def is_accessible(self):
        # Must be logged in and user_type must be admin
        return g.user and g.user.user_type == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return redirect("/login")


# Custom Course View (Teacher selection)
class AdminCourseView(AdminOnlyView):
    column_list = ["name", "max_students", "time", "teacher"]
    form_columns = ["name", "max_students", "time", "teacher"]
    form_ajax_refs = {
        "teacher": {
            "fields": [User.username],
            "page_size": 10
        }
    }

# Custom User View
class AdminUserView(AdminOnlyView):
    column_list = ["username", "realname", "user_type", "password_hash"]
    form_columns = ["username", "realname", "user_type", "password_hash", "courses_taught", "enrollments"]
    column_exclude_list = ['password_hash']


@event.listens_for(User.password_hash, 'set', retval=True)
# Ensures passwords are hashed upon creation/update through Flask-Admin
def hash_user_password(target, value, oldvalue, initiator):
    # Check if the value is not already a hash and is different from the old value
    if value and not isinstance(value, str) or (isinstance(value, str) and not value.startswith('pbkdf2:sha256:')) and value != oldvalue:
        return generate_password_hash(value, method='pbkdf2:sha256')
    return value

# Flask-Admin Setup (Using the CustomAdminIndexView)
admin = Admin(
    app, 
    name='Admin Dashboard',
    index_view=CustomAdminIndexView(url='/admin') # Passed CustomAdminIndexView here
    # template_mode is typically not needed if you override the base template like this
)

admin.add_view(AdminUserView(User, db.session))
admin.add_view(AdminCourseView(Course, db.session))
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
    return "<h2>Lab 8 server running successfully</h2><p>Navigate to <a href='/login'>/login</a> to begin.</p>"


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

        return render_template("login.html", error="Invalid username or password.")

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

    # Fetch all courses and enrollments for the student
    courses = Course.query.all()
    my_enrollments = Enrollment.query.filter_by(student_id=g.user.id).all()
    
    enrolled_course_ids = {e.course_id for e in my_enrollments}
    available_courses = []

    # Calculate current student count for ALL courses efficiently
    course_student_counts = {}
    all_enrollments = Enrollment.query.all()
    for enrollment in all_enrollments:
        course_student_counts[enrollment.course_id] = course_student_counts.get(enrollment.course_id, 0) + 1


    for course in courses:
        # Update cur_students property temporarily for rendering
        course.cur_students = course_student_counts.get(course.id, 0)
        
        # Only show courses the student is NOT already enrolled in
        if course.id not in enrolled_course_ids:
            available_courses.append(course)


    return render_template(
        "student_dashboard.html",
        courses=available_courses,
        my_enrollments=my_enrollments
    )


# Enroll in a course / Unenroll (Drop) from a course (UPDATED LOGIC)
@app.route("/enroll/<int:course_id>", methods=['POST']) # Only accept POST requests
def enroll(course_id):
    if not g.user or g.user.user_type != "student":
        return redirect("/login")

    enrollment = Enrollment.query.filter_by(
        student_id=g.user.id,
        course_id=course_id
    ).first()

    course = Course.query.get(course_id)
    
    if not course:
        return redirect("/student")

    # If an enrollment exists, this is an UNENROLL/DROP action
    if enrollment:
        # Delete the existing enrollment record
        db.session.delete(enrollment)
        db.session.commit()
    
    # If an enrollment does NOT exist, this is an ENROLL action
    else:
        # Calculate current students (better to query enrollment count)
        current_students = Enrollment.query.filter_by(course_id=course_id).count()

        # Check for max capacity
        if current_students >= course.max_students:
            # Optionally show an error message here, but for simplicity, just redirect
            return redirect("/student")

        # Perform the enrollment
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

    # Eager load student info
    enrollments = Enrollment.query.filter_by(course_id=course.id).join(User).all()

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

    new_grade = request.form.get("grade")
    
    if new_grade is not None:
        enrollment.grade = new_grade
        db.session.commit()

    return redirect(f"/teacher/course/{enrollment.course_id}")


# Run App
if __name__ == "__main__":
    app.run(debug=True)