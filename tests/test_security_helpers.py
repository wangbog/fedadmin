from unittest.mock import patch

from app.modules.federation.base import FederationBaseView
from app.modules.member.base import MemberBaseView
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


def test_member_view_exception_rejects_external_referrer(app):
    view = object.__new__(MemberBaseView)

    with (
        app.test_request_context(
            "/member/sp/new/",
            headers={"Referer": "https://evil.example/member-return"},
        ),
        patch("app.modules.member.base.url_for", return_value="/member/"),
    ):
        response = view.handle_view_exception(ValueError("invalid"))

    assert response.status_code == 302
    assert response.location == "/member/"


def test_federation_view_exception_rejects_external_referrer(app):
    view = object.__new__(FederationBaseView)

    with (
        app.test_request_context(
            "/federation/sp/new/",
            headers={"Referer": "https://evil.example/federation-return"},
        ),
        patch("app.modules.federation.base.url_for", return_value="/federation/"),
    ):
        response = view.handle_view_exception(ValueError("invalid"))

    assert response.status_code == 302
    assert response.location == "/federation/"
