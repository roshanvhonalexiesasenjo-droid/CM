import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)

# Railway (and any other host) should set a SECRET_KEY env var in production.
# Falls back to a dev key so the app still runs locally without extra setup.
app.secret_key = os.environ.get("SECRET_KEY", "club_secret_key")


# ==========================================
# USERS LIST
# No database is used
# ==========================================

# Accounts marked "demo": True always work for sign in, but are hidden from
# the manager's member directory and counts so they never show up in the HTML.
users = [
    {
        "username": "manager",
        "password": "manager123",
        "role": "manager",
        "name": "Club Manager",
        "student_id": "",
        "phone": "",
        "year_level": "",
        "department": "",
        "demo": True
    },
    {
        "username": "staff",
        "password": "staff123",
        "role": "staff",
        "name": "Demo Staff",
        "student_id": "",
        "phone": "+1 555 010 0002",
        "year_level": "",
        "department": "",
        "demo": True
    },
    {
        "username": "student",
        "password": "student123",
        "role": "student",
        "name": "Demo Student",
        "student_id": "DEMO-0001",
        "phone": "+1 555 010 0003",
        "year_level": "1st Year",
        "department": "College of Demo",
        "demo": True
    }
]


# ==========================================
# CLUB LIST
# ==========================================

# Year levels offered everywhere in the app (sign up, staff, manager)
YEAR_LEVELS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


@app.context_processor
def inject_year_levels():
    return {"year_levels": YEAR_LEVELS}


# Roles a coordinator can give to the members of their club.
# The first four can only be held by one member per club.
CLUB_ROLES = ["Member", "President", "Vice President", "Secretary", "Treasurer", "Committee Head"]
SINGLE_HOLDER_ROLES = ["President", "Vice President", "Secretary", "Treasurer"]


@app.context_processor
def inject_club_roles():
    return {"club_roles": CLUB_ROLES}


def clubs_coordinated_by(username):
    return [club for club in clubs if club.get("coordinator") == username]


@app.context_processor
def inject_my_coordinated_clubs():
    if session.get("role") in COORDINATOR_ROLES:
        return {"my_coordinated_clubs": clubs_coordinated_by(session.get("username"))}
    return {"my_coordinated_clubs": []}


