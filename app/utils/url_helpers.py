from urllib.parse import urlparse

from flask import request


def safe_redirect_target(target, fallback):
    """Return a same-origin relative redirect target, otherwise the fallback."""
    if not target:
        return fallback

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not target.startswith("/"):
        return fallback
    if target.startswith("//") or target.startswith("\\"):
        return fallback

    return target


def form_redirect_target(fallback):
    """Read the Flask-Admin return URL from form data and keep it same-origin."""
    return safe_redirect_target(request.form.get("url"), fallback)


def is_valid_http_url(value, *, require_https=False):
    """Validate HTTP(S) URLs used in generated metadata."""
    if not value or not value.strip():
        return False

    parsed = urlparse(value.strip())
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if parsed.scheme not in allowed_schemes:
        return False
    if not parsed.netloc:
        return False
    if any(char.isspace() for char in value):
        return False

    return True
