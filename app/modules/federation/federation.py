from flask import request, abort, flash
from urllib.parse import urlparse
from flask_security import current_user
from markupsafe import Markup
from app.utils.logging_helpers import logger, get_client_ip
from .base import FederationBaseView


class FederationFederationModelView(FederationBaseView):
    can_edit = True

    extra_js = [
        "/static/js/form_utils.js",
        "/static/js/federation_forms.js",
    ]

    column_list = [
        "registration_authority",
        "registration_policy_url",
        "publisher",
        "actions",
    ]
    column_formatters = {
        "actions": lambda v, c, m, p: v._render_actions(m),
    }
    column_descriptions = {
        **FederationBaseView.column_descriptions,
        **{
            "registration_authority": 'Registration Authority identifier for mdrpi:RegistrationInfo. <a href="https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-rpi/v1.0/sstc-saml-metadata-rpi-v1.0.html" target="_blank">MDRPI specification</a>',
            "registration_policy_url": "URL pointing to the federation's registration practices statement. MUST be a valid URL.",
            "publisher": "Human-readable name of the federation that publishes this metadata.",
        },
    }
    form_columns = ["registration_authority", "registration_policy_url", "publisher"]

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

        return Markup(" ".join(actions))

    def on_model_change(self, form, model, is_created):
        if is_created:
            abort(403)

        # All fields validation
        if not model.registration_authority or not model.registration_authority.strip():
            raise ValueError("Registration Authority is required.")

        # MDRPI spec: registrationAuthority MUST be a valid URI
        url_check = urlparse(model.registration_authority)
        if not url_check.scheme or not url_check.netloc:
            raise ValueError("Registration Authority must be a valid URI format.")

        if (
            not model.registration_policy_url
            or not model.registration_policy_url.strip()
        ):
            raise ValueError("Registration Policy URL is required.")

        # MDRPI spec: registrationPolicy MUST be a valid URL
        url_check = urlparse(model.registration_policy_url)
        if not url_check.scheme or not url_check.netloc:
            raise ValueError("Registration Policy URL must be a valid URL format.")

        if not model.publisher or not model.publisher.strip():
            raise ValueError("Publisher is required.")

    def after_model_change(self, form, model, is_created):
        client_ip = get_client_ip()
        if is_created:
            # Should not happen (creation is disabled)
            return
        else:
            logger.info(
                f"[{client_ip}] [UPDATE] - User {current_user.id}({current_user.email}) updated federation configuration"
            )

        # re-transform all entities, and regenerate metadata
        self._retransform_all_entities()

        flash(
            "Federation registration configuration has been updated. All entities will automatically re-transform in the background. Federation metadata will be regenerated automatically after completion.",
            "info",
        )
