"""Redistribute (Layer 3: Decision Support)."""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import redistribution
from helpers import current_user_id, login_required

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
    (the Run Optimizer button) runs Scott's engine on the owner's current
    inventory, saves the result, and redirects back to GET."""
    if request.method == "POST":
        try:
            plan = redistribution.generate_plan(current_user_id())
        except redistribution.NoFeasiblePlan:
            session.pop("last_plan", None)
            flash(
                "No plan could cover every shortage: some item can't be moved "
                "from another site and has no replacement cost set.",
                "error",
            )
            return redirect(url_for("redistribute.redistribute"))

        plan["generated_at"] = datetime.now().strftime("%I:%M %p").lstrip("0")
        if len(json.dumps(plan)) <= _MAX_SAVED_PLAN_BYTES:
            session["last_plan"] = plan
            # Redirect so a browser refresh doesn't re-submit the form.
            return redirect(url_for("redistribute.redistribute"))
        session.pop("last_plan", None)
        return render_template("redistribute.html", user=session["user"], plan=plan)

    plan = session.get("last_plan") or {"generated": False}
    return render_template("redistribute.html", user=session["user"], plan=plan)
