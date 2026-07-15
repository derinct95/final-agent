"""Role enforcement for the mock-auth demo login.

The frontend session carries a client-supplied role (practice_admin /
clinical_analyst) with no real credential verification behind it -- see
README's disclosed limitations. This dependency at least makes that role
mean something: write actions require it to be sent and to equal
practice_admin, rather than silently trusting every caller with full access.
"""

from fastapi import Depends, Header, HTTPException

ADMIN_ROLE = "practice_admin"
ANALYST_ROLE = "clinical_analyst"
VALID_ROLES = {ADMIN_ROLE, ANALYST_ROLE}


def get_current_role(x_user_role: str | None = Header(default=None, alias="X-User-Role")) -> str:
    """Missing or unrecognized roles default to the least-privileged role,
    not admin -- a caller must explicitly present practice_admin to unlock
    write actions."""
    return x_user_role if x_user_role in VALID_ROLES else ANALYST_ROLE


def require_admin(role: str = Depends(get_current_role)) -> str:
    if role != ADMIN_ROLE:
        raise HTTPException(status_code=403, detail="This action requires Practice Administrator access.")
    return role


def get_current_email(x_user_email: str | None = Header(default=None, alias="X-User-Email")) -> str:
    """Client-supplied identity, same trust model as get_current_role -- used
    to scope personal data (recent activity) to the caller, not as a real
    authentication boundary."""
    return x_user_email or ""
