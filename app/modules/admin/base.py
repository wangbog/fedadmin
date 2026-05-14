import pytz
from flask import redirect, url_for, request, current_app
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from flask_security import current_user
from markupsafe import Markup
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import get_history
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from app.services.metadata import MetadataService
from app.models.entity_status import EntityStatus
from app.utils.logging_helpers import logger, get_client_ip


class BaseAdminView(ModelView):
    """Base class for all admin views, handling common functionality."""

    extra_css = ["/static/css/admin.css"]

    # Define protected fields that cannot be modified through the edit form
    PROTECTED_FIELDS = []

    can_view_details = True
    can_delete = False  # Disable built-in delete (we use custom delete buttons in _render_actions)
    column_display_actions = False
    form_base_class = SecureForm  # Enable CSRF protection for forms in Flask-Admin

    # Subclasses must define `required_roles` as a list or override `is_accessible`
    required_roles = []  # e.g., ['federation'] or ['full_member', 'sp_member']

    # Subclasses can override this dictionary to provide field descriptions
    column_descriptions = {
        # common fields
        "download_metadata": "Download the metadata file.",
        "contact_technical_name": (
            "Name of the technical contact. Required. See: "
            '<a href="https://technical.edugain.org/documents" target="_blank">'
            "eduGAIN SAML Profile</a>"
        ),
        "contact_technical_email": (
            "Email address of the technical contact. Required. See: "
            '<a href="https://technical.edugain.org/documents" target="_blank">'
            "eduGAIN SAML Profile</a>"
        ),
        "sirtfi_enabled": (
            "Enable if the entity complies with REFEDS Sirtfi framework. "
            '<a href="https://refeds.org/sirtfi" target="_blank">'
            "Sirtfi specification</a>"
        ),
        "security_contact_name": "Name of the security contact (required if Sirtfi enabled).",
        "security_contact_email": "Email address of the security contact (required if Sirtfi enabled).",
        # idp specific fields
        "idp_entityid": "Entity ID of the IdP, extracted from the uploaded metadata.",
        "idp_scope": "shibmd:Scope of the IdP, extracted from the uploaded metadata.",
        "idp_edugain": "Whether this IdP should be included in the eduGAIN metadata feed.",
        "idp_logo": (
            "The logo image url for the IdP."
            "It will be included in the metadata as mdui:Logo."
        ),
        "idp_metadata_file": "Upload the SAML metadata file of the IdP.",
        # sp specific fields
        "sp_entityid": "Entity ID of the SP, extracted from the uploaded metadata.",
        "sp_edugain": "Whether this SP should be included in the eduGAIN metadata feed.",
        "sp_logo": (
            "The logo image url for the SP."
            "It will be included in the metadata as mdui:Logo."
        ),
        "sp_metadata_file": "Upload the SAML metadata file of the SP.",
        "coco_enabled": (
            "Enable if the SP complies with REFEDS Code of Conduct (v2). "
            '<a href="https://refeds.org/category/code-of-conduct" '
            'target="_blank">Code of Conduct v2</a>'
        ),
        "information_url": (
            "URL of a page describing the service (recommended for R&S). "
            '<a href="https://refeds.org/category/research-and-scholarship" '
            'target="_blank">R&S specification</a>'
        ),
        "privacy_statement_url": (
            "URL of the privacy statement (recommended). See: "
            '<a href="https://technical.edugain.org/documents" '
            'target="_blank">eduGAIN SAML Profile</a>'
        ),
    }

    #    def __init__(self, model, session, **kwargs):
    #        super().__init__(model, session, **kwargs)
    #
    #        # Add formatters for details view to display description below field name
    #        for col in self.column_details_list or []:
    #            if col not in self.column_formatters:
    #                # Create closure to capture field name
    #                def make_formatter(field):
    #                    def formatter(v, c, m, p):
    #                        value = getattr(m, field, "")
    #                        desc = self.column_descriptions.get(field, "")
    #                        if desc:
    #                            return Markup(
    #                                f'{value}<br/><small class="text-muted">{desc}</small>'
    #                            )
    #                        return value
    #
    #                    return formatter
    #
    #                self.column_formatters[col] = make_formatter(col)

    def is_accessible(self):
        """Access control: role based."""
        if not current_user.is_authenticated:
            return False
        if not self.required_roles:
            return True  # no role restriction (should be overridden)
        return any(current_user.has_role(role) for role in self.required_roles)

    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login page when access is denied."""
        return redirect(url_for("auth.login", next=request.url))

    # Show field descriptions under field name column in details view.
    def get_details_columns(self):
        """Return list of (column_name, display_label) for details view, with help text."""
        cols = self.column_details_list
        if not cols:
            cols = [c.name for c in self.model.__table__.columns]
        result = []
        for col in cols:
            label = self.get_column_name(col)  # Get original label
            desc = self.column_descriptions.get(col)
            if desc:
                # Add description below the label (supports HTML)
                label = Markup(f'{label}<br/><small class="text-muted">{desc}</small>')
            result.append((col, label))
        return result

    def get_query(self):
        """
        Override get_query to add eager loading of relationships.
        This optimizes database queries by reducing the N+1 problem.

        N+1 Problem Explanation:
        - Without optimization: 1 query to get all entities + N queries to get
          each entity's organization = N+1 total queries
        - With joinedload: 2 queries total (or 1 with JOIN)

        Example:
            # Before optimization (N+1 queries):
            idps = Idp.query.all()  # 1 query
            for idp in idps:
                print(idp.organization.name)  # N queries

            # After optimization (2 queries):
            idps = Idp.query.options(joinedload(Idp.organization)).all()
            for idp in idps:
                print(idp.organization.name)  # No additional queries
        """
        query = self.session.query(self.model)

        # Automatically eager-load 'organization' relationship if it exists
        # This is a common pattern since most models have an organization foreign key
        if hasattr(self.model, "organization"):
            query = query.options(joinedload(self.model.organization))

        return query

    def _regenerate_metadata(self):
        """Asynchronously regenerate all federation metadata files.

        This method submits the regeneration task to the background scheduler
        to avoid blocking the user request. The actual regeneration is performed
        in the background.
        """
        app = current_app._get_current_object()  # Get the actual app instance
        scheduler = current_app.scheduler

        def do_regenerate():
            """Inner function that performs the actual regeneration."""
            with app.app_context():
                MetadataService.safe_regenerate(
                    output_path_key="FEDERATION_METADATA_BETA_OUTPUT",
                    statuses=[EntityStatus.INIT.value, EntityStatus.APPROVING.value],
                )
                MetadataService.safe_regenerate(
                    output_path_key="FEDERATION_METADATA_OUTPUT",
                    statuses=[EntityStatus.READY.value],
                )
                MetadataService.safe_regenerate(
                    output_path_key="FEDERATION_METADATA_EDUGAIN_OUTPUT",
                    statuses=[EntityStatus.READY.value],
                    edugain_only=True,
                )

        # Get misfire_grace_time from config (already has default value in config.py)
        misfire_grace_time = current_app.config.get(
            "METADATA_REGENERATION_MISFIRE_GRACE_TIME"
        )

        job_id = f"regenerate_metadata_{datetime.now(pytz.UTC).timestamp()}"
        scheduler.add_job(
            do_regenerate,
            DateTrigger(run_date=datetime.now(pytz.UTC)),
            id=job_id,
            replace_existing=False,
            misfire_grace_time=misfire_grace_time,
        )

    def _regenerate_metadata_beta(self):
        """Asynchronously regenerate only the beta metadata file."""
        app = current_app._get_current_object()  # Get the actual app instance
        scheduler = current_app.scheduler

        def do_regenerate():
            with app.app_context():
                MetadataService.safe_regenerate(
                    output_path_key="FEDERATION_METADATA_BETA_OUTPUT",
                    statuses=[EntityStatus.INIT.value, EntityStatus.APPROVING.value],
                )

        # Get misfire_grace_time from config (already has default value in config.py)
        misfire_grace_time = current_app.config.get(
            "METADATA_REGENERATION_MISFIRE_GRACE_TIME"
        )

        job_id = f"regenerate_metadata_beta_{datetime.now(pytz.UTC).timestamp()}"
        scheduler.add_job(
            do_regenerate,
            DateTrigger(run_date=datetime.now(pytz.UTC)),
            id=job_id,
            replace_existing=False,
            misfire_grace_time=misfire_grace_time,
        )

    def _retransform_all_entities(self):
        """Asynchronously re-transform all entities metadata.

        This method submits the re-transformation task to the background scheduler
        to avoid blocking the user request. The actual re-transformation is performed
        in the background.
        """
        app = current_app._get_current_object()
        scheduler = current_app.scheduler

        def do_retransform():
            with app.app_context():
                MetadataService.safe_retransform_all()

        # Get misfire_grace_time from config (already has default value in config.py)
        misfire_grace_time = current_app.config.get(
            "METADATA_REGENERATION_MISFIRE_GRACE_TIME"
        )

        job_id = f"retransform_all_entities_{datetime.now(pytz.UTC).timestamp()}"
        scheduler.add_job(
            do_retransform,
            DateTrigger(run_date=datetime.now(pytz.UTC)),
            id=job_id,
            replace_existing=False,
            misfire_grace_time=misfire_grace_time,
        )

    def _format_enum(self, value, enum_class):
        """Format enum value: convert numeric to name, return empty string for None."""
        if value is None:
            return ""
        try:
            return enum_class(value).name
        except (ValueError, TypeError):
            return ""

    def _restore_protected_fields(self, model):
        """Restore protected fields to their original values.

        This method checks if any fields defined in PROTECTED_FIELDS have been modified
        and restores their original values using SQLAlchemy's history tracking.

        Args:
            model: The model instance being modified
        """
        client_ip = get_client_ip()

        # Get the primary key field dynamically
        primary_key = getattr(model.__class__, "id", None)
        if not primary_key:
            # If 'id' is not the primary key, try to find it
            for column in model.__table__.columns:
                if column.primary_key:
                    primary_key = column.name
                    break

        if not primary_key:
            primary_key = "unknown"

        for field in self.PROTECTED_FIELDS:
            history = get_history(model, field)
            if history.has_changes():
                old_value = history.deleted[0] if history.deleted else None
                new_value = getattr(model, field, None)
                setattr(model, field, old_value)
                # Log security event when protected fields are modified
                logger.warning(
                    f"[{client_ip}] [PROTECTED FIELD CHANGE] - User "
                    f"{current_user.id}({current_user.email}) attempted to modify "
                    f"protected field '{field}' from '{old_value}' to '{new_value}' "
                    f"in {model.__class__.__name__} #{getattr(model, primary_key)}"
                )

    def _get_old_field_value(self, model, field):
        history = get_history(model, field)
        if history.has_changes():
            old_value = history.deleted[0] if history.deleted else None
            return old_value
        else:
            new_value = getattr(model, field, None)
            return new_value
