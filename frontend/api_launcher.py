"""Starts the Stock Daddy API alongside the frontend.

Running `python app.py` in frontend/ calls start_api() first, so one command
runs both servers. The API runs as a separate process on its own port, the
same as if it were started by hand in stock_daddy_api/, and stops when the
frontend stops.

It isn't started if:
- something is already listening on the API's port (e.g. someone started
  the API by hand), or
- STOCKDADDY_API_URL points at another machine, or
- STOCKDADDY_START_API is set to 0.

If the API can't start (usually because stock_daddy_api's requirements
aren't installed), the frontend still runs; only Set Target needs the API.
"""

import atexit
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import api_client
import db

API_DIR = Path(__file__).resolve().parent.parent / "stock_daddy_api"
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
STARTUP_SECONDS = 10


def _port_open(host, port):
    try:
        socket.create_connection((host, port), timeout=0.2).close()
        return True
    except OSError:
        return False


def _warn(message):
    print(f" * Stock Daddy API: {message}", file=sys.stderr)


def _stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def start_api():
    """Start the API if it should be and isn't already running.

    Returns the API's process, or None if it wasn't started.
    """
    # Flask's debug reloader runs app.py a second time in a child process
    # (marked with WERKZEUG_RUN_MAIN). The first process already started the
    # API and stays alive across reloads, so the child skips it.
    if os.environ.get("WERKZEUG_RUN_MAIN"):
        return None
    if os.environ.get("STOCKDADDY_START_API", "1") == "0":
        return None

    url = urlparse(api_client.API_URL)
    host, port = url.hostname, url.port or 80
    if host not in LOCAL_HOSTS:
        return None
    if _port_open(host, port):
        return None  # already running, use that one

    env = dict(
        os.environ,
        API_PORT=str(port),
        # Same database file as the frontend, as an absolute path so it
        # doesn't depend on the API's working folder.
        DB_PATH=str(Path(db.DB_PATH).resolve()),
        # No debug reloader for the API: it would start a second process
        # that this one couldn't stop cleanly.
        FLASK_DEBUG="False",
    )
    try:
        proc = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=API_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except OSError as e:
        _warn(f"couldn't start ({e}). Everything except Set Target still works.")
        return None

    deadline = time.time() + STARTUP_SECONDS
    while not _port_open(host, port):
        if proc.poll() is not None:
            error = proc.stderr.read().decode(errors="replace").strip().splitlines()
            reason = error[-1] if error else f"exit code {proc.returncode}"
            _warn(f"didn't start ({reason}). Everything except Set Target still works.")
            return None
        if time.time() > deadline:
            _stop(proc)
            _warn("didn't start in time. Everything except Set Target still works.")
            return None
        time.sleep(0.1)

    # Nothing reads the API's error output once it's running, so close the
    # pipe rather than let it fill up.
    proc.stderr.close()

    # Stop the API when the frontend stops. Ctrl+C ends the frontend
    # normally, which runs atexit; a plain kill (SIGTERM) doesn't, so turn it
    # into a normal exit first.
    atexit.register(_stop, proc)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    print(f" * Stock Daddy API running on http://{host}:{port}")
    return proc
