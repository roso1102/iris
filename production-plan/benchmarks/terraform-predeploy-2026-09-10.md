# Terraform pre-deployment hardening — 2026-09-10

## Scope

Staging configuration for `procambrian-iris-staging-2026`; no GCP resources were
created or modified during this change.

## Changes recorded

- Removed old project, email, bucket, URL, and fixed-Qdrant-IP references from
  deployment/runtime configuration.
- Added explicit API coverage for Cloud Build, Monitoring, Logging, and
  Firebase Rules.
- Added Firestore database and Artifact Registry Terraform resources.
- Replaced the duplicate Eventarc ingestion path with one authenticated
  Pub/Sub push subscription updated after Cloud Run returns its URL.
- Added Pub/Sub dead-letter service-agent permissions.
- Added a reserved internal Qdrant address, persistent data disk, deletion
  protection, and a restricted VM service account.
- Replaced the always-on Serverless VPC Access connector with Direct VPC
  egress to remove connector VM cost and reduce network moving parts.
- Removed secret values from Terraform state and retained only the Firebase
  configuration secret container.
- Added staging-safe remote-state bootstrap and outputs.
- Changed CI deployment to explicit `workflow_dispatch` instead of automatic
  deployment on every push to `main`.
- Reduced the staging Qdrant VM boot disk from 20 GiB balanced/default storage
  to an explicit 10 GiB `pd-standard` disk and reduced the separate Qdrant data
  disk from 50 GiB to 10 GiB `pd-balanced` storage. The data disk remains
  deletion-protected and can be expanded later, but Persistent Disks cannot be
  reduced in place.

## Verification

| Check | Result |
|---|---|
| `terraform fmt -check` | PASS |
| `terraform validate -json` | PASS; 0 errors, 0 warnings |
| Python bytecode compilation (`services`, `scripts`) | PASS |
| Stale deployment references scan | PASS; none in runtime/deployment paths |
| `git diff --check` | PASS; only line-ending warnings |
| Real Terraform plan | PASS; read-only plan targets `procambrian-iris-staging-2026`, 58 resources to add, 0 change, 0 destroy |
| Disk sizing review | PASS; 10 GiB standard boot + 10 GiB balanced Qdrant data configured; expected disk-only cost approximately $1.40/month before tax |
| ADC/project/state verification (2026-09-12) | PASS; ADC authenticated, project ACTIVE with billing enabled, remote state bucket reachable |
| Reviewed plan artifact (2026-09-12) | PASS; saved as `infra/staging.tfplan`; same execution is applied only after the IAM gate is cleared |
| Apply IAM gate (2026-09-12) | BLOCKED pending temporary `roles/compute.admin`, `roles/pubsub.admin`, and `roles/monitoring.editor` for the Terraform operator |
| Billing budget gate (2026-09-12) | API ENABLED; no billing budget exists yet. Budget creation remains a billing-account action and requires Billing Account Costs Manager or Billing Account Administrator access |
| Terraform apply (2026-09-12) | PASS; `staging-retry.tfplan` applied with 38 resources added, 0 changed, and 2 tainted API entries replaced |
| Post-apply control-plane checks (2026-09-12) | PASS; project resources, 10 GiB Qdrant data disk, private IP 10.0.0.2, Firestore, bucket and Artifact Registry verified |
| Terraform drift check (2026-09-12) | PASS; no changes detected after apply |
| Qdrant startup check (2026-09-12) | PASS; serial console reports startup script exit status 0, Docker image qdrant/qdrant:v1.13.0 downloaded, and container started |
| IAP SSH check (2026-09-12) | ROLE CONFIRMED at project scope as `roles/iap.tunnelResourceAccessor` (Console label: IAP-secured Tunnel User); direct VM policy is empty as expected. SSH retest remains optional because serial logs independently confirm the startup script and Qdrant container completed successfully |
| Firebase readiness (2026-09-12) | PASS for linkage, web app, and config secret: Firebase Management API returns ACTIVE project `procambrian-iris-staging-2026` / `46294096145`; web app `iris-web` is ACTIVE (`1:46294096145:web:2a564df5c81c41d89d54b0`); `FIREBASE_CONFIG` secret version `1` is ENABLED. Firebase CLI emits a Windows Node assertion after SDK-config retrieval, but the secret write completed successfully. Evaluation-user provisioning remains separate and no Firebase Admin service account was found yet |
| Billing budget check (2026-09-12) | Budget CREATED: `IRIS staging budget`, INR 10,000/month, billing account `01FC2C-DA1D74-D70567`; Pub/Sub attachment remains BLOCKED with Console request ID `12077045985895169679`. The topic exists and Rohit has Billing Account Costs Manager plus project Pub/Sub Admin; both Console and Billing API return `FAILED_PRECONDITION` when attaching the topic. Billing account currently has 5 linked projects, including IRIS; a separate foundation workflow requests 5 additional associations and is blocked by the account’s project-association quota. Re-running `gcloud billing projects link` returns the same quota error, but verification confirms IRIS remains linked and billing-enabled |
| Billing project cleanup (2026-09-12) | REQUESTED: unlink four non-IRIS projects from the billing account. Rohit’s unlink attempts were denied on all targets because he lacks `billing.resourceAssociations.delete` and `resourcemanager.projects.deleteBillingAssignment` on those projects; no projects were changed. Manoj or each project owner must perform the unlink |
| Unit tests | BLOCKED on this machine because `pytest`, FastAPI, and Pydantic are not installed |

## Next gate

Terraform, resource verification, IAP project role, Firebase linkage/web app/config
secret, and the initial budget are complete. Remaining pre-smoke gates are the
budget Pub/Sub attachment (support/Manoj), Cloud Run retrieval/ingestion deploy,
authenticated Pub/Sub push wiring, one-document smoke test, and the first
application benchmark. The known Firebase CLI Windows assertion is cosmetic;
the config secret write succeeded.
