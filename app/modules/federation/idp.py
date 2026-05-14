from flask import flash, redirect, url_for, request
from flask_admin import expose
from flask_wtf.csrf import generate_csrf
from flask_security import current_user
from markupsafe import Markup
from app.extensions import db
from app.utils.security_helpers import csrf_protected
from app.utils.logging_helpers import logger, get_client_ip
from app.modules.admin.base import BaseAdminView
from app.models.entity_status import EntityStatus
from app.models.edugain_status import EdugainStatus
from .base import FederationBaseView


class FederationIdpModelView(FederationBaseView):
    column_list = [
        "organization_name",
        "idp_status",
        "idp_name",
        "idp_entityid",
        "idp_edugain",
        "actions",
    ]
    column_filters = [
        "organization.organization_name",
        "idp_status",
        "idp_name",
        "idp_entityid",
        "idp_edugain",
    ]
    column_choices = {
        "idp_status": [(e.value, e.name) for e in EntityStatus],
        "idp_edugain": [(e.value, e.name) for e in EdugainStatus],
    }
    column_labels = {
        "organization.organization_name": "Organization Name",
    }
    column_sortable_list = [
        ("organization_name", "organization.organization_name"),
        "idp_status",
        "idp_name",
        "idp_entityid",
        "idp_edugain",
    ]
    column_details_list = [
        "idp_id",
        "organization_name",
        "idp_status",
        "idp_name",
        "idp_description",
        "idp_scope",
        "idp_entityid",
        "idp_edugain",
        "idp_logo",
        "download_metadata",
        "contact_technical_name",
        "contact_technical_email",
        "sirtfi_enabled",
        "security_contact_name",
        "security_contact_email",
        "rs_enabled",
    ]
    column_formatters = {
        "organization_name": lambda v, c, m, p: (
            m.organization.organization_name if m.organization else ""
        ),
        "idp_status": lambda v, c, m, p: v._format_enum(m.idp_status, EntityStatus),
        "idp_edugain": lambda v, c, m, p: v._format_enum(m.idp_edugain, EdugainStatus),
        "idp_logo": lambda v, c, m, p: (
            Markup(
                f'<img src="{url_for("main.public_storage", filename=m.idp_logo)}" style="max-height:50px;">'
            )
            if m.idp_logo
            else ""
        ),
        "download_metadata": lambda v, c, m, p: v._render_download_button(m),
        "actions": lambda v, c, m, p: v._render_actions(m),
    }
    column_descriptions = {
        **BaseAdminView.column_descriptions,
        **{
            "rs_enabled": 'Enable if the IdP supports R&S entity category (i.e., will release attributes to R&S SPs). <a href="https://refeds.org/category/research-and-scholarship" target="_blank">R&S specification</a>',
        },
    }

    def _render_download_button(self, model):
        if model.idp_metadata_file:
            return Markup(
                f'<a href="{url_for("main.download_file", entity_type="idp-metadata", entity_id=model.idp_id)}" '
                f'class="btn btn-sm btn-primary">Download</a>'
            )
        return ""

    def _render_actions(self, model):
        actions = []
        return_path = request.full_path

        # View Button (always available)
        details_url = self.get_url(".details_view", id=model.idp_id, url=return_path)
        actions.append(
            f'<a class="icon" href="{details_url}" title="View Record">'
            f'<span class="fa fa-eye"></span></a>'
        )

        # Download Button (always available, if metadata file exists)
        if model.idp_metadata_file:
            download_url = url_for(
                "main.download_file", entity_type="idp-metadata", entity_id=model.idp_id
            )
            actions.append(
                f'<a class="icon" href="{download_url}" title="Download Metadata">'
                f'<span class="fa fa-file-code-o"></span></a>'
            )

        # Approve Button
        if model.idp_status == EntityStatus.APPROVING.value:
            approve_url = self.get_url(".approve")
            csrf_token = generate_csrf()
            actions.append(
                f"""
            <form class="icon" method="POST" action="{approve_url}">
                <input name="id" type="hidden" value="{model.idp_id}">
                <input name="url" type="hidden" value="{return_path}">
                <input name="csrf_token" type="hidden" value="{csrf_token}">
                <button onclick="return confirm('Approve this entity?');" title="Approve">
                    <span class="fa fa-check"></span>
                </button>
            </form>
            """
            )

        # Reject Button
        if model.idp_status == EntityStatus.APPROVING.value:
            reject_url = self.get_url(".reject")
            csrf_token = generate_csrf()
            actions.append(
                f"""
            <form class="icon" method="POST" action="{reject_url}">
                <input name="id" type="hidden" value="{model.idp_id}">
                <input name="url" type="hidden" value="{return_path}">
                <input name="csrf_token" type="hidden" value="{csrf_token}">
                <button onclick="return confirm('Reject this entity? It will become INIT.');" title="Reject">
                    <span class="fa fa-times"></span>
                </button>
            </form>
            """
            )

        return Markup(" ".join(actions))

    @expose("/approve/", methods=["POST"])
    @csrf_protected
    def approve(self):
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [APPROVE FAILED] - User {current_user.id}({current_user.email}) failed to approve IdP: Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [APPROVE FAILED] - User {current_user.id}({current_user.email}) failed to approve IdP #{record_id}: Entity not found"
            )
            return redirect(redirect_url)
        if model.idp_status != EntityStatus.APPROVING.value:
            flash("This entity is not pending approval.", "warning")
            logger.warning(
                f"[{client_ip}] [APPROVE FAILED] - User {current_user.id}({current_user.email}) failed to approve IdP #{model.idp_id} '{model.idp_name}': Not in APPROVING status"
            )
            return redirect(redirect_url)

        model.idp_status = EntityStatus.READY.value
        db.session.commit()
        flash(f'Entity "{model.idp_name}" approved.', "success")
        logger.info(
            f"[{client_ip}] [APPROVE] - User {current_user.id}({current_user.email}) approved IdP #{model.idp_id} '{model.idp_name}'"
        )
        self._regenerate_metadata()
        return redirect(redirect_url)

    @expose("/reject/", methods=["POST"])
    @csrf_protected
    def reject(self):
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [REJECT FAILED] - User {current_user.id}({current_user.email}) failed to reject IdP: Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [REJECT FAILED] - User {current_user.id}({current_user.email}) failed to reject IdP #{record_id}: Entity not found"
            )
            return redirect(redirect_url)
        if model.idp_status != EntityStatus.APPROVING.value:
            flash("This entity is not pending approval.", "warning")
            logger.warning(
                f"[{client_ip}] [REJECT FAILED] - User {current_user.id}({current_user.email}) failed to reject IdP #{model.idp_id} '{model.idp_name}': Not in APPROVING status"
            )
            return redirect(redirect_url)

        model.idp_status = EntityStatus.INIT.value
        db.session.commit()
        flash(f'Entity "{model.idp_name}" rejected, now INIT.', "success")
        logger.info(
            f"[{client_ip}] [REJECT] - User {current_user.id}({current_user.email}) rejected IdP #{model.idp_id} '{model.idp_name}'"
        )
        return redirect(redirect_url)
