from flask import flash, redirect, url_for, request
from app.modules.admin.base import BaseAdminView
from app.utils.url_helpers import safe_redirect_target


class FederationBaseView(BaseAdminView):
    """Base view for federation admin."""

    required_roles = ["federation"]

    can_create = False
    can_edit = False
    can_delete = False

    def handle_view_exception(self, exc):
        if isinstance(exc, ValueError):
            flash(str(exc), "error")
            fallback = url_for("federation_admin.index")
            return redirect(safe_redirect_target(request.referrer, fallback))
        return super().handle_view_exception(exc)
