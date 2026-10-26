
import os
import json
import re
import tempfile
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from services.pdf_parser import parse_resume
from services.matcher import analyze_resume


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "local-development-key-change-before-deployment",
)

# Preserve the existing SQLite database.
DATABASE_PATH = BASE_DIR / "resume_matcher.db"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_PATH.as_posix()
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Resume upload limit: 5 MB.
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"


# --------------------------------------------------
# DATABASE MODELS
# Keep existing table names and columns unchanged.
# --------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Analysis(db.Model):
    __tablename__ = "analysis"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    filename = db.Column(db.String(255), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    match_score = db.Column(db.Integer, nullable=False)
    matched_skills = db.Column(db.Text, default="")
    missing_skills = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )


# --------------------------------------------------
# LOGIN MANAGER
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_recent_analyses(user_id, limit=5):
    return (
        Analysis.query
        .filter_by(user_id=user_id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(limit)
        .all()
    )


def parse_saved_skills(value):
    """Read skill lists saved as JSON or comma-separated text."""
    if not value:
        return []

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [
                str(skill).strip()
                for skill in parsed
                if str(skill).strip()
            ]
    except (ValueError, TypeError):
        pass

    return [
        skill.strip()
        for skill in re.split(r"[,;\n]", value)
        if skill.strip()
    ]


def build_analytics(analyses):
    """Build dashboard statistics from the current user's history."""
    from collections import Counter

    scores = [int(item.match_score or 0) for item in analyses]

    matched_counter = Counter()
    missing_counter = Counter()
    role_counter = Counter()

    for item in analyses:
        matched_counter.update(
            skill.lower()
            for skill in parse_saved_skills(item.matched_skills)
        )
        missing_counter.update(
            skill.lower()
            for skill in parse_saved_skills(item.missing_skills)
        )

        role = (item.job_title or "Untitled").strip()
        role_counter[role] += 1

    chronological = list(reversed(analyses))

    score_labels = [
        item.created_at.strftime("%d %b %Y")
        if item.created_at
        else f"Analysis #{item.id}"
        for item in chronological
    ]

    score_values = [
        int(item.match_score or 0)
        for item in chronological
    ]

    top_missing = missing_counter.most_common(7)
    top_roles = role_counter.most_common(5)

    return {
        "total_analyses": len(analyses),
        "average_score": (
            round(sum(scores) / len(scores)) if scores else 0
        ),
        "best_score": max(scores) if scores else 0,
        "total_matched_skills": sum(matched_counter.values()),
        "total_missing_skills": sum(missing_counter.values()),
        "score_labels": score_labels,
        "score_values": score_values,
        "skill_labels": ["Matched", "Missing"],
        "skill_values": [
            sum(matched_counter.values()),
            sum(missing_counter.values()),
        ],
        "top_missing_labels": [
            skill for skill, count in top_missing
        ],
        "top_missing_values": [
            count for skill, count in top_missing
        ],
        "role_labels": [
            role for role, count in top_roles
        ],
        "role_values": [
            count for role, count in top_roles
        ],
    }


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():
    recent_analyses = []

    if current_user.is_authenticated:
        recent_analyses = get_recent_analyses(current_user.id)

    return render_template(
        "index.html",
        recent_analyses=recent_analyses,
        analyses=recent_analyses,
    )


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            password,
        )

        if not username or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")

        if len(username) > 80 or len(email) > 255:
            flash("Username or email is too long.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "error",
            )
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        existing_user = User.query.filter(
            or_(
                User.username == username,
                User.email == email,
            )
        ).first()

        if existing_user:
            flash(
                "Username or email is already registered.",
                "error",
            )
            return render_template("register.html")

        user = User(
            username=username,
            email=email,
        )
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Registration failed")
            flash(
                "Registration could not be completed. Please try again.",
                "error",
            )
            return render_template("register.html")

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        identifier = request.form.get(
            "username",
            request.form.get("email", ""),
        ).strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            or_(
                User.username == identifier,
                User.email == identifier.lower(),
            )
        ).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")

            next_page = request.args.get("next", "")
            # Only allow local application paths.
            if (
                next_page.startswith("/")
                and not next_page.startswith("//")
                and "\\" not in next_page
            ):
                return redirect(next_page)

            return redirect(url_for("index"))

        flash("Invalid username/email or password.", "error")

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------
# RESUME ANALYSIS
# --------------------------------------------------

@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    job_title = request.form.get("job_title", "").strip()
    job_description = request.form.get(
        "job_description",
        "",
    ).strip()

    # Accept common file input names for template compatibility.
    resume_file = (
        request.files.get("resume")
        or request.files.get("resume_file")
        or request.files.get("resume_pdf")
    )

    if not job_title or not job_description:
        flash(
            "Please enter a target job title and job description.",
            "error",
        )
        return redirect(url_for("index"))

    if len(job_title) > 150:
        flash("Target job title must be 150 characters or fewer.", "error")
        return redirect(url_for("index"))

    if not resume_file or not resume_file.filename:
        flash("Please select a resume PDF.", "error")
        return redirect(url_for("index"))

    original_filename = secure_filename(resume_file.filename)

    if not original_filename.lower().endswith(".pdf"):
        flash("Only PDF files are supported.", "error")
        return redirect(url_for("index"))

    temp_path = None

    try:
        # Use a temporary file and remove it after processing.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".pdf",
            prefix="resume_",
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            resume_file.save(temp_file)

        if os.path.getsize(temp_path) == 0:
            flash("The uploaded file is empty.", "error")
            return redirect(url_for("index"))

        resume_data = parse_resume(temp_path)

        result = analyze_resume(
            resume_data,
            job_description,
        )

        # Keep the score within the database's expected range.
        match_score = max(
            0,
            min(100, int(result.get("score", 0))),
        )

        saved_analysis = Analysis(
            user_id=current_user.id,
            filename=original_filename[:255],
            job_title=job_title,
            match_score=match_score,
            matched_skills=", ".join(
                result.get("matched_skills", [])
            ),
            missing_skills=", ".join(
                result.get("missing_skills", [])
            ),
        )

        db.session.add(saved_analysis)
        db.session.commit()

        flash("Resume analysis completed successfully.", "success")

        return render_template(
            "results.html",
            result=result,
            resume_data=resume_data,
            job_title=job_title,
        )

    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
        return redirect(url_for("index"))

    except Exception:
        db.session.rollback()
        app.logger.exception("Resume analysis failed")
        flash(
            "Analysis failed. Please check the PDF and try again.",
            "error",
        )
        return redirect(url_for("index"))

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                app.logger.warning(
                    "Could not remove temporary resume file."
                )


# --------------------------------------------------
# INTERACTIVE ANALYTICS DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    analyses = (
        Analysis.query
        .filter_by(user_id=current_user.id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .all()
    )

    analytics = build_analytics(analyses)

    return render_template(
        "dashboard.html",
        analyses=analyses,
        analytics=analytics,
    )


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):
    flash(
        "The uploaded file is too large. Maximum size is 5 MB.",
        "error",
    )
    return redirect(url_for("index")), 413


# --------------------------------------------------
# DATABASE INITIALIZATION
# Creates missing tables only; does not reset existing data.
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    debug_mode = (
        os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
    app.run(debug=debug_mode)
