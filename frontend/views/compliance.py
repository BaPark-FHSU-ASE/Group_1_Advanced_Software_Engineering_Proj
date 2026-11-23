"""Surplus & Shortage (Layer 2: Compliance)."""

from flask import Blueprint, render_template, session

import db
from helpers import current_user_id, login_required

bp = Blueprint("compliance", __name__)


@bp.route("/compliance")
@login_required
def compliance():
    report = db.get_compliance_report(current_user_id())
    return render_template("compliance.html", user=session["user"], report=report)
