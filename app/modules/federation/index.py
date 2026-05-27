from flask import redirect, request, url_for
from flask_admin import AdminIndexView, expose
from flask_security import current_user


class FederationAdminIndexView(AdminIndexView):
    """Dashboard for the federation admin home page."""

    required_roles = ["federation"]

    def is_accessible(self):
        if not current_user.is_authenticated:
            return False
        return any(current_user.has_role(role) for role in self.required_roles)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login", next=request.url))

    @expose("/")
    def index(self):
        if not self.is_accessible():
            return self.inaccessible_callback("index")

        from app.models import Idp, Sp
        from app.models.entity_status import EntityStatus
        from app.services.metadata import MetadataService

        stats = {
            "idp_total": Idp.query.count(),
            "sp_total": Sp.query.count(),
            "idp_approving": Idp.query.filter_by(
                idp_status=EntityStatus.APPROVING.value
            ).count(),
            "sp_approving": Sp.query.filter_by(
                sp_status=EntityStatus.APPROVING.value
            ).count(),
        }

        return self.render(
            "federation/index.html",
            metadata_files=MetadataService.get_federation_metadata_files(),
            stats=stats,
        )
