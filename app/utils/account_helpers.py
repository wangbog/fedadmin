import secrets
import string

from flask import current_app, flash
from flask_security.recoverable import generate_reset_link
from flask_security.signals import reset_password_instructions_sent
from flask_security.utils import config_value, hash_password, send_mail
from markupsafe import Markup, escape

from app.utils.logging_helpers import logger


def set_random_password(user, length=24):
    """Set an unshared random password so the user must use the reset link."""
    user.password = hash_password(_generate_secure_password(length))


def send_password_setup_link(user):
    """Generate a password setup link and send it when reset email is enabled."""
    try:
        reset_link, reset_token = generate_reset_link(user)
    except Exception as exc:
        logger.exception(
            "[Account] Failed to generate password setup link for user #%s: %s",
            user.id,
            exc,
        )
        return None, False, "Password setup link could not be generated."

    if not config_value("SEND_PASSWORD_RESET_EMAIL"):
        return reset_link, False, "Password reset email is disabled."

    try:
        send_mail(
            config_value("EMAIL_SUBJECT_PASSWORD_RESET"),
            user.email,
            "reset_instructions",
            user=user,
            reset_link=reset_link,
            reset_token=reset_token,
        )
        reset_password_instructions_sent.send(
            current_app._get_current_object(),
            _async_wrapper=current_app.ensure_sync,
            user=user,
            token=reset_token,
            reset_token=reset_token,
        )
        return reset_link, True, "Password setup email sent."
    except Exception as exc:
        logger.exception(
            "[Account] Failed to send password setup email to user #%s: %s",
            user.id,
            exc,
        )
        return reset_link, False, "Password setup email could not be sent."


def flash_password_setup_link(user, reset_link, email_sent, email_message):
    """Show the one-time password setup link to the administrator."""
    category = "success" if email_sent else "warning"
    flash(email_message, category)
    if not reset_link:
        return

    flash(
        Markup(
            '<div>Password setup link for user "{username}": '
            '<a href="{url}" target="_blank" rel="noopener noreferrer">'
            "Open password setup link</a></div>"
            '<div class="small text-break mt-1">{url}</div>'
        ).format(username=escape(user.username), url=escape(reset_link)),
        category,
    )


def _generate_secure_password(length):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
