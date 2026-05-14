from flask import request, flash, redirect, url_for
from flask_wtf.csrf import validate_csrf
from wtforms import ValidationError
import functools


def validate_csrf_token():
    """
    Validate CSRF token from request form.
    Returns True if valid, else flashes error and returns False.
    If redirect_on_fail is provided, returns a redirect response.
    """
    try:
        validate_csrf(request.form.get("csrf_token"))
        return True
    except ValidationError:
        flash("Invalid CSRF token. Please refresh the page and try again.", "error")
        return False


def csrf_protected(f):
    """
    Decorator to enforce CSRF protection for view functions.
    Validates CSRF token before executing the decorated function.
    """

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Always validate CSRF token first
        if not validate_csrf_token():
            return redirect(request.referrer or url_for(".index_view"))

        # If validation passes, proceed with the original function
        return f(*args, **kwargs)

    return decorated_function
