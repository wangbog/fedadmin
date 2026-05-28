from markupsafe import Markup, escape

from .base import FederationBaseView


class FederationEmailDeliveryModelView(FederationBaseView):
    can_view_details = True

    column_list = [
        "created_at",
        "status",
        "recipient",
        "subject",
        "template",
        "error_message",
    ]
    column_details_list = [
        "id",
        "created_at",
        "sent_at",
        "status",
        "recipient",
        "subject",
        "template",
        "user",
        "error_message",
    ]
    column_filters = ["status", "recipient", "template", "created_at"]
    column_searchable_list = ["recipient", "subject", "template", "error_message"]
    column_sortable_list = ["created_at", "status", "recipient", "template"]
    column_default_sort = ("created_at", True)
    column_labels = {
        "created_at": "Created At",
        "sent_at": "Sent At",
        "error_message": "Error",
        "user": "User",
    }
    column_formatters = {
        "error_message": lambda v, c, m, p: v._format_error_message(
            m.error_message
        ),
    }

    def _format_error_message(self, error_message):
        if not error_message:
            return ""
        return Markup(
            '<span class="text-break">{message}</span>'
        ).format(message=escape(error_message))
