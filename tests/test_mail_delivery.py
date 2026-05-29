from unittest.mock import patch

from flask import g

from app.models import EmailDelivery
from app.services.mail_delivery import RecordingMailUtil
from tests.conftest import make_organization, make_user


def test_recording_mail_util_records_suppressed_delivery(app, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    util = RecordingMailUtil(app)

    with app.test_request_context("/"):
        result = util.send_mail(
            "reset_instructions",
            "Reset password",
            user.email,
            "sender@example.org",
            "body",
            "<p>body</p>",
            user=user,
        )

        assert result is None
        assert g.last_email_delivery_status == "suppressed"

    record = EmailDelivery.query.one()
    assert record.recipient == user.email
    assert record.status == "suppressed"
    assert record.user_id == user.id


def test_recording_mail_util_records_failed_delivery(app, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    util = RecordingMailUtil(app)
    app.config["MAIL_SUPPRESS_SEND"] = False

    with (
        app.test_request_context("/"),
        patch(
            "flask_security.mail_util.MailUtil.send_mail",
            side_effect=RuntimeError("smtp down"),
        ),
    ):
        result = util.send_mail(
            "reset_instructions",
            "Reset password",
            user.email,
            "sender@example.org",
            "body",
            "<p>body</p>",
            user=user,
        )

        assert result is None
        assert g.last_email_delivery_status == "failed"

    record = EmailDelivery.query.one()
    assert record.status == "failed"
    assert record.error_message == "smtp down"
    app.config["MAIL_SUPPRESS_SEND"] = True
