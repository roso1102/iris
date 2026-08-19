# IRIS — Phase 4.0: Cloud Armor security policy skeleton (cloud-gated).
#
# Edge rate limiting / WAF is intentionally NOT deployed in Phase 4.0 (the
# in-app per-tenant limiter covers MVP). This file exists so the policy is
# reproducible when the cloud phase is approved. Attaching it to the Cloud Run
# services requires a Global External HTTPS Load Balancer, which is deferred
# to Phase 16.0 per the ACTIONPLAN.

# Cloud Armor security policy with a request rate limit rule.
resource "google_compute_security_policy" "iris_rate_limit" {
  count   = 0 # disabled until Phase 16.0 / explicit approval
  name    = "iris-security-policy"
  project = var.project_id

  rule {
    action   = "throttle"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 30
        interval_sec = 60
      }
    }
    description = "Rate limit 30 req/min per IP (interim edge throttling)"
  }

  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow"
  }
}
