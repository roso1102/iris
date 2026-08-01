# IRIS — Task 0.2: monthly billing budget + alert topic.
# Task 0.3: the kill-switch Cloud Function is under services/billing-kill-switch/;
# this file wires the budget to the billing-alerts topic.
#
# NOTE: The ₹25,000/month budget already exists (created in the Billing Console,
# display name "iris budget"). Connecting it to the `billing-alerts` Pub/Sub
# topic must be done in the Console (Budgets & alerts -> iris budget ->
# Manage notifications -> Connect a Pub/Sub topic) — the Console auto-grants the
# Cloud Billing publisher permission that gcloud/terraform cannot (the
# billing-<ID>@billing.gserviceaccount.com SA does not exist to bind).
#
# The Terraform `google_billing_budget` resource is intentionally NOT defined
# here: creating/updating it via terraform hits the same permission wall, and
# the budget is Console-managed. See scripts/deploy.sh for the kill switch.

# Pub/Sub topic that Cloud Billing publishes budget alerts to.
resource "google_pubsub_topic" "billing_alerts" {
  name    = "billing-alerts"
  project = var.project_id

  labels = local.labels
}
