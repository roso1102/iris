# IRIS Clean GCP Bootstrap and Deployment Plan

**Owner:** Procambrian  
**Bootstrap engineer:** `rohit@procambrian.ai`  
**Plan date:** 2026-09-08  
**Status:** Proposed — no GCP changes have been executed  
**Relationship to production plan:** This plan must be completed before Phase 1.0 in [`PRODUCTION_PLAN.md`](PRODUCTION_PLAN.md).

## 1. Decision and scope

IRIS will be deployed as a clean, company-owned GCP environment. The old free-trial project is not a migration source because it contains only disposable test data. We will not transfer its Firestore database, Firebase users, GCS objects, Pub/Sub messages, Qdrant index, service accounts, secrets, or container images.

The eight PDFs in the repository/workspace become a versioned seed corpus and are ingested through the new staging pipeline. This proves that the new environment can be recreated from source and infrastructure code.

The order is intentionally:

```text
Temporary company access
  → local code and test hotfixes
  → Terraform portability/security corrections
  → keyless deployment identities
  → empty staging deployment
  → eight-document seed and benchmark
  → empty production deployment
  → production-plan Phase 1.0+
```

We will not combine the initial cloud deployment with Docling removal, new OCR geometry, a new chunk schema, adaptive HyDE, LangGraph, or a major Qdrant migration. Those changes follow after the clean baseline is running and measured.

## 2. Responsibility split

### CEO — two short manual actions

The CEO keeps control of the billing account. He does not share his password, payment method, MFA code, service-account key, or billing credentials.

He only grants temporary access to `rohit@procambrian.ai` in two places:

1. Company organization/folder IAM.
2. Cloud Billing account IAM.

After bootstrap validation, the temporary roles are removed.

### Rohit — interactive/company-authorized actions

- Sign into `gcloud`, Google Cloud Console, Firebase Console, GitHub, DNS/Vercel using the company identity.
- Create the projects/folder if authorized.
- Link projects to the existing billing account.
- Approve Terraform plans and cloud commands that create billable resources.
- Insert real secret values through Secret Manager without placing them in chat, Git, shell history, Terraform variables, or state.
- Approve production deployment and DNS/frontend changes.

### Codex — repository and guided cloud work

- Patch code, tests, Terraform, CI, IAM definitions, documentation, benchmark harnesses, and deployment configuration.
- Run local tests and create immutable benchmark records.
- After Rohit authenticates and explicitly authorizes cloud execution, run read-only discovery, Terraform plans, and approved deployments.
- Never request or store CEO credentials, card data, service-account JSON keys, Firebase password-hash keys, access tokens, or secret contents.

## 3. Company Phase 0.0 — temporary access bootstrap

### 3.1 Preferred organization structure

```text
Procambrian organization
  └── IRIS folder
       ├── iris-staging project
       └── iris-production project
```

Suggested globally unique project IDs are decided before creation, for example:

```text
procambrian-iris-stg
procambrian-iris-prod
```

Project IDs cannot be changed after creation. Names can be changed.

### 3.2 Exact temporary roles for the CEO to grant

#### Organization/folder IAM

Principal:

```text
rohit@procambrian.ai
```

Required:

| Role | Role ID | Why |
|---|---|---|
| Organization Viewer | `roles/resourcemanager.organizationViewer` | View the company hierarchy and organization ID. |
| Project Creator | `roles/resourcemanager.projectCreator` | Create the staging and production projects. Prefer granting this on an existing `IRIS` folder; otherwise temporarily at organization scope. |

Only if the CEO cannot create an `IRIS` folder himself:

| Role | Role ID | Why |
|---|---|---|
| Folder Creator | `roles/resourcemanager.folderCreator` | Create the one `IRIS` folder. Remove after it exists. |

The CEO should not grant Organization Administrator, Organization Policy Administrator, Project Mover, Project Deleter, or broad Security Administrator for this bootstrap.

#### Billing account IAM

Required:

