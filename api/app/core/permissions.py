from enum import Enum

class Permission(str, Enum):
    # Core system permissions
    MANAGE_USERS = "manage:users"
    VIEW_USERS = "view:users"
    
    # HR permissions
    VERIFY_DOCUMENTS = "verify:documents"
    
    # PM permissions
    CREATE_PLAN = "create:plan"
    PUBLISH_PLAN = "publish:plan"
    
    # Finance permissions
    REVIEW_ATTENDANCE = "review:attendance"
    REVIEW_OVERTIME = "review:overtime"
    
    # OPS permissions
    MANAGE_ASSETS = "manage:assets"
    VIEW_TIMELINE = "view:timeline"
    
    # Audit permissions
    VIEW_AUDIT = "view:audit"
    
    # Document permissions
    UPLOAD_DOCUMENTS = "upload:documents"
    VIEW_DOCUMENTS = "view:documents"

# Mapping Role -> Permissions
ROLE_PERMISSIONS = {
    "admin": [p.value for p in Permission],
    "hr": [
        Permission.VIEW_USERS,
        Permission.MANAGE_USERS,
        Permission.VERIFY_DOCUMENTS,
        Permission.VIEW_DOCUMENTS,
    ],
    "pm": [
        Permission.VIEW_USERS,
        Permission.VIEW_DOCUMENTS,
        Permission.CREATE_PLAN,
        Permission.PUBLISH_PLAN,
        Permission.VIEW_TIMELINE,
    ],
    "finance": [
        Permission.VIEW_USERS,
        Permission.REVIEW_ATTENDANCE,
        Permission.REVIEW_OVERTIME,
    ],
    "ops": [
        Permission.VIEW_USERS,
        Permission.MANAGE_ASSETS,
        Permission.VIEW_TIMELINE,
    ],
    "field": [
        Permission.VIEW_USERS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_DOCUMENTS,
    ]
}

def get_role_permissions(role: str) -> list[str]:
    return ROLE_PERMISSIONS.get(role, [])