clubs = [
    {
        "id": 1,
        "name": "Computer Science Club",
        "description": "For students interested in programming and technology.",
        "category": "Technology",
        "coordinator": ""
    },
    {
        "id": 2,
        "name": "Sports Club",
        "description": "Activities for students who enjoy sports.",
        "category": "Sports",
        "coordinator": ""
    },
    {
        "id": 3,
        "name": "Music Club",
        "description": "For students interested in music and performing arts.",
        "category": "Arts",
        "coordinator": ""
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


def valid_phone(phone):
    allowed_characters = "+(). -"
    digit_count = sum(character.isdigit() for character in phone)
    return 7 <= digit_count and len(phone) <= 20 and all(
        character.isdigit() or character in allowed_characters for character in phone
    )


def validate_new_user(name, username, password, confirm, role, student_id, phone, year_level, department):
    """Shared by the public sign up form and the manager's Add User form.
    Returns an error message, or None when everything is fine."""

    if not name:
        return "Please enter a full name."
    if not valid_phone(phone):
        return "Enter a valid contact number with at least 7 digits."
    if role not in ["student", "staff"]:
        return "Choose whether the account is for a student or for staff."
    if len(username) < 4:
        return "Username needs at least 4 characters."
    if " " in username:
        return "Username can't contain spaces."
    if find_user(username):
        return "That username is taken. Try another one."
    if len(password) < 6:
        return "Password needs at least 6 characters."
    if password != confirm:
        return "The two passwords don't match."
    if role == "student" and not student_id:
        return "Students need to enter a student ID."
    if role == "student" and year_level not in YEAR_LEVELS:
        return "Students need to choose a year level (1st to 4th Year)."
    if role == "student" and not department:
        return "Students need to enter a department."
    return None


def find_student_by_id(student_id):
    for user in users:
        if user["role"] == "student" and user.get("student_id", "").lower() == student_id.lower():
            return user
    return None


def find_club(club_id):
    for club in clubs:
        if club["id"] == club_id:
            return club
    return None


def coordinator_of(club):
    """The user account chosen as coordinator for a club, or None."""
    username = club.get("coordinator", "")
    return find_user(username) if username else None


@app.context_processor
def inject_coordinator_helper():
    return {"coordinator_of": coordinator_of}


COORDINATOR_ROLES = ("staff", "student")


def coordinator_choices(role):
    """Accounts of one role that can be picked as a coordinator (demo accounts stay hidden)."""
    return [u for u in users if u["role"] == role and not u.get("demo")]


def members_by_department(club):
    """Accepted members of a club, grouped by department (A-Z, blank last)."""
    groups = {}

    for registration in registrations:
        if registration["club"] != club["name"] or registration["status"] != "accepted":
            continue

        department = (registration.get("department") or "").strip()
        key = department.casefold()

        if key not in groups:
            groups[key] = {"department": department or "No department", "blank": not department, "members": []}

        groups[key]["members"].append(registration)

    result = sorted(groups.values(), key=lambda g: (g["blank"], g["department"].casefold()))

    for group in result:
        group["members"].sort(key=lambda r: r["student_name"].casefold())

    return result


def club_of_registration(registration):
    for club in clubs:
        if club["name"] == registration["club"]:
            return club
    return None


def pending_for(club):
    return [r for r in registrations if r["club"] == club["name"] and r["status"] == "pending"]


def is_accepted_member(username, club):
    return any(
        r.get("username") == username and r["club"] == club["name"] and r["status"] == "accepted"
        for r in registrations
    )


def coordinated_registration(reg_id):
    """(registration, club) if the signed-in user coordinates that registration's club, else (None, None)."""
    if session.get("role") not in COORDINATOR_ROLES:
        return None, None

    registration = find_registration(reg_id)
    club = club_of_registration(registration) if registration else None

    if club and club.get("coordinator") == session.get("username"):
        return registration, club

    return None, None


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
# ACTIVITY LOG
# Everything that is created, changed or deleted is written here so a
# manager can look back at it, including a short snapshot of anything
# that was deleted. Kept in memory like the rest of the data (resets on
# restart), newest entries last, capped at ACTIVITY_LIMIT.
#
# Activity by (or about) the demo staff and demo student accounts is not
# logged, so they never show up in the HTML. The manager account is
# the one that reads the log, so its own actions are logged. Set
# LOG_DEMO_ACTIVITY=1 to log the demo staff and student too. Set APP_TIMEZONE (for example "America/New_York")
# to change the time zone used for timestamps. It defaults to UTC.
# ==========================================

ACTIVITY_LIMIT = 500
ACTIVITY_SHOW = 200
LOG_DEMO_ACTIVITY = os.environ.get("LOG_DEMO_ACTIVITY") == "1"

activity_log = []

ACTIVITY_FILTERS = [
    ("all", "All"),
    ("deleted", "Deleted"),
    ("accounts", "Accounts"),
    ("clubs", "Clubs"),
    ("requests", "Requests"),
    ("roles", "Roles"),
    ("sign-ins", "Sign-ins"),
]


def log_timezone():
    try:
        return ZoneInfo(os.environ.get("APP_TIMEZONE", "UTC"))
    except Exception:
        return timezone.utc


def hidden_from_log(user):
    """Demo staff and demo student stay out of the log (the demo manager does not)."""
    return bool(user and user.get("demo") and user["role"] != "manager" and not LOG_DEMO_ACTIVITY)


def log_activity(category, action, details, tone="neutral", deleted=False,
                 subjects=(), actor=None, actor_role=""):
    """Add an entry. tone is "good", "danger" or "neutral" (only changes the colour).
    subjects are usernames the entry is about; actor defaults to whoever is signed in."""

    if actor is None:
        username = session.get("username")

        if username:
            user = find_user(username)

            if hidden_from_log(user):
                return

            actor = f"{session.get('name', username)} (@{username})"
            actor_role = session.get("role", "")
        else:
            actor = "System"

    for subject in subjects:
        if hidden_from_log(find_user(subject) if subject else None):
            return

    activity_log.append({
        "id": (activity_log[-1]["id"] + 1) if activity_log else 1,
        "time": datetime.now(log_timezone()).strftime("%b %d, %Y · %I:%M %p %Z"),
        "category": category,
        "action": action,
        "details": details,
        "tone": tone,
        "deleted": deleted,
        "actor": actor,
        "actor_role": actor_role
    })

    del activity_log[:-ACTIVITY_LIMIT]


def count_word(number, word):
    return f"{number} {word}{'' if number == 1 else 's'}"


def registration_label(registration):
    return f"{registration['student_name']} ({registration['student_id']}) · {registration['club']}"


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
            session["phone"] = user.get("phone", "")
            session["year_level"] = user.get("year_level", "")
            session["department"] = user.get("department", "")

            log_activity("sign-ins", "Signed in", f"Signed in as {user['role']}.")

            return redirect(dashboard_for(user["role"]))

        log_activity(
            "sign-ins", "Failed sign-in",
            f"Wrong username or password for '{username[:40]}'.",
            tone="danger", actor="Not signed in", subjects=[username]
        )

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
        phone = request.form.get("phone", "").strip()
        year_level = request.form.get("year_level", "").strip()
        department = request.form.get("department", "").strip()

        # Keep what was typed so the form can be refilled on an error
        form = {
            "name": name,
            "username": username,
            "role": role,
            "student_id": student_id,
            "phone": phone,
            "year_level": year_level,
            "department": department
        }

        error = validate_new_user(
            name, username, password, confirm, role,
            student_id, phone, year_level, department
        )

        if error:
            return render_template("signup.html", error=error, form=form)

        users.append({
            "username": username,
            "password": password,
            "role": role,
            "name": name,
            "student_id": student_id,
            "phone": phone,
            "year_level": year_level if role == "student" else "",
            "department": department if role == "student" else ""
        })

        log_activity(
            "accounts", "Account created",
            f"{name} (@{username}) signed up as {role}.",
            tone="good", actor=f"{name} (@{username})", actor_role=role,
            subjects=[username]
        )

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
            "category": category,
            "coordinator": ""
        })

        log_activity("clubs", "Club created", f"Created club '{club_name}' ({category}).", tone="good")

        return redirect(url_for("manager"))

    return render_manager()