| Role | Role ID | Why |
|---|---|---|
| Billing Account User | `roles/billing.user` | Link the two new projects to the existing active billing account. |
| Billing Account Costs Manager | `roles/billing.costsManager` | Create budgets/alerts and view/export relevant cost information. |

Optional if detailed billing reports are not visible with the roles above:

| Role | Role ID |
|---|---|
| Billing Account Viewer | `roles/billing.viewer` |

Do **not** grant Rohit Billing Account Administrator unless a later, separately approved task truly requires changing payment instruments or billing IAM. The CEO retains `roles/billing.admin`.

Where IAM conditions/expiration are supported in the console, use a bootstrap expiry of 7 days. Otherwise, create a calendar task to revoke the roles at Company Phase 0.6.

### 3.3 CEO click path

Organization roles:

```text
Google Cloud Console
  → select the company organization
  → IAM & Admin
  → IAM
  → Grant access
  → principal: rohit@procambrian.ai
  → add Organization Viewer + Project Creator
```

If an `IRIS` folder already exists, select that folder and grant Project Creator there instead of the entire organization.

Billing roles:

```text
Google Cloud Console
  → Billing
  → select active company billing account
  → Account management / Permissions
  → Add principal: rohit@procambrian.ai
  → Billing Account User + Billing Account Costs Manager
```

### 3.4 Rohit verification — read-only

After the CEO grants access, Rohit signs in interactively:

```powershell
gcloud auth login rohit@procambrian.ai
gcloud auth list
gcloud organizations list
gcloud billing accounts list
```

Do not paste command output containing tokens or private account data into tickets/chat. Organization ID, project ID, project number, billing account ID, region, and service-account email are identifiers rather than credentials, but keep them in approved company systems.

### 3.5 Exit criteria

- `rohit@procambrian.ai` can see the company organization and active billing account.
- Rohit cannot modify payment instruments or billing IAM.
- MFA is enabled for CEO and Rohit.
- At least two company-controlled identities can recover organization/billing administration.
- Temporary-role removal date is recorded.

## 4. Company Phase 0.1 — local critical code and test fixes

No GCP deployment occurs in this phase. These changes prevent known defects and obsolete SDK/model choices from becoming the new baseline.

### 4.1 Required code changes

1. Fix uninitialized `intent` in `/query` for requests without `active_docs`.
2. Use one monotonic clock for deep-search and stage latency.
3. Validate non-empty query, structured history, bounded `doc_ids`, bounded/typed `active_docs`, IDs, model outputs, embedding count/dimension, and finite vector values.
4. Await every Pub/Sub publication result; initialize progress before dispatch.
5. Download a PDF once and guarantee temporary-file cleanup on success/failure.
6. Replace internal exception strings in API responses with stable codes and correlation IDs.
7. Do not report plain-text full-page OCR as a precise element bbox; label it page/coarse fallback until structured OCR lands.
8. Remove unconditional network/model downloads from unit-test fixtures.
9. Resolve `token.txt`: if it contains a credential, rotate it, remove it, and add a suitable secret-scan/ignore rule without exposing its contents.
10. Delete known dead/duplicate cross-lingual paths and fix known Hindi normalization data defects only where covered by tests.

### 4.2 Google SDK/model blocker

The code currently uses `vertexai.generative_models`. The target deployment must use the supported Google Gen AI SDK (`google-genai`) through the existing `ModelProvider` boundary.

Required work:

- Implement the current SDK adapter without leaking SDK objects outside `services/common/models`.
- Add mocked contract tests for text generation, structured output, vision, rewrite, HyDE, routing, synthesis and error classification.
- Add a small opt-in live provider suite; never run it in hermetic unit tests.
- Select a current GA model available to the chosen Vertex location using a stored bake-off.
- Do not deploy Gemini 2.5 Flash/Flash-Lite as the new long-lived baseline because their announced retirement is 2026-10-16.
- Keep embedding-model migration independent unless the empty target-index bake-off selects the replacement before initial ingestion.

### 4.3 Unit-test gates

