# IRIS — IAM Change Alerting.
# Notification channel (email to rohit) is managed by Terraform.
# The alert policy itself is created by gcloud in scripts/deploy.sh
# because Terraform's google_monitoring_alert_policy has limited syntax
# support for log-based conditions.

# Email notification channel for rohit.
resource "google_monitoring_notification_channel" "iam_alerts" {
  project      = var.project_id
  display_name = "IRIS IAM Alert → rohit"
  type         = "email"
  labels = {
    email_address = "rohit.soni@naturepivot.com"
  }
}