def visible_members():
    return [user for user in users if user["role"] != "manager" and not user.get("demo")]


def render_manager(**extra):
    return render_template(
        "manager.html",
        clubs=clubs,
        registrations=registrations,
        members=visible_members(),
        **extra
    )


# ==========================================
# MANAGER: ADD A USER (its own page)
# GET shows the form, POST creates the account.
# ==========================================

@app.route("/manager/add_user", methods=["GET", "POST"])
def add_user():

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("add_user.html")

    name = request.form["name"].strip()
    username = request.form["username"].strip()
    password = request.form["password"]
    confirm = request.form["confirm"]
    role = request.form["role"]
    student_id = request.form.get("student_id", "").strip()
    phone = request.form.get("phone", "").strip()
    year_level = request.form.get("year_level", "").strip()
    department = request.form.get("department", "").strip()

    error = validate_new_user(
        name, username, password, confirm, role,
        student_id, phone, year_level, department
    )

    if error:
        form = {
            "name": name, "username": username, "role": role,
            "student_id": student_id, "phone": phone,
            "year_level": year_level, "department": department
        }
        return render_template("add_user.html", user_error=error, user_form=form)

    users.append({
        "username": username,
        "password": password,
        "role": role,
        "name": name,
        "student_id": student_id if role == "student" else "",
        "phone": phone,
        "year_level": year_level if role == "student" else "",
        "department": department if role == "student" else ""
    })

    log_activity(
        "accounts", "Account created",
        f"Created {role} account for {name} (@{username}).",
        tone="good", subjects=[username]
    )

    flash(f"Account created for {name} ({username}).")
    return redirect(url_for("add_user"))


