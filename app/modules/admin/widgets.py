from flask import request, url_for
from flask_admin.menu import MenuLink
from flask_admin.form.upload import FileUploadInput, ImageUploadInput
from flask_security import current_user


class SwitchRoleLink(MenuLink):
    """A menu link that appears only for federation administrators."""

    def __init__(self, target_endpoint, link_name, link_category):
        super().__init__(
            name=link_name,
            icon_type="fa",
            icon_value="fa-exchange",
            category=link_category,
        )
        self.target_endpoint = target_endpoint

    def is_accessible(self):
        return current_user.is_authenticated and current_user.has_role("federation")

    def get_url(self):
        return url_for(self.target_endpoint)


class CurrentUserLink(MenuLink):
    """Read-only menu item that shows the signed-in user."""

    @property
    def name(self):
        if current_user.is_authenticated:
            username = current_user.username or current_user.email
            return f"Signed in as '{username}'"
        return "Signed in"

    @name.setter
    def name(self, value):
        self._name = value

    def __init__(self, link_category):
        super().__init__(
            name="Signed in",
            icon_type="fa",
            icon_value="fa-user",
            category=link_category,
        )

    def is_accessible(self):
        return current_user.is_authenticated

    def get_url(self):
        return request.url


class SimpleFileUploadInput(FileUploadInput):
    """File upload field without path text box, retaining delete checkbox and upload button."""

    data_template = "<input %(file)s>"


class SimpleImageUploadInput(ImageUploadInput):
    """Image upload field without hidden path input, retaining thumbnail, delete checkbox and upload button."""

    data_template = (
        '<div class="image-thumbnail">' " <img %(image)s>" "</div>" "<input %(file)s>"
    )
