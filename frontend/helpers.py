"""Small helpers shared by every blueprint in views/."""

from functools import wraps
from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, session, url_for

import api_client


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


def remember_roles(memberships):
    """Keep the user's roles in the session so pages can hide owner-only
    controls. Each entry is {business_id, role}, as the API returns them.

    This only decides what buttons to show. The API checks the role again
    on every request, so a stale session can't do anything it shouldn't.
    """
    session["is_owner"] = any(m["role"] == "owner" for m in memberships)


def is_owner():
    """True if the user owns at least one business."""
    return bool(session.get("is_owner"))


def form_int(name):
    """A whole number from the submitted form, or None if blank or not a number.
    The API decides whether None is allowed and says so if it isn't."""
    return request.form.get(name, type=int)


def form_float(name):
    return request.form.get(name, type=float)


def form_text(name):
    return request.form.get(name, "").strip()


def back(fallback_endpoint="dashboard.dashboard", **values):
    """Redirect to the page the form was on, or a fallback.

    Only follows the Referer header when it points back at this site, so a
    crafted link can't bounce the user somewhere else.
    """
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for(fallback_endpoint, **values))


def register_api_error_handlers(app):
    """What happens when a page's API call fails, in one place.

    - The API can't be reached: a page saying so (503), not a stack trace.
    - 404: the record doesn't exist or isn't the user's. Go back to the
      Dashboard without saying which (NF-REQ-12).
    - Anything else (400, 403, 409, ...): show the API's own sentence as a
      flash message on the page the user came from. The frontend doesn't
      repeat the API's validation; the API's message is the one shown.
    """

    @app.errorhandler(api_client.ApiUnavailable)
    def api_unavailable(error):
        return render_template("api_unavailable.html"), 503

    @app.errorhandler(api_client.ApiError)
    def api_error(error):
        if error.status == 404:
            if request.endpoint == "dashboard.dashboard":
                # The Dashboard is where 404s send people, so a 404 here
                # means the API itself is missing the endpoint. Say so
                # rather than redirecting in a loop.
                return render_template("api_unavailable.html", missing=True), 502
            return redirect(url_for("dashboard.dashboard"))
        flash(error.message, "error")
        return back()

    @app.context_processor
    def inject_user():
        return {"user": session.get("user"), "is_owner": is_owner()}
