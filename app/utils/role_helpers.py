"""
Utility functions for managing user roles based on organization type.
"""

from flask import abort, current_app
from app.models.organization_type import OrganizationType


def assign_user_roles(user, organization):
    """
    Assign roles to a user based on their organization's type.

    Args:
        user: The user object to assign roles to
        organization: The organization object that determines the user's roles

    Raises:
        ValueError: If the organization type is unknown
    """
    user_datastore = current_app.extensions["security"].datastore

    # Clear all existing roles for the user
    user.roles = []

    # Assign new roles based on the organization type
    if organization.organization_type == OrganizationType.FULL_MEMBER.value:
        role_name = "full_member"
        role = user_datastore.find_or_create_role(name=role_name)
        user_datastore.add_role_to_user(user, role)
    elif organization.organization_type == OrganizationType.SP_MEMBER.value:
        role_name = "sp_member"
        role = user_datastore.find_or_create_role(name=role_name)
        user_datastore.add_role_to_user(user, role)
    elif organization.organization_type == OrganizationType.FEDERATION_ADMIN.value:
        # Federation admins should have both federation and full_member roles
        role_fed = user_datastore.find_or_create_role(name="federation")
        user_datastore.add_role_to_user(user, role_fed)
        role_full = user_datastore.find_or_create_role(name="full_member")
        user_datastore.add_role_to_user(user, role_full)
    else:
        abort(
            400,
            description=f"Unknown organization type {organization.organization_type}",
        )
