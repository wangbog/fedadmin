from enum import Enum


class OrganizationType(Enum):
    """Organization type enumeration"""

    FEDERATION_ADMIN = 9
    FULL_MEMBER = 1
    SP_MEMBER = 2
