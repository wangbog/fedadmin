"""Member module for Flask-Admin views."""

__all__ = [
    "MemberBaseView",
    "MemberAdminIndexView",
    "MemberUserModelView",
    "MemberOrganizationModelView",
    "MemberIdpModelView",
    "MemberSpModelView",
]


def __getattr__(name):
    if name == "MemberBaseView":
        from .base import MemberBaseView

        return MemberBaseView
    if name == "MemberAdminIndexView":
        from .index import MemberAdminIndexView

        return MemberAdminIndexView
    if name == "MemberUserModelView":
        from .user import MemberUserModelView

        return MemberUserModelView
    if name == "MemberOrganizationModelView":
        from .organization import MemberOrganizationModelView

        return MemberOrganizationModelView
    if name == "MemberIdpModelView":
        from .idp import MemberIdpModelView

        return MemberIdpModelView
    if name == "MemberSpModelView":
        from .sp import MemberSpModelView

        return MemberSpModelView

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