- Query matrix: standard/deep × active docs present/absent × document filter present/absent × session present/absent.
- Clock property test: no negative stage/total duration.
- Embedding outputs: empty, partial, too many, wrong dimension, NaN and Inf.
- Publisher: partial failure, timeout, retryable/permanent error and out-of-order completion.
- Temporary file cleanup: success, reject, exception and cancellation.
- Error response snapshot: no stack, internal path, endpoint, credential or provider payload leakage.
- Coarse bbox response is explicit and cannot be mistaken for precise geometry.
- Unit tests pass with network disabled and empty cloud credentials.

### 4.4 Benchmarks and stored evidence

Store baseline and candidate at:

```text
production-plan/benchmarks/runs/YYYY-MM-DD/phase-company-0.1/<run-id>/
```

Include `manifest.json`, `CHANGE.md`, unit results, coverage, latency sanity, memory, provider-call count and known limitations following [`production-plan/TEST_AND_BENCHMARK_STANDARD.md`](production-plan/TEST_AND_BENCHMARK_STANDARD.md).

### 4.5 Exit criteria

- Hermetic unit suite passes 100%.
- Critical authorization/idempotency/validation branches have 100% coverage.
- No known P0 crash remains.
- No obsolete SDK call exists outside a deliberately temporary adapter.
- Candidate model configuration has contract evidence or remains disabled pending staging live test.

## 5. Company Phase 0.2 — Terraform and deployment remediation

No resources are applied until the Terraform plan is reviewed.

### 5.1 Make environments explicit

Target layout:

```text
infra/
  modules/
    project-services/
    identity/
    network/
    storage/
    messaging/
    qdrant/
    serverless/
    observability/
  environments/
    staging/
      backend.hcl
      terraform.tfvars.example
    production/
      backend.hcl
      terraform.tfvars.example
  bootstrap/
    README.md
    bootstrap_state.ps1
```

Real `.tfvars`, backend credentials, plans containing sensitive data, and Terraform state are never committed.

### 5.2 Required Terraform changes

1. Parameterize project ID, region, environment, billing identifiers, domains, service URLs, bucket names, image digests, model IDs, collection/index names and notification recipients.
2. Replace globally hardcoded `iris-raw-pdfs` with project/environment-qualified bucket names.
3. Add a real state-bucket bootstrap process; the currently referenced bootstrap script is missing.
4. Use separate versioned, public-access-blocked state buckets/prefixes for staging and production.
5. Terraform creates Secret Manager containers/IAM, but real secret values are inserted out of band; no `secret_data` in state.
6. Replace runtime `roles/datastore.owner` with `roles/datastore.user` or narrower custom roles.
7. Replace project-wide Secret Accessor with per-secret bindings.
8. Replace broad bucket permissions with bucket- and action-scoped roles/custom roles.
9. Create a dedicated no-login service account for Qdrant VM if a VM remains; do not use the default compute service account.
10. Define Artifact Registry and immutable image deployment.
11. Choose one Pub/Sub delivery topology; remove the duplicate push/Eventarc path.
12. Make Terraform or one CI workflow the single owner of Cloud Run configuration.
13. Define Firestore database location, rules, indexes and service identities explicitly.
14. Create Workload Identity Federation restricted to the exact GitHub organization/repository/branch/environment.
15. Add dashboards, alerts, log retention, audit configuration and budget notification plumbing.
16. Pin provider/module/container versions; production deploys digests, never `latest`.
17. Output generated endpoints/IPs from Terraform; do not hardcode an old Cloud Run URL, service-account email, or `10.0.0.5` in repository configuration.

### 5.3 Terraform deployer identity

Rohit creates one deployer per project after project creation:

```text
terraform-deployer@PROJECT_ID.iam.gserviceaccount.com
```

Initial project-scoped roles, reduced later through IAM Recommender/audit evidence:

