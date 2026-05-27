from flask import redirect, request, url_for
from flask_admin import AdminIndexView, expose
from flask_security import current_user


class MemberAdminIndexView(AdminIndexView):
    """Dashboard for the member admin home page."""

    required_roles = ["full_member", "sp_member"]

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

        organization_id = current_user.organization_id
        show_idp_stats = current_user.has_role("full_member")

        stats = {
            "sp_total": Sp.query.filter_by(organization_id=organization_id).count(),
            "sp_approving": Sp.query.filter_by(
                organization_id=organization_id,
                sp_status=EntityStatus.APPROVING.value,
            ).count(),
        }

        if show_idp_stats:
            stats.update(
                {
                    "idp_total": Idp.query.filter_by(
                        organization_id=organization_id
                    ).count(),
                    "idp_approving": Idp.query.filter_by(
                        organization_id=organization_id,
                        idp_status=EntityStatus.APPROVING.value,
                    ).count(),
                }
            )

        return self.render(
            "member/index.html",
            metadata_files=MetadataService.get_federation_metadata_files(),
            show_idp_stats=show_idp_stats,
            stats=stats,
        )
