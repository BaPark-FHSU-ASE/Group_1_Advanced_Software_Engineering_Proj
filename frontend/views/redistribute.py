"""Redistribute (Layer 3: Decision Support).

The optimizer runs behind the API (POST /plans); the frontend only shows
the plan it gets back.
"""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import api_client
from helpers import current_user_id, is_owner, login_required

bp = Blueprint("redistribute", __name__)

# The last plan is kept in the session (a signed browser cookie) so it stays
# on the page until the owner runs it again or logs out. Browsers drop
# cookies over ~4 KB - and with them the login - so a plan too big to fit
# is shown once and not saved.
_MAX_SAVED_PLAN_BYTES = 3000


@bp.route("/redistribute", methods=["GET", "POST"])
@login_required
def redistribute():
    """GET shows the last plan run this session (or the empty state); POST
    (the Run Optimizer button) asks the API for a plan, saves it, and
    redirects back to GET."""
    if request.method == "POST":
        try:
            plan = api_client.run_plan(current_user_id())
        except api_client.ApiError as e:
            if e.status == 404:
                raise
            # 409: no plan covers every shortage. 403: not an owner.
            session.pop("last_plan", None)
            flash(e.message, "error")
            return redirect(url_for("redistribute.redistribute"))

        plan["generated_at"] = datetime.now().strftime("%I:%M %p").lstrip("0")
        if len(json.dumps(plan)) <= _MAX_SAVED_PLAN_BYTES:
            session["last_plan"] = plan
            # Redirect so a browser refresh doesn't re-submit the form.
            return redirect(url_for("redistribute.redistribute"))
        session.pop("last_plan", None)
        return render_template("redistribute.html", plan=plan)

    plan = session.get("last_plan") or {"generated": False}
    return render_template("redistribute.html", plan=plan, can_run=is_owner())