- `roles/serviceusage.serviceUsageAdmin`
- `roles/resourcemanager.projectIamAdmin`
- `roles/iam.serviceAccountAdmin`
- `roles/compute.networkAdmin`
- `roles/compute.instanceAdmin.v1`
- `roles/compute.securityAdmin`
- `roles/servicenetworking.networksAdmin`
- `roles/vpcaccess.admin`
- `roles/storage.admin`
- `roles/pubsub.admin`
- `roles/artifactregistry.admin`
- `roles/run.admin`
- `roles/cloudfunctions.admin`
- `roles/eventarc.admin`
- `roles/secretmanager.admin`
- `roles/firebaserules.admin`
- `roles/datastore.indexAdmin`
- `roles/monitoring.admin`

Grant deployer `roles/iam.serviceAccountUser` only on the specific runtime service accounts it attaches to resources.

Rohit receives `roles/iam.serviceAccountTokenCreator` only on the Terraform deployer service account. No service-account JSON key is created.

### 5.4 Static validation gates

- `terraform fmt -check`.
- `terraform validate`.
- TFLint/provider lint.
- Checkov/tfsec or equivalent IaC security scan.
- No high/critical unresolved finding.
- Terraform plan creates resources only in the selected staging project.
- Plan contains no secret value.
- A second plan after apply is empty except documented provider-computed fields.

## 6. Company Phase 0.3 — create projects and state safely

### 6.1 Create staging first

Rohit creates the `IRIS` folder if required, then `iris-staging`, links billing and records:

- organization/folder ID;
- project ID and project number;
- billing link status;
- selected region;
- budget/currency;
- approved domains and GitHub repository.

Rohit is automatically highly privileged on a project he creates. This is temporary bootstrap authority, not the steady state.

### 6.2 Bootstrap state

Create a globally unique state bucket such as:

```text
procambrian-iris-stg-tfstate
```

Required settings:

- uniform bucket-level access;
- public access prevention enforced;
- object versioning;
- lifecycle retaining enough prior state generations for recovery;
- no customer documents or application artifacts;
- access limited to Terraform deployer plus break-glass administrators;
- audit logs enabled according to company policy.

### 6.3 Create production only after staging infrastructure plan is clean

Production uses a different project, deployer, state bucket, secrets, Firebase configuration, service accounts and WIF environment.

## 7. Company Phase 0.4 — keyless CI/CD and supply-chain security

### 7.1 GitHub identity

Create:

```text
github-deployer@PROJECT_ID.iam.gserviceaccount.com
```

Authenticate using GitHub OIDC → Google Workload Identity Federation. Restrict trust to:

- exact GitHub organization;
- exact repository;
- protected `main` branch or named deployment environment;
- production environment approval for production impersonation.

No JSON credential is stored in GitHub.

### 7.2 CI stages

```text
Pull request:
  formatting → lint → type → unit → component → contract
  → secret scan → SAST → dependency/license → IaC scan

Main/staging:
  build once → SBOM → vulnerability scan → sign/attest image
  → push digest → Terraform plan → approved apply
  → deploy digest → smoke → benchmark

Production:
  promote the exact staging-tested digest
  → manual environment approval
  → canary/health gate
  → full traffic or rollback
```

### 7.3 GitHub deployer permissions

Grant only what the pipeline needs:

- submit Cloud Build or build in GitHub;
- Artifact Registry Writer;
- Cloud Run deployment permission;
- Service Account User on exact runtime identities;
- read deployment configuration, but no application data;
- no Billing Admin, Project IAM Admin, Firestore data role, broad Storage Admin, or secret-value access.

## 8. Company Phase 0.5 — empty staging deployment

### 8.1 Initial components

- staging GCS raw/artifact buckets;
- Firestore database, indexes and rules;
- Firebase/Identity Platform test configuration;
- Pub/Sub topic, one delivery path and DLQ;
- Qdrant non-production deployment with authentication/private connectivity;
- ingestion-worker and retrieval-api;
- Artifact Registry;
- Secret Manager resources and exact IAM;
- OpenTelemetry/export baseline, structured logs, dashboards and alerts;
- budget alerts and strict maximum instances.

