from datetime import datetime

from flask import current_app, flash, g, has_request_context
from flask_security.mail_util import MailUtil
from sqlalchemy.orm import sessionmaker

from app.utils.logging_helpers import logger


class RecordingMailUtil(MailUtil):
    """Record Flask-Security email delivery and keep SMTP failures non-fatal."""

    def send_mail(self, template, subject, recipient, sender, body, html, **kwargs):
        user = kwargs.get("user")
        if current_app.config.get("MAIL_SUPPRESS_SEND"):
            _record_delivery(
                template=template,
                subject=subject,
                recipient=recipient,
                status="suppressed",
                user=user,
            )
            _flash_mail_warning("Email sending is suppressed by configuration.")
            return None

        try:
            result = super().send_mail(
                template, subject, recipient, sender, body, html, **kwargs
            )
        except Exception as exc:
            _record_delivery(
                template=template,
                subject=subject,
                recipient=recipient,
                status="failed",
                user=user,
                error_message=str(exc),
            )
            logger.warning(
                "[Mail] Delivery failed: template=%s recipient=%s error=%s",
                template,
                recipient,
                exc,
            )
            _flash_mail_warning(
                "Email could not be sent. The action was not cancelled; "
                "ask a federation administrator to check Email Delivery."
            )
            return None

        _record_delivery(
            template=template,
            subject=subject,
            recipient=recipient,
            status="sent",
            user=user,
            sent_at=datetime.now(),
        )
        return result


def get_last_delivery_status():
    if not has_request_context():
        return None
    return getattr(g, "last_email_delivery_status", None)


def _record_delivery(
    *,
    template,
    subject,
    recipient,
    status,
    user=None,
    error_message=None,
    sent_at=None,
):
    if has_request_context():
        g.last_email_delivery_status = status

    session = None
    try:
        from app.extensions import db
        from app.models.email_delivery import EmailDelivery

        session = sessionmaker(bind=db.engine)()
        record = EmailDelivery(
            recipient=recipient,
            subject=subject,
            template=template,
            status=status,
            error_message=_truncate_error(error_message),
            user_id=getattr(user, "id", None),
            sent_at=sent_at,
        )
        session.add(record)
        session.commit()
    except Exception as exc:
        if session is not None:
            try:
                session.rollback()
            except Exception:
                pass
        logger.warning("[Mail] Could not record email delivery status: %s", exc)
    finally:
        if session is not None:
            session.close()


def _flash_mail_warning(message):
    if has_request_context():
        flash(message, "warning")


def _truncate_error(error_message, max_length=2000):
    if not error_message:
        return None
    return error_message[:max_length]
