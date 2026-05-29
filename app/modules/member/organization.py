import os
from urllib.parse import urlparse
from flask import abort, current_app, request, flash
from flask_security import current_user
from markupsafe import Markup, escape
from app.models import Idp, Sp
from app.models.edugain_status import EdugainStatus
from app.models.entity_status import EntityStatus
from app.models.organization_type import OrganizationType
from app.services.metadata import MetadataService
from app.utils.logging_helpers import logger, get_client_ip
from .base import MemberBaseView


class MemberOrganizationModelView(MemberBaseView):
    can_create = False

    # Define protected fields that cannot be modified through the edit form
    PROTECTED_FIELDS = ["organization_status", "organization_type", "organization_name"]

    extra_js = [
        "/static/js/form_utils.js",
        "/static/js/organization_forms.js",
    ]
    column_list = [
        "organization_type",
        "organization_status",
        "organization_name",
        "actions",
    ]
    column_details_list = [
        "organization_type",
        "organization_status",
        "organization_name",
        "organization_description",
        "organization_url",
    ]
    column_formatters = {
        "organization_status": lambda v, c, m, p: v._format_enum(
            m.organization_status, EntityStatus
        ),
        "organization_type": lambda v, c, m, p: v._format_enum(
            m.organization_type, OrganizationType
        ),
        "actions": lambda v, c, m, p: v._render_actions(m),
    }
    form_columns = [
        "organization_name",
        "organization_description",
        "organization_url",
    ]
    form_args = {
        "organization_name": {
            "render_kw": {"readonly": True},
        },
    }

    def _render_actions(self, model):
        actions = []
        return_path = escape(request.full_path)

        # View Button (always available)
        details_url = self.get_url(
            ".details_view", id=model.organization_id, url=return_path
        )
        actions.append(
            f'<a class="icon" href="{details_url}" title="View Record">'
            f'<span class="fa fa-eye"></span></a>'
        )

        # Edit Button (always available)
        edit_url = self.get_url(".edit_view", id=model.organization_id, url=return_path)
        actions.append(
            f'<a class="icon" href="{edit_url}" title="Edit Record">'
            f'<span class="fa fa-pencil"></span></a>'
        )

        return Markup(" ".join(actions))

    def on_model_change(self, form, model, is_created):
        if is_created:
            abort(403)
        else:
            # Editing: permission check + restore immutable fields
            if model.organization_id != current_user.organization_id:
                abort(403)

            # Cannot change organization_status, organization_type, and organization_name
            # through edit form, must keep original value
            self._restore_protected_fields(model)

            # All fields validation
            if not model.organization_name or not model.organization_name.strip():
                raise ValueError("Organization name is required.")

            if (
                not model.organization_description
                or not model.organization_description.strip()
            ):
                raise ValueError("Organization description is required.")

            if not model.organization_url or not model.organization_url.strip():
                raise ValueError("Organization URL is required.")

            # URL format validation
            url_check = urlparse(model.organization_url)
            if not url_check.scheme or not url_check.netloc:
                raise ValueError("Organization URL must be a valid URL format.")

    def after_model_change(self, form, model, is_created):
        client_ip = get_client_ip()
        if is_created:
            # Should not happen (creation is disabled)
            return
        else:
            logger.info(
                f"[{client_ip}] [UPDATE] - User {current_user.id}"
                f"({current_user.email}) updated Organization "
                f"#{model.organization_id} '{model.organization_name}'"
            )

        storage_root = current_app.config["STORAGE_ROOT"]

        # ----- Update Metadata -----
        transform_errors = []
        idps = Idp.query.filter_by(organization_id=model.organization_id).all()
        for idp in idps:
            if (
                idp.idp_metadata_file
                and idp.idp_edugain != EdugainStatus.ALREADY_IN.value
            ):
                try:
                    MetadataService.safe_transform(
                        entity_type="idp",
                        entity_id=idp.idp_id,
                        original_path=os.path.join(storage_root, idp.idp_metadata_file),
                        organization_id=model.organization_id,
                        raise_on_error=True,
                    )
                except Exception as exc:
                    transform_errors.append(
                        f"IdP #{idp.idp_id} ({idp.idp_entityid}): {exc}"
                    )
        sps = Sp.query.filter_by(organization_id=model.organization_id).all()
        for sp in sps:
            if (
                sp.sp_metadata_file
                and sp.sp_edugain != EdugainStatus.ALREADY_IN.value
            ):
                try:
                    MetadataService.safe_transform(
                        entity_type="sp",
                        entity_id=sp.sp_id,
                        original_path=os.path.join(storage_root, sp.sp_metadata_file),
                        organization_id=model.organization_id,
                        raise_on_error=True,
                    )
                except Exception as exc:
                    transform_errors.append(
                        f"SP #{sp.sp_id} ({sp.sp_entityid}): {exc}"
                    )

        if transform_errors:
            error_text = "; ".join(transform_errors)
            flash(
                "Organization was updated, but metadata transformation failed for: "
                f"{error_text}. Federation metadata was not regenerated.",
                "error",
            )
            logger.error(
                "[Metadata] Organization #%s transformation failed: %s",
                model.organization_id,
                error_text,
            )
            return

        try:
            self._regenerate_metadata(raise_on_error=True)
        except Exception as exc:
            flash(
                "Organization was updated and entity metadata was re-transformed, "
                "but federation metadata could not be regenerated. Please contact "
                "a federation administrator to fix metadata generation and retry the organization update.",
                "error",
            )
            logger.exception(
                "[Metadata] Organization #%s federation metadata regeneration failed: %s",
                model.organization_id,
                exc,
            )
            return

        flash(
            "Organization configuration has been updated. All entities in this "
            "organization have been re-transformed and federation metadata has "
            "been regenerated.",
            "info",
        )