# ==========================================
# MANAGER: MEMBER DIRECTORY (its own page)
# Demo accounts are left out of the list.
# ==========================================

@app.route("/manager/members")
def member_directory():

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    return render_template("directory.html", members=visible_members())


# ==========================================
# MANAGER: ACTIVITY LOG (its own page)
# ?filter= picks one of ACTIVITY_FILTERS. Newest first.
# ==========================================

@app.route("/manager/activity")
def activity():

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    def matches(entry, key):
        if key == "all":
            return True
        if key == "deleted":
            return entry["deleted"]
        return entry["category"] == key

    current = request.args.get("filter", "all")

    if current not in [key for key, _ in ACTIVITY_FILTERS]:
        current = "all"

    counts = {key: sum(1 for e in activity_log if matches(e, key)) for key, _ in ACTIVITY_FILTERS}
    matching = [e for e in activity_log if matches(e, current)]

    return render_template(
        "activity.html",
        entries=list(reversed(matching))[:ACTIVITY_SHOW],
        total=len(matching),
        filters=ACTIVITY_FILTERS,
        counts=counts,
        current=current,
        limit=ACTIVITY_LIMIT
    )


@app.route("/manager/activity/clear", methods=["POST"])
def clear_activity():

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    activity_log.clear()
    log_activity("system", "Log cleared", "The activity log was cleared.", tone="danger")
    flash("Activity log cleared.")

    return redirect(url_for("activity"))


# ==========================================
# MANAGER: DELETE A USER
# Removes the account and any join requests they made themselves.
# The manager account can't be deleted.
# ==========================================

@app.route("/manager/user/<username>/delete", methods=["POST"])
def delete_user(username):

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    user = find_user(username)

    if user and user["role"] != "manager" and not user.get("demo"):
        own_registrations = [r for r in registrations if r.get("username") == user["username"]]
        coordinated = [c["name"] for c in clubs if c.get("coordinator") == user["username"]]

        users.remove(user)
        for club in clubs:
            if club.get("coordinator") == user["username"]:
                club["coordinator"] = ""
        registrations[:] = [r for r in registrations if r.get("username") != user["username"]]

        info = [user["role"]]
        for key, label in (("student_id", "ID {}"), ("year_level", "{}"), ("department", "{}")):
            if user.get(key):
                info.append(label.format(user[key]))

        details = f"Deleted account {user['name']} (@{user['username']}) · {', '.join(info)}."
        if own_registrations:
            details += f" Also removed {count_word(len(own_registrations), 'registration')}."
        if coordinated:
            details += f" No longer coordinator of {', '.join(coordinated)}."

        log_activity("accounts", "Account deleted", details, tone="danger", deleted=True)

    return redirect(url_for("member_directory"))


# ==========================================
# CLUB PAGE (staff and manager)
# Shows the club's coordinator and its accepted members,
# split up by department.
# ==========================================

@app.route("/club/<int:club_id>")
def club_detail(club_id):

    if "username" not in session or session["role"] not in ("staff", "manager"):
        return redirect(url_for("login"))

    club = find_club(club_id)

    if not club:
        return redirect(url_for(dashboard_route()))

    groups = members_by_department(club)
    pending_count = sum(
        1 for r in registrations if r["club"] == club["name"] and r["status"] == "pending"
    )

    return render_template(
        "club_detail.html",
        club=club,
        groups=groups,
        member_count=sum(len(g["members"]) for g in groups),
        pending_count=pending_count,
        staff_list=coordinator_choices("staff"),
        student_list=coordinator_choices("student")
    )


