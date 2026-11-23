"""Surplus & Shortage (Layer 2: Compliance), and items past their service life."""

from flask import Blueprint, render_template

import api_client
from helpers import current_user_id, login_required

bp = Blueprint("compliance", __name__)


@bp.route("/compliance")
@login_required
def compliance():
    user_id = current_user_id()
    return render_template(
        "compliance.html",
        report=api_client.get_compliance(user_id),
        expired=api_client.get_expired_items(user_id),
    )
