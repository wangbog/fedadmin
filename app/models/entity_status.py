from enum import Enum


class EntityStatus(Enum):
    """Entity status enumeration"""

    INIT = 0
    APPROVING = 1
    READY = 2
