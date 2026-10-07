"""Calls from the frontend to the Stock Daddy API (stock_daddy_api/).

So far only stock targets go through the API; the rest of the frontend
still reads and writes through db.py.

Uses only the standard library (urllib), so the frontend needs no extra
packages to talk to the API.
"""

import json
import os
import urllib.error
import urllib.request

API_URL = os.environ.get("STOCKDADDY_API_URL", "http://127.0.0.1:5001").rstrip("/")
TIMEOUT_SECONDS = 5


class ApiUnavailable(Exception):
    """The API couldn't be reached (not running, wrong port, ...)."""


class ApiError(Exception):
    """The API answered with an error (4xx/5xx)."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read()).get("error", e.reason)
        except (ValueError, AttributeError):
            message = e.reason
        raise ApiError(e.code, message) from None
    except (urllib.error.URLError, OSError) as e:
        raise ApiUnavailable(str(e)) from None


def set_target(owner_id, building_id, item_type_id, target_qty):
    """Create or update a building's target for one item type (REQ-15).

    Returns (target, created): the saved target as a dict, and True if it
    was new or False if an existing target was updated.
    """
    status, target = _request(
        "PUT",
        f"/target_quantities/{building_id}/{item_type_id}",
        {"owner_id": owner_id, "target_qty": target_qty},
    )
    return target, status == 201
