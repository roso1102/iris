#!/usr/bin/env bash
# IRIS — IAM Change Alerting (run once, manually).
#
# Creates a log-based alert that emails rohit.soni@naturepivot.com
# every time a SetIamPolicy event is detected in the project audit logs.
#
# Prerequisites: gcloud auth login done, project set to naturepivot-rag.

set -euo pipefail

PROJECT="${1:-naturepivot-rag}"

# 1. Find the email notification channel (created by Terraform in monitoring.tf)
CHANNEL=$(gcloud monitoring channels list \
  --project="${PROJECT}" \
  --filter="type=email AND displayName~\"IRIS IAM Alert\"" \
  --format="value(name)" 2>/dev/null | head -1)

if [[ -z "${CHANNEL}" ]]; then
  echo "ERROR: No email notification channel found. Run terraform apply in infra/ first." >&2
  exit 1
fi

echo "==> Using notification channel: ${CHANNEL}"

# 2. Create the alert policy
gcloud monitoring policies create \
  --project="${PROJECT}" \
  --display-name="IAM Policy Change Detected" \
  --severity="WARNING" \
  --combiner="OR" \
  --notification-channels="${CHANNEL}" \
  --documentation='An IAM policy binding was modified on the project. Check the audit log for details: who, what role, which principal.' \
  --condition-display-name="SetIamPolicy event" \
  --condition-filter='resource.type="project" AND log_id("cloudaudit.googleapis.com/activity") AND protoPayload.methodName="SetIamPolicy" AND severity>=NOTICE' \
  --condition-threshold-value=0 \
  --condition-threshold-duration=0s \
  --condition-comparison="COMPARISON_GT" \
  --condition-aggregation='{"alignmentPeriod":"60s","perSeriesAligner":"ALIGN_COUNT","crossSeriesReducer":"REDUCE_COUNT"}'

echo "==> IAM alert policy created."
echo "    You will now receive an email at rohit.soni@naturepivot.com"
echo "    within ~60 seconds of any IAM policy change."