### 8.2 Runtime identity policy

#### Retrieval API

- `roles/aiplatform.user`.
- `roles/datastore.user`.
- bucket-scoped object actions required for upload/view/delete.
- `roles/run.invoker` only on ingestion-worker.
- Secret Accessor only on its named secrets.
- self-scoped signing permission only if signed URLs need it.
- Qdrant application credential, not administrative access.

#### Ingestion worker

- `roles/aiplatform.user`.
- `roles/datastore.user`.
- bucket-scoped raw/artifact object actions.
- Pub/Sub Publisher only if its design still fans out work.
- Document AI invocation only when the OCR phase begins.
- Secret Accessor only on its named secrets.
- Qdrant write credential without cluster administration where supported.

#### Trigger identity

- Cloud Run Invoker on ingestion-worker only.

Authorization and storage access must fail closed. A Firestore/provider outage cannot grant additional access.

### 8.3 Initial cost controls

- staging Cloud Run min instances `0` unless a measured need exists;
- ingestion-worker max instances `1` initially;
- retrieval-api max instances `2` initially;
- Qdrant smallest viable staging size;
- provider quotas/concurrency limits;
- ingestion pause flag and documented queue pause procedure;
- billing alerts at 25%, 50%, 75%, 90% and 100%;
- daily anomaly alert;
- no Document AI bulk processing until the OCR benchmark phase.

Budgets alert; they are not guaranteed hard caps. Quotas, max instances, rate limits, queue controls and application admission control provide additional containment.

## 9. Company Phase 0.6 — seed corpus and staging acceptance

### 9.1 Seed data

The eight local PDFs become `seed-corpus-v1`.

For each PDF store in the dataset manifest:

- SHA-256;
- page count;
- language/script;
- digital/scanned/mixed label;
- tables/figures/handwriting label;
- expected test questions and evidence pages;
- data/license approval.

Create one staging Firebase user and one test tenant. No old Firebase user migration is performed.

### 9.2 Required acceptance tests

- authentication, tenant claim and invalid-token cases;
- upload and file validation;
- all eight documents reach an explicit ingestion state;
- no missing or duplicate active chunks;
- `/search` and `/query` with/without active documents;
- follow-up baseline;
- HyDE invocation baseline;
- citation registry and coarse/exact geometry state;
- Pub/Sub retry and DLQ;
- Qdrant backup/restore smoke test;
- secret/IAM negative tests;
- CORS and signed URL behavior;
- staging teardown/recreation plan.

### 9.3 Required benchmark record

Create:

```text
production-plan/benchmarks/runs/YYYY-MM-DD/phase-company-0.6/<run-id>/
  manifest.json
  CHANGE.md
  results.json
  per_example.jsonl
  config.json
  environment.json
  reports/
  logs/
  artifacts/
```

Record:

- exact Git and container digests;
- Terraform/provider versions;
- project/region and machine shapes;
- model/prompt/embedding/parser/chunker/index versions;
- document hashes;
- unit/component/live-provider results;
- document/page/chunk retrieval metrics;
- P50/P95/P99;
- OCR/VLM/embedding/generation calls;
- estimated and billed cost;
- known failures and `PASS`, `FAIL`, or `INCONCLUSIVE`.

### 9.4 Exit criteria

- All hermetic tests pass.
- Staging can be recreated from Terraform and source.
- All eight seed documents ingest or have explicit valid rejection/review states.
- Zero tenant/ACL leakage.
- No project-wide runtime secret access or Datastore Owner.
- No static service-account key.
- Benchmark record is immutable and complete.
- Rohit can operate through keyless deployer identities.

## 10. Company Phase 0.7 — remove temporary bootstrap access

After staging passes:

