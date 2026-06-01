import os
from flask import flash, request, redirect, current_app
from flask_security import current_user
from markupsafe import Markup, escape
from flask_admin import expose
from flask_wtf.csrf import generate_csrf
from wtforms import SelectField
from app.models import User, Idp, Sp
from app.models.edugain_status import EdugainStatus
from app.models.entity_status import EntityStatus
from app.models.organization_type import OrganizationType
from app.extensions import db
from app.utils.security_helpers import csrf_protected
from app.utils.logging_helpers import logger, get_client_ip
from app.utils.url_helpers import form_redirect_target, is_valid_http_url
from app.services.metadata import MetadataService
from app.utils.role_helpers import assign_user_roles
from .base import FederationBaseView


class FederationOrganizationModelView(FederationBaseView):
    can_create = True
    can_edit = True

    column_list = [
        "organization_type",
        "organization_status",
        "organization_name",
        "actions",
    ]
    column_filters = [
        "organization_type",
        "organization_status",
        "organization_name",
    ]
    column_choices = {
        "organization_type": [(e.value, e.name) for e in OrganizationType],
        "organization_status": [(e.value, e.name) for e in EntityStatus],
    }
    column_details_list = [
        "organization_id",
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
        "organization_type",
        "organization_status",
        "organization_name",
        "organization_description",
        "organization_url",
    ]
    form_overrides = {
        "organization_status": SelectField,
        "organization_type": SelectField,
    }
    form_args = {
        "organization_type": {
            "choices": [(e.value, e.name) for e in OrganizationType],
            "coerce": int,
        },
        "organization_status": {
            "choices": [(e.value, e.name) for e in EntityStatus],
            "coerce": int,
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

        # Delete Button (only if not the current user's organization)
        if current_user.organization_id != model.organization_id:
            delete_url = self.get_url(".delete")
            csrf_token = generate_csrf()
            actions.append(
                f'<form class="icon" method="POST" action="{delete_url}">'
                f'<input name="id" type="hidden" value="{model.organization_id}">'
                f'<input name="url" type="hidden" value="{return_path}">'
                f'<input name="csrf_token" type="hidden" value="{csrf_token}">'
                "<button onclick=\"return faHelpers.safeConfirm('Are you sure you "
                'want to delete this record?\');" title="Delete Record">'
                '<span class="fa fa-trash"></span></button></form>'
            )

        return Markup(" ".join(actions))

    @expose("/delete/", methods=["POST"])
    @csrf_protected
    def delete(self):
        """Custom delete endpoint for organizations (cannot delete current user's organization)."""
        redirect_url = form_redirect_target(self.get_url(".index_view"))
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User {current_user.id}"
                f"({current_user.email}) failed to delete Organization: "
                f"Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.get(self.model, record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User {current_user.id}"
                f"({current_user.email}) failed to delete Organization "
                f"#{record_id}: Entity not found"
            )
            return redirect(redirect_url)

        # Check if this is the current user's organization
        if current_user.organization_id == model.organization_id:
            flash(
                "Cannot delete the organization you are currently associated with.",
                "error",
            )
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User {current_user.id}"
                f"({current_user.email}) attempted to delete their own organization "
                f"#{model.organization_id} '{model.organization_name}'"
            )
            return redirect(redirect_url)

        # Check if there are users under this organization
        users_in_org = User.query.filter_by(
            organization_id=model.organization_id
        ).count()
        if users_in_org > 0:
            flash(
                f"Cannot delete organization with {users_in_org} active users. Please remove all users first.",
                "error",
            )
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User {current_user.id}"
                f"({current_user.email}) attempted to delete organization "
                f"#{model.organization_id} '{model.organization_name}' "
                f"with {users_in_org} active users"
            )
            return redirect(redirect_url)

        # Check if there are IdPs under this organization
        idps_in_org = Idp.query.filter_by(organization_id=model.organization_id).count()
        if idps_in_org > 0:
            flash(
                f"Cannot delete organization with {idps_in_org} IdP entities. Please remove all IdPs first.",
                "error",
            )
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User {current_user.id}"
                f"({current_user.email}) attempted to delete organization "
                f"#{model.organization_id} '{model.organization_name}' "
                f"with {idps_in_org} IdP entities"
            )
            return redirect(redirect_url)

        # Check if there are SPs under this organization
        sps_in_org = Sp.query.filter_by(organization_id=model.organization_id).count()
        if sps_in_org > 0:
            flash(
                f"Cannot delete organization with {sps_in_org} SP entities. Please remove all SPs first.",
                "error",
            )
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User {current_user.id}"
                f"({current_user.email}) attempted to delete organization "
                f"#{model.organization_id} '{model.organization_name}' "
                f"with {sps_in_org} SP entities"
            )
            return redirect(redirect_url)

        entity_name = model.organization_name
        db.session.delete(model)
        db.session.commit()
        flash(f'Entity "{entity_name}" deleted.', "success")
        logger.info(
            f"[{client_ip}] [DELETE] - User {current_user.id}"
            f"({current_user.email}) deleted Organization #{record_id} "
            f"'{entity_name}'"
        )
        # self._regenerate_metadata_beta()
        return redirect(redirect_url)

    def on_model_change(self, form, model, is_created):
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

        if not is_valid_http_url(model.organization_url):
            raise ValueError("Organization URL must be a valid URL format.")

        if not is_created:
            # Get old values
            old_organization_type = self._get_old_field_value(
                model, "organization_type"
            )
            old_organization_status = self._get_old_field_value(
                model, "organization_status"
            )

            # Check if is changing own organization
            if current_user.organization_id == model.organization_id:
                if old_organization_type != model.organization_type:
                    raise ValueError(
                        "Cannot modify the organization type of your own organization."
                    )

                if old_organization_status != model.organization_status:
                    raise ValueError(
                        "Cannot modify the organization status of your own organization."
                    )

            # Check if organization_type is being changed
            if old_organization_type != model.organization_type:
                # 1. Restriction: Cannot change non-FEDERATION_ADMIN to FEDERATION_ADMIN
                if (
                    old_organization_type != OrganizationType.FEDERATION_ADMIN.value
                    and model.organization_type
                    == OrganizationType.FEDERATION_ADMIN.value
                ):
                    raise ValueError(
                        "Cannot change organization type to FEDERATION_ADMIN."
                    )

                # 2. Restriction: Cannot change from FULL_MEMBER to SP_MEMBER if there are IdPs
                if (
                    old_organization_type == OrganizationType.FULL_MEMBER.value
                    and model.organization_type == OrganizationType.SP_MEMBER.value
                ):
                    idps_in_org = Idp.query.filter_by(
                        organization_id=model.organization_id
                    ).count()
                    if idps_in_org > 0:
                        raise ValueError(
                            "Cannot change organization type to SP_MEMBER "
                            f"when there are {idps_in_org} IdP entities. "
                            "Please remove all IdPs first."
                        )

                # 3. Reset user roles if organization_type is changed
                users_in_org = User.query.filter_by(
                    organization_id=model.organization_id
                ).all()

                for user in users_in_org:
                    # Reset user roles based on the new organization type
                    assign_user_roles(user, model)

    def after_model_change(self, form, model, is_created):
        client_ip = get_client_ip()
        if is_created:
            logger.info(
                f"[{client_ip}] [CREATE] - User {current_user.id}"
                f"({current_user.email}) created Organization "
                f"#{model.organization_id} '{model.organization_name}'"
            )
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
                "but federation metadata could not be regenerated. Check the signing "
                "certificate, pyFF output, and server logs, then retry the organization update.",
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
