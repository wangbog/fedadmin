from unittest.mock import patch

from app.utils.security_helpers import csrf_protected


def test_csrf_failure_rejects_external_referrer(app):
    with (
        app.test_request_context(
            "/",
            method="POST",
            headers={"Referer": "https://evil.example/after-csrf"},
        ),
        patch("app.utils.security_helpers.validate_csrf_token", return_value=False),
        patch("app.utils.security_helpers.url_for", return_value="/fallback"),
    ):

        @csrf_protected
        def protected_view():
            return "ok"

        response = protected_view()

    assert response.status_code == 302
    assert response.location == "/fallback"
