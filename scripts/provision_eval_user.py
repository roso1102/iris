#!/usr/bin/env python
"""Provision the eval Firebase user used by scripts/eval_phase2.py.

Phase 4.0/5.0: the eval harness mints a real Firebase ID token and calls
retrieval-api with `X-Firebase-Token`. That user must exist in Firebase Auth
with `tenant_id` (and `role`) custom claims. This script creates the user if
missing and sets the claims — the one-time provisioning step.

Auth for this script (admin operation, like set_tenant_claims.py):
  - Requires firebaseauth.admin. Default: ADC with a service-account key
    (GOOGLE_APPLICATION_CREDENTIALS). Alternatively pass an access token for
    the admin SA via --admin-token or the ADMIN_SA_TOKEN env var (useful when
    key creation is disabled and you impersonate via gcloud).

Usage:
    python scripts/provision_eval_user.py \
        --email eval@iris.local --password <pw> \
        [--tenant test-tenant] [--role member] \
        [--admin-token <token>]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

PROJECT = "naturepivot-rag"
DEFAULT_TENANT = "test-tenant"


def _credentials(admin_token: str | None):
    """Build Firebase Admin credentials from a token, or fall back to ADC."""
    token = admin_token or os.environ.get("ADMIN_SA_TOKEN", "")
    if token:
        from google.oauth2.credentials import Credentials

        return Credentials(token=token.strip())
    from firebase_admin import credentials

    return credentials.ApplicationDefault()


def _create_user_if_missing(firebase_auth, email: str, password: str, app) -> str:
    """Return the user UID, creating the account first if needed."""
    try:
        return firebase_auth.get_user_by_email(email, app=app).uid
    except Exception:
        return firebase_auth.create_user(email=email, password=password, app=app).uid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=os.environ.get("EVAL_USER_EMAIL", "eval@iris.local"))
    parser.add_argument("--password", default=os.environ.get("EVAL_USER_PASSWORD", ""))
    parser.add_argument("--tenant", default=os.environ.get("EVAL_TENANT_ID", DEFAULT_TENANT))
    parser.add_argument("--role", default="member")
    parser.add_argument("--admin-token", default=os.environ.get("ADMIN_SA_TOKEN", ""))
    args = parser.parse_args()

    if not args.password:
        print("ERROR: --password (or EVAL_USER_PASSWORD) is required", file=sys.stderr)
        return 1

    from firebase_admin import auth as firebase_auth
    from firebase_admin import initialize_app, delete_app

    app = initialize_app(
        credential=_credentials(args.admin_token),
        options={"projectId": PROJECT},
        name="provision-eval-user",
    )
    try:
        uid = _create_user_if_missing(firebase_auth, args.email, args.password, app)
        firebase_auth.set_custom_user_claims(
            uid,
            {"tenant_id": args.tenant, "role": args.role},
            app=app,
        )
        print(f"OK: eval user {args.email} (uid={uid}) claims tenant_id={args.tenant}, role={args.role}")
        return 0
    finally:
        delete_app(app)


if __name__ == "__main__":
    sys.exit(main())
