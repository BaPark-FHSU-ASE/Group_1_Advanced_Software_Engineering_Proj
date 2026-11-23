"""Login, register and logout."""

from flask import Blueprint, redirect, render_template, request, session, url_for

import db

bp = Blueprint("auth", __name__)


@bp.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        owner = db.verify_owner(email, password)
        if owner is not None:
            session["user"] = owner["first_name"]
            session["owner_id"] = owner["owner_id"]
            return redirect(url_for("dashboard.dashboard"))
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not first_name or not last_name or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            try:
                owner_id = db.register_owner(first_name, last_name, email, password)
                session["user"] = first_name
                session["owner_id"] = owner_id
                return redirect(url_for("dashboard.dashboard"))
            except db.EmailAlreadyRegistered:
                error = "An account with that email already exists."

    return render_template("register.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