@app.route("/club/<int:club_id>/coordinator", methods=["POST"])
def set_coordinator(club_id):

    if "username" not in session or session["role"] not in ("staff", "manager"):
        return redirect(url_for("login"))

    club = find_club(club_id)

    if not club:
        return redirect(url_for(dashboard_route()))

    username = request.form.get("coordinator", "").strip()
    previous = coordinator_of(club)

    if not username:
        club["coordinator"] = ""
        flash(f"{club['name']} no longer has a coordinator.")

        if previous:
            log_activity(
                "roles", "Coordinator removed",
                f"{previous['name']} (@{previous['username']}) is no longer coordinator of {club['name']}.",
                tone="danger"
            )
    else:
        chosen = find_user(username)

        if not chosen or chosen["role"] not in COORDINATOR_ROLES or chosen.get("demo"):
            flash("Choose someone from the list.", "error")
        else:
            club["coordinator"] = chosen["username"]
            flash(f"{chosen['name']} is now the coordinator for {club['name']}.")

            if not previous or previous["username"] != chosen["username"]:
                details = f"{chosen['name']} (@{chosen['username']}, {chosen['role']}) is now coordinator of {club['name']}."
                if previous:
                    details += f" Replaced {previous['name']}."
                log_activity("roles", "Coordinator assigned", details, tone="good")

    return redirect(url_for("club_detail", club_id=club_id))


# ==========================================
# COORDINATOR PAGE
# A staff or student account that was picked as coordinator of one
# or more clubs can give each accepted member of those clubs a role.
# ==========================================

@app.route("/coordinator")
def coordinator_page():

    if "username" not in session or session["role"] not in COORDINATOR_ROLES:
        return redirect(url_for("login"))

    mine = clubs_coordinated_by(session["username"])

    if not mine:
        return redirect(dashboard_for(session["role"]))

    sections = []

    for club in mine:
        groups = members_by_department(club)
        sections.append({
            "club": club,
            "groups": groups,
            "pending": pending_for(club),
            "member_count": sum(len(g["members"]) for g in groups)
        })

    return render_template("coordinator.html", sections=sections)


@app.route("/coordinator/registration/<int:reg_id>/role", methods=["POST"])
def set_member_role(reg_id):

    if "username" not in session or session["role"] not in COORDINATOR_ROLES:
        return redirect(url_for("login"))

    registration, club = coordinated_registration(reg_id)

    # Only the coordinator of this member's club may change the role
    if not club or registration["status"] != "accepted":
        return redirect(url_for("coordinator_page"))

    role = request.form.get("club_role", "").strip()
    anchor = f"#club-{club['id']}"

    if role not in CLUB_ROLES:
        flash("Choose a role from the list.", "error")
        return redirect(url_for("coordinator_page") + anchor)

    if role in SINGLE_HOLDER_ROLES:
        for other in registrations:
            if (
                other["id"] != registration["id"]
                and other["club"] == club["name"]
                and other["status"] == "accepted"
                and other.get("club_role") == role
            ):
                flash(f"{other['student_name']} is already {role} of {club['name']}. "
                      f"Change their role first.", "error")
                return redirect(url_for("coordinator_page") + anchor)

    old_role = registration.get("club_role") or "Member"
    registration["club_role"] = role
    flash(f"{registration['student_name']} is now {role} of {club['name']}.")

    if old_role != role:
        log_activity(
            "roles", "Role changed",
            f"{registration['student_name']} in {club['name']}: {old_role} → {role} (as coordinator).",
            subjects=[registration.get("username")]
        )
    return redirect(url_for("coordinator_page") + anchor)


# ==========================================
# COORDINATOR: ACCEPT / REJECT REQUESTS, REMOVE MEMBERS
# Limited to the clubs the signed-in user coordinates.
# ==========================================

