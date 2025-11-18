from flask import Flask, render_template, request, redirect, session, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash

# App Setup 
app = Flask(__name__)
app.secret_key = "supersecretkey"  # replace later


# Database Config 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab8.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):#moved db class defs to app because it
    #errors out when trying to import on my computer (maybe circular import?)
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    user_type = db.Column(db.String(16))  # student / teacher / admin

    enrollments = db.relationship("Enrollment", back_populates="student")
    courses_taught = db.relationship("Course", back_populates="teacher")

    # use method='pbkdf2:sha256'
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw, method='pbkdf2:sha256')

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    max_students = db.Column(db.Integer)
    time = db.Column(db.String(32))

    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    teacher = db.relationship("User", back_populates="courses_taught")

    enrollments = db.relationship("Enrollment", back_populates="course")


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"))
    grade = db.Column(db.String(4))

    student = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")


# Secure Admin-Only Access
class AdminOnlyView(ModelView):
    def is_accessible(self):
        # Must be logged in AND user_type must be admin
        return g.user and g.user.user_type == "admin"

    def inaccessible_callback(self, name, **kwargs):
        # Redirect non-admin users to login page
        return redirect("/login")


# Flask-Admin Setup 
admin = Admin(app, name='Admin Dashboard')#, template_mode='bootstrap4')


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

@app.route("/api/courses", methods=["GET", "POST"])
def classes():
    #if(request.method == 'POST'):
    #    x = Course(name=request.json['name'], max_students=['max_students'],
    #               time=['time'], teacher=['teacher'])
    #    db.session.add(x)
    #    db.session.commit()
    if(request.method == 'GET'):
        if g.user.user_type == "student":
            y = Enrollment.query.filter_by(student_id=g.user.id)
            for i in y:
                x[i] = Course.query.filter_by(id=i.course_id)
        if g.user.user_type == "teacher":
            x = Course.query.filter_by(teacher_id=g.user.id)
        a = []
        for i in x:
            data = {
                "name" = i.name
                "max_students" = i.max_students
                "time" = i.time
                "teacher" = i.teacher
            }
            a.append(data)
        return jsonify(a)

@app.route("/api/courses/<course>", methods = ['GET', 'PUT', 'DELETE'])
def classesRoute():
    x = Course.query.filter_by(name=course).first()
    if (x != None):
        if(request.method == 'PUT'):
            x.max_students = request.json['max_students']
            x.time = request.json['time']
            x.teacher = request.json['teacher']
            db.session.add(x)
            db.session.commit()
        if(request.method == 'DELETE'):
            db.session.delete(x)
            db.session.commit()


    #n = session["user.id"]
    #Enrollment.query.filter_by(

# Run the app 
if __name__ == "__main__":
    app.run(debug=True)
