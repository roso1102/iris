"""Admin-only custom-claims setter (Phase 4.0).

Assigns the server-set `tenant_id` and `role` custom claims to a Firebase
user. These claims are NOT client-writable; this script is the admin
provisioning path (SRS FR-3.2). Requires a service-account credential with
firebaseauth.admin — the same credential the deployed services use via ADC.

Usage:
    python scripts/set_tenant_claims.py <uid> <tenant_id> [role]

Role defaults to "member". Allowed roles: member, admin.
"""

from __future__ import annotations

import sys


def set_tenant_claims(uid: str, tenant_id: str, role: str = "member") -> dict:
    from firebase_admin import auth as firebase_auth

    if not uid or not tenant_id:
        raise ValueError("uid and tenant_id are required")
    if role not in ("member", "admin"):
        raise ValueError("role must be 'member' or 'admin'")

    claims = {"tenant_id": tenant_id, "role": role}
    firebase_auth.set_custom_user_claims(uid, claims)
    return claims


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    uid, tenant_id = args[0], args[1]
    role = args[2] if len(args) > 2 else "member"
    claims = set_tenant_claims(uid, tenant_id, role)
    print(f"Set claims {claims} on user {uid}")
