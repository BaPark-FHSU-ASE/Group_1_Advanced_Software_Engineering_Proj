"""Login, register and logout, through the API's /auth endpoints."""

from flask import Blueprint, redirect, render_template, request, session, url_for

import api_client
from helpers import form_text, remember_roles

bp = Blueprint("auth", __name__)


def _start_session(owner):
    session.clear()
    session["user"] = owner["first_name"]
    session["owner_id"] = owner["owner_id"]
    remember_roles(owner.get("memberships", []))


@bp.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        try:
            owner = api_client.login(form_text("email"), request.form.get("password", ""))
        except api_client.ApiError as e:
            error = e.message
        else:
            _start_session(owner)
            return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html", error=error)


@bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        # The only check left here: the API never sees the second copy.
        if password != request.form.get("confirm_password", ""):
            error = "Passwords do not match."
        else:
            try:
                owner = api_client.register(
                    form_text("first_name"), form_text("last_name"),
                    form_text("email"), password,
                )
            except api_client.ApiError as e:
                error = e.message
            else:
                _start_session(owner)
                return redirect(url_for("dashboard.dashboard"))

    return render_template("register.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