@app.route("/coordinator/registration/<int:reg_id>/accept", methods=["POST"])
def coordinator_accept(reg_id):

    if "username" not in session:
        return redirect(url_for("login"))

    registration, club = coordinated_registration(reg_id)

    if not club:
        return redirect(dashboard_for(session["role"]))

    if registration["status"] == "pending":
        registration["status"] = "accepted"
        flash(f"{registration['student_name']} was accepted into {club['name']}.")
        log_activity("requests", "Request accepted", f"{registration_label(registration)} (as coordinator).",
                     tone="good", subjects=[registration.get("username")])

    return redirect(url_for("coordinator_page") + f"#club-{club['id']}")


@app.route("/coordinator/registration/<int:reg_id>/reject", methods=["POST"])
def coordinator_reject(reg_id):

    if "username" not in session:
        return redirect(url_for("login"))

    registration, club = coordinated_registration(reg_id)

    if not club:
        return redirect(dashboard_for(session["role"]))

    if registration["status"] == "pending":
        registration["status"] = "rejected"
        flash(f"{registration['student_name']}'s request for {club['name']} was declined.")
        log_activity("requests", "Request rejected", f"{registration_label(registration)} (as coordinator).",
                     tone="danger", subjects=[registration.get("username")])

    return redirect(url_for("coordinator_page") + f"#club-{club['id']}")


@app.route("/coordinator/registration/<int:reg_id>/remove", methods=["POST"])
def coordinator_remove(reg_id):

    if "username" not in session:
        return redirect(url_for("login"))

    registration, club = coordinated_registration(reg_id)

    if not club:
        return redirect(dashboard_for(session["role"]))

    if registration["status"] == "accepted":
        registrations.remove(registration)
        flash(f"{registration['student_name']} was removed from {club['name']}.")
        log_activity(
            "requests", "Member removed",
            f"Removed {registration_label(registration)} · was {registration.get('club_role') or 'Member'} (as coordinator).",
            tone="danger", deleted=True, subjects=[registration.get("username")]
        )

    return redirect(url_for("coordinator_page") + f"#club-{club['id']}")


# ==========================================
# STUDENT: SEE EVERYONE IN A CLUB THEY JOINED
# Members can see the whole club, every department, in tabs.
# Contact numbers and student IDs are not shown to other students.
# ==========================================

