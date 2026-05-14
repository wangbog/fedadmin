import os
import shutil
from flask import flash, redirect, url_for, abort, current_app, request
from flask_security import current_user
from flask_admin import expose
from flask_admin.form import FileUploadField
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup
from wtforms import SelectField
from werkzeug.datastructures import FileStorage
from app.services.metadata import MetadataService
from app.services.metadata_validator import MetadataValidator
from app.extensions import db
from app.modules.admin.base import BaseAdminView
from app.models.entity_status import EntityStatus
from app.models.edugain_status import EdugainStatus
from app.modules.admin.widgets import SimpleFileUploadInput
from app.utils.file_helpers import (
    safe_ext,
    sp_metadata_namegen,
    move_uploaded_file,
    validate_xml,
)
from app.utils.security_helpers import csrf_protected
from app.utils.logging_helpers import logger, get_client_ip
from .base import MemberBaseView


class MemberSpModelView(MemberBaseView):

    # Define protected fields that cannot be modified through the edit form
    PROTECTED_FIELDS = ["sp_edugain"]

    extra_js = [
        "/static/js/utils.js",
        "/static/js/metadata.js",
        "/static/js/form_utils.js",
        "/static/js/entity_forms.js",
    ]
    column_list = [
        "sp_status",
        "sp_name",
        "sp_entityid",
        "sp_edugain",
        "actions",
    ]
    column_filters = [
        "sp_status",
        "sp_name",
        "sp_entityid",
        "sp_edugain",
    ]
    column_choices = {
        "sp_status": [(e.value, e.name) for e in EntityStatus],
        "sp_edugain": [(e.value, e.name) for e in EdugainStatus],
    }
    column_details_list = [
        "sp_name",
        "sp_status",
        "sp_description",
        "sp_entityid",
        "sp_edugain",
        "sp_logo",
        "download_metadata",
        "contact_technical_name",
        "contact_technical_email",
        "sirtfi_enabled",
        "security_contact_name",
        "security_contact_email",
        "coco_enabled",
        "rs_enabled",
        "information_url",
        "privacy_statement_url",
    ]
    column_formatters = {
        "sp_status": lambda v, c, m, p: v._format_enum(m.sp_status, EntityStatus),
        "sp_edugain": lambda v, c, m, p: v._format_enum(m.sp_edugain, EdugainStatus),
        "sp_logo": lambda v, c, m, p: (
            Markup(f'<img src="{m.sp_logo}" style="max-height:50px;">')
            if m.sp_logo
            else ""
        ),
        "download_metadata": lambda v, c, m, p: v._render_download_button(m),
        "actions": lambda v, c, m, p: v._render_actions(m),
    }
    column_descriptions = {
        **BaseAdminView.column_descriptions,
        **{
            "rs_enabled": 'Enable if the SP meets the R&S entity category requirements. <a href="https://refeds.org/category/research-and-scholarship" target="_blank">R&S specification</a>',
        },
    }
    form_columns = [
        "sp_name",
        "sp_edugain",
        "sp_description",
        "sp_entityid",
        "sp_logo",
        "sp_metadata_file",
        "contact_technical_name",
        "contact_technical_email",
        "sirtfi_enabled",
        "security_contact_name",
        "security_contact_email",
        "coco_enabled",
        "rs_enabled",
        "information_url",
        "privacy_statement_url",
    ]
    form_overrides = {
        "sp_edugain": SelectField,
        "sp_metadata_file": FileUploadField,
    }
    form_args = {
        "sp_edugain": {
            "label": "SP eduGAIN Status",
            "choices": [(e.value, e.name) for e in EdugainStatus],
            "coerce": int,
        },
        "sp_entityid": {
            "label": "SP Entity ID",
        },
        "contact_technical_name": {
            "label": "Technical Contact Name",
        },
        "contact_technical_email": {
            "label": "Technical Contact Email",
        },
        "security_contact_name": {
            "label": "Security Contact Name",
        },
        "security_contact_email": {
            "label": "Security Contact Email",
        },
        "sirtfi_enabled": {
            "label": "Sirtfi Compliant",
        },
        "coco_enabled": {
            "label": "Code of Conduct Compliant",
        },
        "rs_enabled": {
            "label": "Research & Scholarship Category",
        },
        "information_url": {
            "label": "Information URL",
        },
        "privacy_statement_url": {
            "label": "Privacy Statement URL",
        },
        "sp_metadata_file": {
            "label": "Metadata File",
            "base_path": current_app.config["STORAGE_ROOT"],
            "relative_path": "",
            "namegen": sp_metadata_namegen,
            "allowed_extensions": ["xml"],
            "widget": SimpleFileUploadInput(),
        },
    }

    def _render_download_button(self, model):
        if model.sp_metadata_file:
            return Markup(
                f'<a href="{url_for("main.download_file", entity_type="sp-metadata", entity_id=model.sp_id)}" '
                f'class="btn btn-sm btn-primary">Download</a>'
            )
        return ""

    def _render_actions(self, model):
        actions = []
        return_path = request.full_path

        # View Button (always available)
        details_url = self.get_url(".details_view", id=model.sp_id, url=return_path)
        actions.append(
            f'<a class="icon" href="{details_url}" title="View Record">'
            f'<span class="fa fa-eye"></span></a>'
        )

        # Edit Button
        if model.sp_status == EntityStatus.INIT.value:
            edit_url = self.get_url(".edit_view", id=model.sp_id, url=return_path)
            actions.append(
                f'<a class="icon" href="{edit_url}" title="Edit Record">'
                f'<span class="fa fa-pencil"></span></a>'
            )

        # Delete Button
        if model.sp_status == EntityStatus.INIT.value:
            delete_url = self.get_url(".delete")
            csrf_token = generate_csrf()
            actions.append(
                f'<form class="icon" method="POST" action="{delete_url}">'
                f'<input name="id" type="hidden" value="{model.sp_id}">'
                f'<input name="url" type="hidden" value="{return_path}">'
                f'<input name="csrf_token" type="hidden" value="{csrf_token}">'
                "<button onclick=\"return faHelpers.safeConfirm('Are you sure you "
                'want to delete this record?\');" title="Delete Record">'
                '<span class="fa fa-trash"></span></button></form>'
            )

        # Download Button (always available, if metadata file exists)
        if model.sp_metadata_file:
            download_url = url_for(
                "main.download_file", entity_type="sp-metadata", entity_id=model.sp_id
            )
            actions.append(
                f'<a class="icon" href="{download_url}" title="Download Metadata">'
                f'<span class="fa fa-file-code-o"></span></a>'
            )

        # Apply Button
        if model.sp_status == EntityStatus.INIT.value:
            apply_url = self.get_url(".apply")
            csrf_token = generate_csrf()
            actions.append(
                f'<form class="icon" method="POST" action="{apply_url}">'
                f'<input name="id" type="hidden" value="{model.sp_id}">'
                f'<input name="url" type="hidden" value="{return_path}">'
                f'<input name="csrf_token" type="hidden" value="{csrf_token}">'
                '<button onclick="return faHelpers.safeConfirm(\'Submit this entity for approval?\');" title="Submit for approval">'
                '<span class="fa fa-paper-plane"></span></button></form>'
            )

        # Cancel Button
        if model.sp_status == EntityStatus.APPROVING.value:
            cancel_url = self.get_url(".cancel")
            csrf_token = generate_csrf()
            actions.append(
                f'<form class="icon" method="POST" action="{cancel_url}">'
                f'<input name="id" type="hidden" value="{model.sp_id}">'
                f'<input name="url" type="hidden" value="{return_path}">'
                f'<input name="csrf_token" type="hidden" value="{csrf_token}">'
                '<button onclick="return faHelpers.safeConfirm(\'Cancel this application? It will become INIT again.\');" title="Cancel application">'
                '<span class="fa fa-times-circle"></span></button></form>'
            )

        # Withdraw Button
        if model.sp_status == EntityStatus.READY.value:
            withdraw_url = self.get_url(".withdraw")
            csrf_token = generate_csrf()
            actions.append(
                f'<form class="icon" method="POST" action="{withdraw_url}">'
                f'<input name="id" type="hidden" value="{model.sp_id}">'
                f'<input name="url" type="hidden" value="{return_path}">'
                f'<input name="csrf_token" type="hidden" value="{csrf_token}">'
                '<button onclick="return faHelpers.safeConfirm(\'Withdraw this entity? It will become INIT again.\');" title="Withdraw">'
                '<span class="fa fa-undo"></span></button></form>'
            )

        return Markup(" ".join(actions))

    @expose("/apply/", methods=["POST"])
    @csrf_protected
    def apply(self):
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [APPLY FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to apply SP: "
                "Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [APPLY FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to apply SP "
                f"#{record_id}: Entity not found"
            )
            return redirect(redirect_url)
        if model.organization_id != current_user.organization_id:
            logger.warning(
                f"[{client_ip}] [APPLY FAILED] - User "
                f"{current_user.id}({current_user.email}) attempted to apply "
                f"SP #{model.sp_id} '{model.sp_name}': Permission denied"
            )
            abort(403)
        if model.sp_status != EntityStatus.INIT.value:
            flash("This entity is not pending application.", "warning")
            logger.warning(
                f"[{client_ip}] [APPLY FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to apply SP "
                f"#{model.sp_id} '{model.sp_name}': Not in INIT status"
            )
            return redirect(redirect_url)

        model.sp_status = EntityStatus.APPROVING.value
        db.session.commit()
        flash(f'Entity "{model.sp_name}" applied.', "success")
        logger.info(
            f"[{client_ip}] [APPLY] - User "
            f"{current_user.id}({current_user.email}) applied SP "
            f"#{model.sp_id} '{model.sp_name}'"
        )
        return redirect(redirect_url)

    @expose("/cancel/", methods=["POST"])
    @csrf_protected
    def cancel(self):
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [CANCEL FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to cancel SP: "
                "Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [CANCEL FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to cancel SP "
                f"#{record_id}: Entity not found"
            )
            return redirect(redirect_url)
        if model.organization_id != current_user.organization_id:
            logger.warning(
                f"[{client_ip}] [CANCEL FAILED] - User "
                f"{current_user.id}({current_user.email}) attempted to cancel "
                f"SP #{model.sp_id} '{model.sp_name}': Permission denied"
            )
            abort(403)
        if model.sp_status != EntityStatus.APPROVING.value:
            flash("Only APPROVING entities can be canceled.", "warning")
            logger.warning(
                f"[{client_ip}] [CANCEL FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to cancel SP "
                f"#{model.sp_id} '{model.sp_name}': Not in APPROVING status"
            )
            return redirect(redirect_url)

        model.sp_status = EntityStatus.INIT.value
        db.session.commit()
        flash(f'Application for "{model.sp_name}" has been canceled.', "success")
        logger.info(
            f"[{client_ip}] [CANCEL] - User "
            f"{current_user.id}({current_user.email}) canceled SP "
            f"#{model.sp_id} '{model.sp_name}'"
        )
        return redirect(redirect_url)

    @expose("/withdraw/", methods=["POST"])
    @csrf_protected
    def withdraw(self):
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [WITHDRAW FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to withdraw SP: "
                "Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [WITHDRAW FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to withdraw SP "
                f"#{record_id}: Entity not found"
            )
            return redirect(redirect_url)
        if model.organization_id != current_user.organization_id:
            logger.warning(
                f"[{client_ip}] [WITHDRAW FAILED] - User "
                f"{current_user.id}({current_user.email}) attempted to withdraw "
                f"SP #{model.sp_id} '{model.sp_name}': Permission denied"
            )
            abort(403)
        if model.sp_status != EntityStatus.READY.value:
            flash("Only READY entities can be withdrawn.", "warning")
            logger.warning(
                f"[{client_ip}] [WITHDRAW FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to withdraw SP "
                f"#{model.sp_id} '{model.sp_name}': Not in READY status"
            )
            return redirect(redirect_url)

        model.sp_status = EntityStatus.INIT.value
        db.session.commit()
        flash(f'Entity "{model.sp_name}" withdrawn, now INIT.', "success")
        logger.info(
            f"[{client_ip}] [WITHDRAW] - User "
            f"{current_user.id}({current_user.email}) withdrew SP "
            f"#{model.sp_id} '{model.sp_name}'"
        )
        self._regenerate_metadata()
        return redirect(redirect_url)

    @expose("/delete/", methods=["POST"])
    @csrf_protected
    def delete(self):
        """Custom delete endpoint for INIT status entities."""
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to delete SP: "
                "Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("Entity not found.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to delete SP "
                f"#{record_id}: Entity not found"
            )
            return redirect(redirect_url)
        if model.organization_id != current_user.organization_id:
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) attempted to delete "
                f"SP #{model.sp_id} '{model.sp_name}': Permission denied"
            )
            abort(403)
        if model.sp_status != EntityStatus.INIT.value:
            flash("Only INIT entities can be deleted.", "warning")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to delete SP "
                f"#{model.sp_id} '{model.sp_name}': Not in INIT status"
            )
            return redirect(redirect_url)

        # Delete associated files before deleting the model
        storage_root = current_app.config["STORAGE_ROOT"]
        if model.sp_metadata_file:
            meta_path = os.path.join(storage_root, model.sp_metadata_file)
            if os.path.exists(meta_path):
                try:
                    os.remove(meta_path)
                except OSError:
                    pass
            transformed = model.sp_metadata_file.replace(".xml", "-transformed.xml")
            trans_path = os.path.join(storage_root, transformed)
            if os.path.exists(trans_path):
                try:
                    os.remove(trans_path)
                except OSError:
                    pass

        entity_name = model.sp_name
        db.session.delete(model)
        db.session.commit()
        flash(f'Entity "{entity_name}" deleted.', "success")
        logger.info(
            f"[{client_ip}] [DELETE] - User "
            f"{current_user.id}({current_user.email}) deleted SP "
            f"#{record_id} '{entity_name}'"
        )
        self._regenerate_metadata_beta()
        return redirect(redirect_url)

    def create_form(self, obj=None):
        """Pre-fill technical contacts and set data attributes for security contacts."""
        form = super().create_form(obj)
        if obj is None:
            self._inject_contact_defaults(form)

            # Remove validators for ALREADY_IN mode when creating
            if form.sp_edugain.data == EdugainStatus.ALREADY_IN.value:
                form.sp_description.validators = []
                form.sp_metadata_file.validators = []
                form.sp_logo.validators = []

        return form

    def edit_form(self, obj=None):
        form = super().edit_form(obj)
        if obj:
            self._inject_contact_defaults(form)

            # Remove validators for ALREADY_IN mode when editing
            if obj.sp_edugain == EdugainStatus.ALREADY_IN.value:
                form.sp_description.validators = []
                form.sp_metadata_file.validators = []
                form.sp_logo.validators = []

            # Fix Flask Admin FileUploadField BUG: only remove DataRequired validator, keep all other validations for security
            if obj.sp_metadata_file:
                form.sp_metadata_file.validators = [
                    v
                    for v in form.sp_metadata_file.validators
                    if type(v).__name__
                    not in ["DataRequired", "Required", "InputRequired"]
                ]

            # Make sp_edugain field disabled during editing
            form.sp_edugain.render_kw = {"disabled": True}

        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            # Set common fields (status and organization)
            model.sp_status = EntityStatus.INIT.value
            model.organization_id = current_user.organization_id

            if model.sp_edugain == EdugainStatus.ALREADY_IN.value:
                # Entity validation
                self._validate_entity_edugain(model)

                self._handle_edugain_already_in(model, sp_metadata_namegen)
            else:
                # Entity validation
                self._validate_entity(model)

                if not form.sp_metadata_file.data or not isinstance(
                    form.sp_metadata_file.data, FileStorage
                ):
                    raise ValueError("Metadata file is required.")

                # Validate MIME types
                validate_xml(form.sp_metadata_file.data)

                # Temporarily disable autoflush to prevent premature database flush
                # before all required fields are set.
                # The MetadataValidator.validate() performs a DB query that could trigger autoflush.
                original_autoflush = self.session.autoflush
                try:
                    self.session.autoflush = False

                    # Validate metadata and extract entityID
                    validation = MetadataValidator.validate(
                        "sp", form.sp_metadata_file.data
                    )
                    validation.raise_if_error()

                    # Set all required fields before re-enabling autoflush
                    model.sp_entityid = validation.entity_id
                finally:
                    self.session.autoflush = original_autoflush
        else:
            # Editing: permission check + restore immutable fields
            if model.organization_id != current_user.organization_id:
                abort(403)

            if model.sp_status != EntityStatus.INIT.value:
                raise ValueError("Only INIT entities can be edited.")

            # Set common fields (status and organization)
            model.sp_status = EntityStatus.INIT.value
            model.organization_id = current_user.organization_id

            # Cannot change protected fields through edit form, must keep original value
            self._restore_protected_fields(model)

            # Handle ALREADY_IN mode for edit
            if model.sp_edugain == EdugainStatus.ALREADY_IN.value:
                # Entity validation
                self._validate_entity_edugain(model)

                self._handle_edugain_already_in(model, sp_metadata_namegen)
            else:
                # Entity validation
                self._validate_entity(model)

                # If new metadata file uploaded, validate and extract entityID
                if form.sp_metadata_file.data and isinstance(
                    form.sp_metadata_file.data, FileStorage
                ):
                    validate_xml(form.sp_metadata_file.data)
                    validation = MetadataValidator.validate(
                        "sp",
                        form.sp_metadata_file.data,
                        exclude_id=model.sp_id,
                    )
                    validation.raise_if_error()
                    model.sp_entityid = validation.entity_id

    def after_model_change(self, form, model, is_created):
        client_ip = get_client_ip()
        if is_created:
            logger.info(
                f"[{client_ip}] [CREATE] - User "
                f"{current_user.id}({current_user.email}) created SP "
                f"#{model.sp_id} '{model.sp_name}'"
            )
        else:
            logger.info(
                f"[{client_ip}] [UPDATE] - User "
                f"{current_user.id}({current_user.email}) updated SP "
                f"#{model.sp_id} '{model.sp_name}'"
            )

        storage_root = current_app.config["STORAGE_ROOT"]

        if is_created:
            organization_id = str(model.organization_id)
            sp_id = str(model.sp_id)

            # Get old paths (for cleanup)
            old_metadata_relative = None
            original = self.model.query.get(model.sp_id)
            if original:
                old_metadata_relative = original.sp_metadata_file

            # ----- Handle Metadata -----
            if model.sp_metadata_file:
                final_path = os.path.join(storage_root, model.sp_metadata_file)
                ext = safe_ext(model.sp_metadata_file)
                if not ext:
                    raise ValueError("Invalid metadata file extension")
                final_filename = f"sp-{sp_id}-metadata.{ext}"
                final_relative = f"private/members/{organization_id}/{final_filename}"
                # Move temp file to final location
                if os.path.exists(final_path):
                    move_uploaded_file(
                        storage_root,
                        model.sp_metadata_file,
                        final_relative,
                        old_metadata_relative,
                        delete_old=True,
                    )
                    model.sp_metadata_file = final_relative
                    db.session.commit()

        # Always process metadata (both create and edit modes)
        if model.sp_metadata_file:
            final_path = os.path.join(storage_root, model.sp_metadata_file)
            if os.path.exists(final_path):
                if model.sp_edugain == EdugainStatus.ALREADY_IN.value:
                    # ALREADY_IN: just copy as transformed
                    transformed_path = final_path.replace(".xml", "-transformed.xml")
                    shutil.copy(final_path, transformed_path)
                    logger.info(
                        f"[SP] Created transformed metadata copy for eduGAIN entity "
                        f"{model.sp_entityid}"
                    )
                else:
                    # Normal mode: run full transformation
                    MetadataService.safe_transform(
                        entity_type="sp",
                        entity_id=model.sp_id,
                        original_path=final_path,
                        organization_id=model.organization_id,
                    )

        # Regenerate federation metadata (only beta)
        self._regenerate_metadata_beta()
