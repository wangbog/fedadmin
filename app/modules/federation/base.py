from flask import flash, redirect, url_for, request
from app.modules.admin.base import BaseAdminView


class FederationBaseView(BaseAdminView):
    """Base view for federation admin."""

    required_roles = ["federation"]

    can_create = False
    can_edit = False
    can_delete = False

    def handle_view_exception(self, exc):
        if isinstance(exc, ValueError):
            flash(str(exc), "error")
            return redirect(request.referrer or url_for("federation_admin.index"))
        return super().handle_view_exception(exc)
