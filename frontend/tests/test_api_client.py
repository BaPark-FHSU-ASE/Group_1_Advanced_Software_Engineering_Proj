"""Tests for api_client.py that don't need the API running.

End-to-end tests against the real API are in test_targets.py.
"""

import socket

import pytest

import api_client


def _unused_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_unreachable_api_raises_api_unavailable(monkeypatch):
    monkeypatch.setattr(api_client, "API_URL", f"http://127.0.0.1:{_unused_port()}")
    with pytest.raises(api_client.ApiUnavailable):
        api_client.set_target(1, 1, 1, 5)


def test_default_url_is_port_5001():
    # Unless STOCKDADDY_API_URL is set, the frontend looks for the API on 5001.
    import os
    if "STOCKDADDY_API_URL" not in os.environ:
        assert api_client.API_URL == "http://127.0.0.1:5001"
