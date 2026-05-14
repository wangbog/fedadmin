import os
from flask import redirect, url_for, request, flash, abort, current_app
from flask_security import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import re
from app.modules.admin.base import BaseAdminView
from app.services.metadata import MetadataService


class MemberBaseView(BaseAdminView):
    """Base view for member admin."""

    required_roles = ["full_member", "sp_member"]

    def handle_view_exception(self, exc):
        if isinstance(exc, ValueError):
            flash(str(exc), "error")
            return redirect(request.referrer or url_for("member_admin.index"))
        return super().handle_view_exception(exc)

    def get_query(self):
        """
        Override get_query to filter by organization and add eager loading.
        This ensures users can only see their own organization's data
        and optimizes queries by pre-loading related data.
        """
        query = self.session.query(self.model).filter(
            self.model.organization_id == current_user.organization_id
        )

        # Add eager loading for organization relationship if it exists
        if hasattr(self.model, "organization"):
            query = query.options(joinedload(self.model.organization))

        return query

    def get_count_query(self):
        return self.session.query(func.count()).filter(
            self.model.organization_id == current_user.organization_id
        )

    def get_one(self, id):
        model = super().get_one(id)
        if model and model.organization_id != current_user.organization_id:
            abort(403)
        return model

    def on_form_prefill(self, form, id):
        model = self.get_one(id)
        if model and model.organization_id != current_user.organization_id:
            abort(403)

    def _inject_contact_defaults(self, form):
        """Inject default values for all contact fields (technical + security)"""
        # Technical contacts: pre-fill with current user if empty
        if not form.contact_technical_email.data:
            form.contact_technical_email.data = current_user.email
        if not form.contact_technical_name.data:
            form.contact_technical_name.data = current_user.username

        if not form.security_contact_email.data:
            form.security_contact_email.data = current_user.email
        if not form.security_contact_name.data:
            form.security_contact_name.data = current_user.username

    def _handle_edugain_already_in(self, model, metadata_namegen):
        """Common handler for eduGAIN ALREADY_IN mode: fetch metadata, save temp file"""
        entity_id_attr = model.entity_type + "_entityid"
        entity_id = getattr(model, entity_id_attr)

        if not entity_id:
            raise ValueError("Entity ID is required for entities already in eduGAIN.")

        # Try to fetch metadata from eduGAIN to verify entity exists
        success, result = MetadataService.fetch_edugain_metadata(entity_id)
        if not success:
            raise ValueError(f"Could not retrieve entity from eduGAIN: {result}")

        # Generate temp filename using same namegen as file upload
        class FakeFile:
            filename = "metadata.xml"

        temp_path = metadata_namegen(model, FakeFile())

        # Save downloaded metadata to temp location
        storage_root = current_app.config["STORAGE_ROOT"]
        full_temp_path = os.path.join(storage_root, temp_path)
        os.makedirs(os.path.dirname(full_temp_path), exist_ok=True)
        with open(full_temp_path, "w", encoding="utf-8") as f:
            f.write(result)

        # Calculate SHA1 hash of the metadata
        sha1_hash = MetadataService.calculate_sha1(result)

        # Assign temp path to model (will be moved in after_model_change)
        setattr(model, model.entity_type + "_metadata_file", temp_path)

        # Store the SHA1 hash
        sha1_attr = model.entity_type + "_metadata_sha1"
        setattr(model, sha1_attr, sha1_hash)

        # Automatically extract and set scope for IdP entities
        if model.entity_type == "idp":
            extracted_scope = MetadataService.extract_scope_from_idp_metadata(result)
            setattr(model, "idp_scope", extracted_scope)

        # Set nullable=False fields
        setattr(model, model.entity_type + "_description", "")
        setattr(model, model.entity_type + "_logo", "")
        setattr(model, "contact_technical_name", "")
        setattr(model, "contact_technical_email", "")
        setattr(model, "security_contact_name", "")
        setattr(model, "security_contact_email", "")

        return result

    def _validate_entity(self, model):
        """
        Entity validation for eduGAIN YES/NO (except ALREADY_IN) mode.
        This validation can not be bypassed under any circumstances.
        Applies to both IdP and SP entities.
        """

        # Entity name is ALWAYS required
        name_attr = model.entity_type + "_name"
        name_value = getattr(model, name_attr)
        if not name_value or not name_value.strip():
            raise ValueError("Entity name is required.")

        # Entity description is ALWAYS required
        desc_attr = model.entity_type + "_description"
        desc_value = getattr(model, desc_attr)
        if not desc_value or not desc_value.strip():
            raise ValueError("Entity description is required.")

        # Technical contacts are ALWAYS required
        if not model.contact_technical_name or not model.contact_technical_name.strip():
            raise ValueError("Technical contact name is required.")

        if not model.contact_technical_email:
            raise ValueError("Technical contact email is required.")

        # Validate email format using standard regex
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, model.contact_technical_email):
            raise ValueError("Invalid technical contact email format.")

        # Security contacts are REQUIRED ONLY if Sirtfi is enabled
        if model.sirtfi_enabled:
            if (
                not model.security_contact_name
                or not model.security_contact_name.strip()
            ):
                raise ValueError(
                    "Security contact name is required when Sirtfi is enabled."
                )

            if not model.security_contact_email:
                raise ValueError(
                    "Security contact email is required when Sirtfi is enabled."
                )

            if not re.match(email_regex, model.security_contact_email):
                raise ValueError("Invalid security contact email format.")

        # Validate logo URL
        logo_attr = model.entity_type + "_logo"
        logo_value = getattr(model, logo_attr)
        if not logo_value or not logo_value.strip():
            raise ValueError(f"Entity logo URL is required.")

        url_regex = r"^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$"
        if not re.match(url_regex, logo_value):
            raise ValueError(f"Invalid entity logo URL format.")

    def _validate_entity_edugain(self, model):
        """
        Entity validation for eduGAIN ALREADY_IN mode.
        This validation can not be bypassed under any circumstances.
        Applies to both IdP and SP entities.
        """

        # Entity name is ALWAYS required
        name_attr = model.entity_type + "_name"
        name_value = getattr(model, name_attr)
        if not name_value or not name_value.strip():
            raise ValueError("Entity name is required.")
