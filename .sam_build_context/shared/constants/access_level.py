from enum import Enum

class AccessLevel(str, Enum):
    PUBLIC = "public"
    TEAM = "team"
    DEVELOPER = "developer"
    ADMIN = "admin"
