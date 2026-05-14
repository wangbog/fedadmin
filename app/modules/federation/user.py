import re
from flask import abort, flash, redirect, request
from flask_admin import expose
from flask_security import current_user
from flask_security.utils import hash_password
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup
from app.extensions import db
from app.utils.security_helpers import csrf_protected
from app.utils.logging_helpers import logger, get_client_ip
from app.utils.role_helpers import assign_user_roles
from .base import FederationBaseView


class FederationUserModelView(FederationBaseView):
    can_create = True
    can_edit = True

    # Define protected fields that cannot be modified through the edit form
    PROTECTED_FIELDS = ["organization", "password"]

    column_list = [
        "organization_name",
        "username",
        "email",
        "active",
        "actions",
    ]
    column_filters = ["organization.organization_name", "username", "email"]
    column_labels = {
        "organization.organization_name": "Organization Name",
    }
    column_sortable_list = [
        ("organization_name", "organization.organization_name"),
        "username",
        "email",
        "active",
    ]
    column_details_list = [
        "id",
        "organization_name",
        "username",
        "email",
        "active",
        "confirmed_at",
    ]
    column_formatters = {
        "organization_name": lambda v, c, m, p: (
            m.organization.organization_name if m.organization else ""
        ),
        "actions": lambda v, c, m, p: v._render_actions(m),
    }
    form_columns = [
        "organization",
        "username",
        "email",
        "active",
    ]

    def _render_actions(self, model):
        actions = []
        return_path = request.full_path

        # View Button (always available)
        details_url = self.get_url(".details_view", id=model.id, url=return_path)
        actions.append(
            f'<a class="icon" href="{details_url}" title="View Record">'
            f'<span class="fa fa-eye"></span></a>'
        )

        # Edit Button (always available)
        edit_url = self.get_url(".edit_view", id=model.id, url=return_path)
        actions.append(
            f'<a class="icon" href="{edit_url}" title="Edit Record">'
            f'<span class="fa fa-pencil"></span></a>'
        )

        # Delete Button (only for users other than current user)
        if model.id != current_user.id:
            delete_url = self.get_url(".delete")
            csrf_token = generate_csrf()
            actions.append(
                f'<form class="icon" method="POST" action="{delete_url}">'
                f'<input name="id" type="hidden" value="{model.id}">'
                f'<input name="url" type="hidden" value="{return_path}">'
                f'<input name="csrf_token" type="hidden" value="{csrf_token}">'
                "<button onclick=\"return faHelpers.safeConfirm('Are you sure you "
                'want to delete this user?\');" title="Delete User">'
                '<span class="fa fa-trash"></span></button></form>'
            )

        return Markup(" ".join(actions))

    @expose("/delete/", methods=["POST"])
    @csrf_protected
    def delete(self):
        """Custom delete endpoint for users (cannot delete current user)."""
        redirect_url = request.form.get("url") or self.get_url(".index_view")
        client_ip = get_client_ip()
        record_id = request.form.get("id")
        if not record_id:
            flash("Invalid request.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to delete User: "
                "Invalid request"
            )
            return redirect(redirect_url)
        model = self.session.query(self.model).get(record_id)
        if not model:
            flash("User not found.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) failed to delete User "
                f"#{record_id}: User not found"
            )
            return redirect(redirect_url)
        if model.id == current_user.id:
            flash("Cannot delete the currently logged-in user.", "error")
            logger.warning(
                f"[{client_ip}] [DELETE FAILED] - User "
                f"{current_user.id}({current_user.email}) attempted to delete "
                f"themselves User #{model.id}"
            )
            return redirect(redirect_url)

        username = model.username
        db.session.delete(model)
        db.session.commit()
        flash(f'User "{username}" deleted.', "success")
        logger.info(
            f"[{client_ip}] [DELETE] - User "
            f"{current_user.id}({current_user.email}) deleted User #{record_id} "
            f"'{username}'"
        )
        return redirect(redirect_url)

    def edit_form(self, obj=None):
        form = super().edit_form(obj)
        if obj:
            # Make organization field disabled during editing, and remove validators
            form.organization.render_kw = {"disabled": True}
            form.organization.validators = []

        return form

    def on_model_change(self, form, model, is_created):
        # All fields validation
        if not model.username or not model.username.strip():
            raise ValueError("Username is required.")

        if not model.email or not model.email.strip():
            raise ValueError("Email is required.")

        # Validate email format using standard regex
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, model.email):
            raise ValueError("Invalid email format.")

        if is_created:
            # Set default password
            model.password = hash_password(model.username)

            # Set roles based on organization type
            organization = model.organization
            if not organization:
                abort(400, description="Invalid organization")

            # Assign roles based on organization type
            assign_user_roles(model, organization)

        else:
            # Cannot change organization_id/password through edit form,
            # must keep original value
            self._restore_protected_fields(model)

    def after_model_change(self, form, model, is_created):
        client_ip = get_client_ip()
        if is_created:
            logger.info(
                f"[{client_ip}] [CREATE] - User "
                f"{current_user.id}({current_user.email}) created User "
                f"#{model.id} '{model.username}'"
            )
        else:
            logger.info(
                f"[{client_ip}] [UPDATE] - User "
                f"{current_user.id}({current_user.email}) updated User "
                f"#{model.id} '{model.username}'"
            )
