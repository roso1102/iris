#!/usr/bin/env bash
# IRIS — Task 0.7: provision Firebase for the project (no SDK wiring yet —
# that lands in Phase 4.0). Writes the web app config to Secret Manager.

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-asia-south1}"
SECRET_ID="FIREBASE_CONFIG"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: could not determine GCP project. Pass it: $0 <project-id>" >&2
  exit 1
fi

echo "==> Linking Firebase to project '${PROJECT_ID}'"
firebase projects:addfirebase "${PROJECT_ID}" || true

echo "==> Enabling Firebase + Identity Platform APIs"
gcloud services enable firebase.googleapis.com identitytoolkit.googleapis.com \
  --project "${PROJECT_ID}"

echo "==> Creating Firebase web app"
APP_JSON="$(firebase apps:create WEB iris-web --project "${PROJECT_ID}" 2>/dev/null | tail -1)"
if [[ -z "${APP_JSON}" || "${APP_JSON}" != *appId* ]]; then
  echo "INFO: app may already exist; listing existing apps."
  APP_JSON="$(firebase apps:list WEB --project "${PROJECT_ID}" | grep -m1 '"appId"')"
fi
APP_ID="$(echo "${APP_JSON}" | grep -o '"appId": *"[^"]*"' | head -1 | sed 's/.*"appId": *"//;s/"$//')"

echo "==> Fetching web app config"
CONFIG_JSON="$(firebase apps:sdkconfig WEB "${APP_ID}" --project "${PROJECT_ID}" 2>/dev/null | sed -n '/^{/,/^}$/p')"
if [[ -z "${CONFIG_JSON}" ]]; then
  echo "ERROR: could not fetch app config" >&2
  exit 1
fi

echo "==> Writing config to Secret Manager secret '${SECRET_ID}'"
printf '%s' "${CONFIG_JSON}" | gcloud secrets versions add "${SECRET_ID}" \
  --data-file=- --project "${PROJECT_ID}"

echo "==> Provisioning eval user for the evaluation harness"
# The eval harness (scripts/eval_phase2.py) mints a Firebase ID token for a
# dedicated user. Create it (if missing) and set tenant_id/role claims.
# Requires firebaseauth.admin; key creation is disabled in this project, so
# the script is invoked with an impersonated admin-SA access token.
EVAL_EMAIL="${EVAL_USER_EMAIL:-eval@iris.local}"
EVAL_PASSWORD="${EVAL_USER_PASSWORD:-EvalPass!2026x}"
EVAL_TENANT="${EVAL_TENANT_ID:-test-tenant}"
ADMIN_SA="firebase-adminsdk-fbsvc@${PROJECT_ID}.iam.gserviceaccount.com"
# Impersonate the admin SA for a short-lived access token (needs the caller
# to hold roles/iam.serviceAccountTokenCreator + serviceAccountUser on it).
ADMIN_TOKEN="$(gcloud auth print-access-token \
  --impersonate-service-account="${ADMIN_SA}" --project="${PROJECT_ID}" 2>/dev/null || true)"
if [[ -n "${ADMIN_TOKEN}" ]]; then
  ADMIN_SA_TOKEN="${ADMIN_TOKEN}" EVAL_USER_EMAIL="${EVAL_EMAIL}" \
  EVAL_USER_PASSWORD="${EVAL_PASSWORD}" EVAL_TENANT_ID="${EVAL_TENANT}" \
  python scripts/provision_eval_user.py --admin-token "${ADMIN_TOKEN}" || {
    echo "WARN: eval user provisioning failed (you can rerun later with" >&2
    echo "      scripts/provision_eval_user.py)." >&2
  }
else
  echo "WARN: could not impersonate admin SA — eval user provisioning skipped." >&2
  echo "      Rerun with: python scripts/provision_eval_user.py --password <pw>" >&2
fi

echo "==> Done. Firebase config stored in secret '${SECRET_ID}'."
echo "    Phase 4.0 will consume it for client-side auth."
