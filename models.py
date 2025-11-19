from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    #realname = db.Column(db.String(64), unique=False, nullable=False)
    password_hash = db.Column(db.String(128))
    user_type = db.Column(db.String(16))  # student / teacher / admin

    enrollments = db.relationship("Enrollment", back_populates="student")
    courses_taught = db.relationship("Course", back_populates="teacher")

    # use method='pbkdf2:sha256'
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw, method='pbkdf2:sha256')

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    # This makes teacher1 show correctly in dropdown
    def __str__(self):
        return self.username


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    max_students = db.Column(db.Integer)
    time = db.Column(db.String(32))

    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    teacher = db.relationship("User", back_populates="courses_taught")

    enrollments = db.relationship("Enrollment", back_populates="course")

    # For debugging and admin display
    def __str__(self):
        return self.name


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"))
    grade = db.Column(db.String(4))

    student = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")

    # Shows nice text instead of <Enrollment X>
    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.name}"
