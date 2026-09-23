import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

# Railway (and any other host) should set a SECRET_KEY env var in production.
# Falls back to a dev key so the app still runs locally without extra setup.
app.secret_key = os.environ.get("SECRET_KEY", "club_secret_key")


# ==========================================
# USERS LIST
# No database is used
# ==========================================

users = [
    {
        "username": "manager",
        "password": "manager123",
        "role": "manager",
        "name": "Club Manager",
        "student_id": ""
    },
    {
        "username": "staff",
        "password": "staff123",
        "role": "staff",
        "name": "Club Staff",
        "student_id": ""
    },
    {
        "username": "student",
        "password": "student123",
        "role": "student",
        "name": "Juan Student",
        "student_id": "2024-0001",
        "year_level": "2nd Year",
        "department": "College of Computer Studies"
    }
]


# ==========================================
# CLUB LIST
# ==========================================

clubs = [
    {
        "id": 1,
        "name": "Computer Science Club",
        "description": "For students interested in programming and technology.",
        "category": "Technology"
    },
    {
        "id": 2,
        "name": "Sports Club",
        "description": "Activities for students who enjoy sports.",
        "category": "Sports"
    },
    {
        "id": 3,
        "name": "Music Club",
        "description": "For students interested in music and performing arts.",
        "category": "Arts"
    }
]


# ==========================================
# REGISTRATION LIST
# Each registration now has:
#   id            unique number
#   status        "pending" / "accepted" / "rejected"
#   date          when the request was made
# ==========================================

registrations = []


# ==========================================
# HELPERS
# ==========================================

def find_user(username):
    for user in users:
        if user["username"].lower() == username.lower():
            return user
    return None


def find_club(club_id):
    for club in clubs:
        if club["id"] == club_id:
            return club
    return None


def find_registration(reg_id):
    for registration in registrations:
        if registration["id"] == reg_id:
            return registration
    return None


def next_club_id():
    if not clubs:
        return 1
    return max(club["id"] for club in clubs) + 1


def next_registration_id():
    if not registrations:
        return 1
    return max(registration["id"] for registration in registrations) + 1


def today():
    return datetime.now().strftime("%b %d, %Y")


def dashboard_for(role):
    if role == "manager":
        return url_for("manager")
    if role == "staff":
        return url_for("staff")
    return url_for("student")