1. Confirm Terraform deployer impersonation works.
2. Confirm GitHub WIF deployment works.
3. Remove Rohit's automatic/basic Project Owner role from staging if present.
4. Remove temporary Folder Creator and organization-wide Project Creator after production project creation.
5. Remove Billing Account User if Rohit no longer needs to link projects.
6. Retain Billing Costs Manager/Viewer only if cost operations are part of Rohit's job.
7. Keep Browser, Logs Viewer and Monitoring Viewer for normal operations.
8. Review IAM policy for unknown/default service accounts and broad primitive roles.
9. Export an IAM policy snapshot into the security evidence record without credentials.
10. Remove the temporary project override that sets the Domain Restricted Sharing
    organization policy to allow all. First verify that Cloud Billing can still
    publish a test budget notification to `billing-budget-notifications`, record
    the required Google-managed billing service-agent principal, and replace the
    broad override with the narrowest supported organization-policy exception.
    Do not promote staging to production while the allow-all override remains.

## 11. Company Phase 0.8 — production deployment

Production is not developed interactively. It receives the same Terraform modules and exact container digests that passed staging.

Sequence:

1. Review production Terraform plan.
2. Apply foundational IAM/network/storage/messaging.
3. Insert production secret values manually.
4. Deploy the staging-tested image digests.
5. Create only approved production users/tenants.
6. Run smoke, IAM-negative, health and cost checks.
7. Upload the seed corpus only if approved for production; otherwise use dedicated non-sensitive production verification fixtures and remove them afterward.
8. Configure production frontend/DNS/CORS.
9. Observe for 24–48 hours under low concurrency.
10. Store the production deployment and rollback evidence.

Production rollback uses the previous Cloud Run revision/image digest and previous Terraform state generation. No destructive data migration is part of initial deployment.

## 12. Work after the clean deployment

After Company Phase 0.8, continue [`production-plan/PHASES.md`](production-plan/PHASES.md):

1. Versioned contracts.
2. Full OpenTelemetry/SLO implementation.
3. Durable/idempotent ingestion control plane.
4. Google Enterprise Document OCR vs PyMuPDF/Docling bbox bake-off.
5. Production multilingual spatial ingestion.
6. Qdrant/index lifecycle and HA.
7. Follow-up memory and adaptive HyDE.
8. Routing/reranking/context optimization.
9. Grounded synthesis, prompt-injection, PII and document ACL hardening.
10. Cost/performance optimization.
11. Scale, chaos and disaster-recovery validation.

## 13. Information required from Rohit before implementation

Do not provide credentials or secret values. Provide only:

- company organization ID or confirmation that no organization exists;
- whether an `IRIS` folder already exists;
- staging project ID to create/use;
- production project ID to create/use;
- active billing account ID and currency;
- approved region/data-residency decision;
- monthly staging and production budgets;
- GitHub organization/repository and protected production branch/environment;
- staging/production frontend domains;
- notification emails/channels;
- whether CEO will grant the strict temporary roles or the empty-project temporary Owner fallback;
- confirmation that the eight local PDFs are approved as staging test data.

## 14. Stop conditions

Stop and request direction if:

- the project is created under the wrong organization/folder;
- billing identity appears to belong to a different legal customer;
- Terraform targets an unexpected project;
- a plan contains secret values or destructive operations;
- the requested region cannot provide required services/models;
- a command requires a downloadable service-account key;
- staging tests reveal cross-tenant access, data loss, duplicate active chunks, or fabricated citations;
- projected cost exceeds the approved budget;
- production differs from the tested staging artifact/configuration without a reviewed exception.

## 15. Definition of bootstrap complete

The GCP bootstrap is complete only when:

- staging and production are company-owned and correctly billed;
- infrastructure is reproducible from reviewed Terraform;
- humans and CI authenticate without service-account JSON keys;
- runtime services have least-privilege, resource-scoped roles;
- unit tests are hermetic and critical fixes pass;
- staging has ingested the seed corpus and stored its benchmark evidence;
- production deploys immutable tested digests;
- temporary bootstrap permissions are revoked;
- the temporary Domain Restricted Sharing allow-all override has been removed
  and the effective organization policy has been verified;
- budgets, quotas, logs, alerts, rollback and ownership are documented and tested.
