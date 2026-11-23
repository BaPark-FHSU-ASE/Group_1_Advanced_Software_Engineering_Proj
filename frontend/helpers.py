"""Small helpers shared by every blueprint in views/."""

from functools import wraps

from flask import redirect, session, url_for


def login_required(view):
    """Send anyone who isn't logged in to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def current_user_id():
    """The logged-in account's id (an owner or an employee)."""
    return session["owner_id"]