# ==========================================
# LOGIN
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        user = find_user(username)

        if user and user["password"] == password:

            session["username"] = user["username"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            session["student_id"] = user.get("student_id", "")
            session["year_level"] = user.get("year_level", "")
            session["department"] = user.get("department", "")

            return redirect(dashboard_for(user["role"]))

        return render_template(
            "login.html",
            error="That username and password don't match an account."
        )

    # After a successful sign up the user is sent back here with ?new=1
    notice = None

    if request.args.get("new"):
        notice = "Account created. Sign in below to get started."

    return render_template("login.html", notice=notice)


# ==========================================
# SIGN UP
# ==========================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm = request.form["confirm"]
        role = request.form["role"]
        student_id = request.form.get("student_id", "").strip()
        year_level = request.form.get("year_level", "").strip()
        department = request.form.get("department", "").strip()

        # Keep what was typed so the form can be refilled on an error
        form = {
            "name": name,
            "username": username,
            "role": role,
            "student_id": student_id,
            "year_level": year_level,
            "department": department
        }

        error = None

        if role not in ["student", "staff"]:
            error = "Choose whether you are joining as a student or as staff."

        elif len(username) < 4:
            error = "Username needs at least 4 characters."

        elif " " in username:
            error = "Username can't contain spaces."

        elif find_user(username):
            error = "That username is taken. Try another one."

        elif len(password) < 6:
            error = "Password needs at least 6 characters."

        elif password != confirm:
            error = "The two passwords don't match."

        elif role == "student" and not student_id:
            error = "Students need to enter a student ID."

        elif role == "student" and not year_level:
            error = "Students need to choose a year level."

        elif role == "student" and not department:
            error = "Students need to enter a department."

        if error:
            return render_template("signup.html", error=error, form=form)

        users.append({
            "username": username,
            "password": password,
            "role": role,
            "name": name,
            "student_id": student_id,
            "year_level": year_level if role == "student" else "",
            "department": department if role == "student" else ""
        })

        return redirect(url_for("login", new=1))

    return render_template("signup.html", form={})


# ==========================================
# MANAGER DASHBOARD
# ==========================================

@app.route("/manager", methods=["GET", "POST"])
def manager():

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    # Add new club
    if request.method == "POST":

        club_name = request.form["club_name"].strip()
        description = request.form["description"].strip()
        category = request.form["category"].strip()

        clubs.append({
            "id": next_club_id(),
            "name": club_name,
            "description": description,
            "category": category
        })

        return redirect(url_for("manager"))

    return render_template(
        "manager.html",
        clubs=clubs,
        registrations=registrations,
        members=[user for user in users if user["role"] != "manager"]
    )


# ==========================================
# STAFF DASHBOARD
# ==========================================

@app.route("/staff")
def staff():

    if "username" not in session or session["role"] != "staff":
        return redirect(url_for("login"))

    pending = [r for r in registrations if r["status"] == "pending"]
    decided = [r for r in registrations if r["status"] != "pending"]

    return render_template(
        "staff.html",
        clubs=clubs,
        pending_registrations=pending,
        registrations=decided
    )


# ==========================================
# STAFF REGISTRATION
# Staff registering a student directly is auto-accepted, since
# a staff member is vouching for it on the spot.
# ==========================================

@app.route("/register_student", methods=["POST"])
def register_student():

    if "username" not in session or session["role"] != "staff":
        return redirect(url_for("login"))

    student_name = request.form["student_name"].strip()
    student_id = request.form["student_id"].strip()
    year_level = request.form.get("year_level", "").strip()
    department = request.form.get("department", "").strip()
    club_id = int(request.form["club_id"])

    selected_club = find_club(club_id)

    if selected_club:

        registrations.append({
            "id": next_registration_id(),
            "username": "",
            "student_name": student_name,
            "student_id": student_id,
            "year_level": year_level,
            "department": department,
            "club": selected_club["name"],
            "registered_by": "Staff",
            "status": "accepted",
            "date": today()
        })

    return redirect(url_for("staff"))


# ==========================================
# ACCEPT / REJECT A JOIN REQUEST
# ==========================================

def dashboard_route():
    return "manager" if session["role"] == "manager" else "staff"


@app.route("/registration/<int:reg_id>/accept", methods=["POST"])
def accept_registration(reg_id):

    if "username" not in session or session["role"] not in ("staff", "manager"):
        return redirect(url_for("login"))

    registration = find_registration(reg_id)

    if registration and registration["status"] == "pending":
        registration["status"] = "accepted"

    return redirect(url_for(dashboard_route()))


@app.route("/registration/<int:reg_id>/reject", methods=["POST"])
def reject_registration(reg_id):

    if "username" not in session or session["role"] not in ("staff", "manager"):
        return redirect(url_for("login"))

    registration = find_registration(reg_id)

    if registration and registration["status"] == "pending":
        registration["status"] = "rejected"

    return redirect(url_for(dashboard_route()))


# ==========================================
# STUDENT DASHBOARD
# ==========================================

@app.route("/student")
def student():

    if "username" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    username = session["username"]

    my_registrations = []

    for registration in registrations:

        if registration.get("username") == username:
            my_registrations.append(registration)

    # Latest status per club, so a rejected request doesn't block
    # trying again, but a pending/accepted one does.
    club_status = {}

    for registration in my_registrations:
        club_status[registration["club"]] = registration["status"]

    return render_template(
        "student.html",
        clubs=clubs,
        registrations=my_registrations,
        club_status=club_status
    )


# ==========================================
# STUDENT CLUB REGISTRATION
# Creates a pending request instead of joining instantly.
# ==========================================

@app.route("/join_club/<int:club_id>", methods=["POST"])
def join_club(club_id):

    if "username" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    selected_club = find_club(club_id)

    if selected_club:

        blocked = False

        for registration in registrations:

            if (
                registration.get("username") == session["username"]
                and registration["club"] == selected_club["name"]
                and registration["status"] in ("pending", "accepted")
            ):
                blocked = True

        if not blocked:

            registrations.append({
                "id": next_registration_id(),
                "username": session["username"],
                "student_name": session["name"],
                "student_id": session.get("student_id") or session["username"],
                "year_level": session.get("year_level", ""),
                "department": session.get("department", ""),
                "club": selected_club["name"],
                "registered_by": "Student",
                "status": "pending",
                "date": today()
            })

    return redirect(url_for("student"))


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==========================================
# RUN APPLICATION
# Railway (and most hosts) inject PORT; gunicorn is used in production
# via the Procfile, this block is only for local `python app.py` runs.
# ==========================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
