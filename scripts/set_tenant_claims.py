#!/usr/bin/env python
"""Admin CLI: assign tenant_id/role custom claims to a Firebase user.

Phase 4.0 provisioning helper. The Retrieval API only *verifies* tokens;
this script is how a user is bound to a tenant (SRS FR-3.2 — claims are
server-set, never client-writable).

Usage:
    python scripts/set_tenant_claims.py <uid> <tenant_id> [member|admin]
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")  # repo root, so `from services...` imports resolve

from services.common.auth.claims import set_tenant_claims

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    uid, tenant_id = args[0], args[1]
    role = args[2] if len(args) > 2 else "member"
    try:
        claims = set_tenant_claims(uid, tenant_id, role)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: set {claims} on uid={uid}")