@app.route("/student/club/<int:club_id>")
def club_roster(club_id):

    if "username" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    club = find_club(club_id)

    if not club or not is_accepted_member(session["username"], club):
        return redirect(url_for("student"))

    groups = members_by_department(club)

    return render_template(
        "club_roster.html",
        club=club,
        groups=groups,
        member_count=sum(len(g["members"]) for g in groups)
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
    phone = request.form.get("phone", "").strip()
    year_level = request.form.get("year_level", "").strip()
    department = request.form.get("department", "").strip()
    password = request.form.get("password", "")

    try:
        selected_club = find_club(int(request.form.get("club_id", "")))
    except ValueError:
        selected_club = None

    error = None
    created_account = False
    account = find_student_by_id(student_id) if student_id else None

    if not selected_club:
        error = "Choose a club for the student."
    elif not student_name or not student_id:
        error = "Enter the student's name and ID."
    elif not valid_phone(phone):
        error = "Enter a valid contact number with at least 7 digits."
    elif year_level not in YEAR_LEVELS:
        error = "Choose a year level (1st to 4th Year)."
    elif not department:
        error = "Enter the student's department."
    elif account is None and find_user(student_id):
        error = "That student ID is already used by another account."
    elif account is None:
        # No account for this student yet: create one. The student ID is
        # their username, and staff sets the first password.
        error = validate_new_user(
            student_name, student_id, password, password, "student",
            student_id, phone, year_level, department
        )

        if not error:
            account = {
                "username": student_id,
                "password": password,
                "role": "student",
                "name": student_name,
                "student_id": student_id,
                "phone": phone,
                "year_level": year_level,
                "department": department
            }
            users.append(account)
            created_account = True

    if not error:
        for registration in registrations:
            if (
                registration.get("username") == account["username"]
                and registration["club"] == selected_club["name"]
                and registration["status"] in ("pending", "accepted")
            ):
                error = f"{student_name} already has a request or membership in {selected_club['name']}."

    if error:
        flash(error, "error")
        return redirect(url_for("staff"))

    registrations.append({
        "id": next_registration_id(),
        "username": account["username"],
        "student_name": student_name,
        "student_id": student_id,
        "phone": phone,
        "year_level": year_level,
        "department": department,
        "club": selected_club["name"],
        "registered_by": "Staff",
        "club_role": "Member",
        "status": "accepted",
        "date": today()
    })

    if created_account:
        log_activity(
            "accounts", "Account created",
            f"Created student account for {student_name} (@{account['username']}) while registering them.",
            tone="good", subjects=[account["username"]]
        )

    log_activity(
        "requests", "Student registered",
        f"{student_name} ({student_id}) was registered in {selected_club['name']} (accepted).",
        tone="good", subjects=[account["username"]]
    )

    if created_account:
        flash(f"{student_name} is registered in {selected_club['name']}. "
              f"They can sign in with username {student_id} and the password you set.")
    else:
        flash(f"{student_name} is registered in {selected_club['name']}. "
              f"They already have an account, so their password was left unchanged.")

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
        log_activity("requests", "Request accepted", registration_label(registration),
                     tone="good", subjects=[registration.get("username")])

    return redirect(url_for(dashboard_route()))


@app.route("/registration/<int:reg_id>/reject", methods=["POST"])
def reject_registration(reg_id):

    if "username" not in session or session["role"] not in ("staff", "manager"):
        return redirect(url_for("login"))

    registration = find_registration(reg_id)

    if registration and registration["status"] == "pending":
        registration["status"] = "rejected"
        log_activity("requests", "Request rejected", registration_label(registration),
                     tone="danger", subjects=[registration.get("username")])

    return redirect(url_for(dashboard_route()))


# ==========================================
# DELETE A REGISTRATION
# Staff and managers can remove a registration record.
# ==========================================

@app.route("/registration/<int:reg_id>/delete", methods=["POST"])
def delete_registration(reg_id):

    if "username" not in session or session["role"] not in ("staff", "manager"):
        return redirect(url_for("login"))

    registration = find_registration(reg_id)

    if registration:
        registrations.remove(registration)
        log_activity(
            "requests", "Registration deleted",
            f"Deleted registration: {registration_label(registration)} · was {registration['status']}.",
            tone="danger", deleted=True, subjects=[registration.get("username")]
        )

    return redirect(url_for(dashboard_route()))


# ==========================================
# DELETE A CLUB (manager only)
# Also removes the registrations that belonged to that club,
# so nothing is left pointing at a club that no longer exists.
# ==========================================

@app.route("/club/<int:club_id>/delete", methods=["POST"])
def delete_club(club_id):

    if "username" not in session or session["role"] != "manager":
        return redirect(url_for("login"))

    club = find_club(club_id)

    if club:
        removed = [r for r in registrations if r["club"] == club["name"]]
        coordinator = coordinator_of(club)

        clubs.remove(club)
        registrations[:] = [r for r in registrations if r["club"] != club["name"]]

        details = f"Deleted club '{club['name']}' ({club['category']})."
        if coordinator:
            details += f" Coordinator was {coordinator['name']}."
        if removed:
            by_status = {status: sum(1 for r in removed if r["status"] == status)
                         for status in ("accepted", "pending", "rejected")}
            breakdown = ", ".join(f"{n} {status}" for status, n in by_status.items() if n)
            details += f" Also removed {count_word(len(removed), 'registration')} ({breakdown})."

        log_activity("clubs", "Club deleted", details, tone="danger", deleted=True)

    return redirect(url_for("manager"))


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
                "phone": session.get("phone", ""),
                "year_level": session.get("year_level", ""),
                "department": session.get("department", ""),
                "club": selected_club["name"],
                "registered_by": "Student",
                "club_role": "Member",
                "status": "pending",
                "date": today()
            })

            log_activity("requests", "Join request",
                         f"{session['name']} asked to join {selected_club['name']}.",
                         subjects=[session["username"]])

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
