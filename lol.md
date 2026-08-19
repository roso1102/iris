

Here is exactly what I would add to Phase 4.

**Production Route**
Use this route for production-level security:

```text
Vercel frontend
  -> Firebase Auth login
  -> api.yourdomain.com
  -> Google External HTTPS Load Balancer
  -> Cloud Armor
  -> Cloud Run retrieval-api
  -> app verifies Firebase JWT
  -> tenant_id comes only from verified JWT
```

For `retrieval-api`, use:

```text
Cloud Run ingress = internal-and-cloud-load-balancing
Cloud Run IAM = allow unauthenticated is acceptable only because direct public URL is blocked by ingress
App-level Firebase JWT = mandatory on every user route
Cloud Armor = rate/IP/WAF layer at load balancer
```

For `ingestion-worker`, use:

```text
Cloud Run ingress/IAM = private machine route
Pub/Sub/Eventarc service account has run.invoker
No Firebase auth on Pub/Sub routes
Firebase admin auth only on QA /memory route if exposed
```

Why this route: it gives you edge protection, blocks direct Cloud Run URL bypass, keeps browser auth simple, and still enforces tenant identity in your code. Google’s own Cloud Run end-user auth tutorial uses the pattern of clients sending Identity Platform/Firebase ID tokens to the backend, and the backend verifying them. Firebase Admin docs also confirm server-side ID token verification and optional revoked-token checks. Sources: [Cloud Run end-user auth](https://docs.cloud.google.com/run/docs/tutorials/identity-platform?authuser=00), [Firebase verify ID tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens), [Firebase session revocation](https://firebase.google.com/docs/auth/admin/manage-sessions?authuser=19&hl=en).

**Add To Phase 4**
1. **Security Architecture Decision**
Add a section:

```text
Production exposure model:
- retrieval-api is reachable only through External HTTPS Load Balancer + Cloud Armor.
- Cloud Run direct URL is blocked with ingress=internal-and-cloud-load-balancing.
- Firebase JWT is still verified inside retrieval-api.
- ingestion-worker Pub/Sub routes remain Cloud Run IAM-only.
```

This removes the current ambiguity between `--no-allow-unauthenticated` and browser Firebase JWTs.

2. **Auth Context**
Add shared auth module:

```text
services/common/auth/jwt.py
```

It should produce:

```text
AuthContext:
  uid
  tenant_id
  role
  email
  email_verified
```

Rules:

```text
missing token -> 401
invalid/expired token -> 401
missing tenant_id claim -> 403
unknown role -> 403
email_verified false -> 403, unless explicitly allowed for dev/test
```

3. **Route Auth Matrix**
Add a route table to the plan.

```text
retrieval-api /healthz
  auth: none or internal only
  returns: no sensitive config

retrieval-api /search
  auth: Firebase JWT
  tenant: JWT only
  rate limit: yes

retrieval-api /query
  auth: Firebase JWT
  tenant: JWT only
  rate limit: yes
  cost limits: yes

retrieval-api /doc-status/{doc_id}
  auth: Firebase JWT
  tenant: JWT only

retrieval-api /sessions
  auth: Firebase JWT
  tenant: JWT only

retrieval-api /documents/{doc_id}
  auth: Firebase JWT
  tenant: JWT only

retrieval-api /documents/{doc_id}/view-url
  auth: Firebase JWT
  tenant: JWT only
  signed URL TTL: 15 minutes

ingestion-worker POST /
  auth: Cloud Run IAM / Eventarc only
  no Firebase

ingestion-worker POST /ingest
  auth: Cloud Run IAM or internal admin only
  no public browser access

ingestion-worker GET /memory
  auth: Firebase JWT
  role: admin only
```

4. **ID Validation**
Add strict validation before using IDs in Firestore, GCS, or Qdrant.

```text
tenant_id from JWT: ^[a-zA-Z0-9_-]{1,64}$
doc_id:             ^[a-zA-Z0-9_-]{1,128}$
session_id:         ^[a-zA-Z0-9_-]{1,128}$
role:               admin | member
```

Reject slashes, dots, URL encoding tricks, empty strings, long strings.

5. **Tenant Rewrite Rule**
Add this as a non-negotiable:

```text
No user-facing API accepts tenant_id in header, path, query param, or body.
If client sends tenant_id anyway, ignore it.
Every Qdrant/Firestore/GCS operation uses auth.tenant_id only.
```

6. **Document Authorization**
Tenant-level auth is not enough if multiple users in one tenant should have limited sessions.

Add this explicitly:

```text
Phase 4 guarantees tenant isolation.
Phase 4 does not yet guarantee per-user document ACL unless added below.
```

My recommendation: add basic session ownership now.

```text
sessions/{session_id} has:
  tenant_id
  owner_uid
  document_ids
  created_at
```

For `/query`:

```text
If session_id is provided:
  load session by auth.tenant_id/session_id
  verify owner_uid == auth.uid OR role == admin
  use session.document_ids as allowed docs
  intersect with request.doc_ids if request.doc_ids exists
```

This avoids “any member can query every tenant doc.”

7. **Signed URL Hardening**
Before generating signed URL:

```text
verify doc_id format
load Firestore doc metadata at tenants/{tenant}/documents/{doc_id}
confirm doc exists and tenant_id matches
sign only path {tenant_id}/{doc_id}.pdf
TTL = 900 seconds
method = GET
```

Do not sign arbitrary client-provided paths.

8. **Request Size / Cost Limits**
Add limits:

```text
query max chars: 2,000-4,000
history max turns: 6
history max total chars: 12,000
doc_ids max count: 25
top_k max for /query: 20
top_k max for /search: 50 or 100 only if internal/dev
session name max chars: 100
```

Why: authenticated users can still create cost abuse.

9. **Rate Limiting**
Implement two layers:

Phase 4 local:

```text
in-memory per tenant fixed window
/search and /query only
default: 30/min/tenant
```

Production later but plan now:

```text
Cloud Armor at load balancer:
  IP based limits
  geo/block rules if needed
  WAF managed rules
```

Note: in-memory limits are per Cloud Run instance and not enough alone.

10. **Revoked Token Policy**
Add:

```text
/search and /query:
  verify normal Firebase token, no revocation check by default for latency

DELETE routes, signed URL, /memory admin:
  verify token with check_revoked=True if latency acceptable
```

Firebase docs note revocation checks require an extra backend request, so use them selectively.

11. **Least Privilege IAM**
Current plan should reduce broad roles.

Change target from:

```text
roles/datastore.owner
roles/storage.objectAdmin
```

To preferably:

```text
retrieval-api:
  Firestore: datastore.user or custom role
  GCS: objectViewer + object delete/signing needs
  IAM: serviceAccountTokenCreator on itself only if needed for signed URLs
  Vertex AI: aiplatform.user

ingestion-worker:
  Firestore: only progress/document metadata write
  GCS: objectViewer/objectCreator/objectAdmin only if required for split/delete
  Pub/Sub: publisher/subscriber as needed
  Vertex AI: aiplatform.user
```

If custom roles are too much for MVP, add a TODO:

```text
Broad IAM accepted only for MVP. Must be reduced before external customer data.
```

12. **Cloud Run Ingress Settings**
Add exact deploy intent:

```text
retrieval-api:
  ingress=internal-and-cloud-load-balancing
  min-instances=1
  behind HTTPS LB + Cloud Armor

ingestion-worker:
  no public unauthenticated access
  Eventarc/PubSub service account only
```

If you do not add load balancer yet, temporary MVP route:

```text
retrieval-api allow unauthenticated
Firebase JWT required by app
Cloud Run URL public temporarily
Cloud Armor/API Gateway deferred
```

But mark it as weaker.

13. **Debug Route Safety**
For `/healthz`:

```text
Do not reveal Qdrant internal IP, collection names, project IDs, model names in public health response.
```

Use:

```text
{"status":"ok"}
```

Add `/internal/healthz` later for detailed checks behind admin/IAM.

14. **Logging Rules**
Add:

```text
Never log full JWT
Never log full query if documents may be sensitive
Never log raw Pub/Sub payload
Hash or truncate tenant_id/user_id where possible
Log security events separately:
  auth_failed
  tenant_spoof_attempt
  rate_limited
  signed_url_created
  delete_requested
```

15. **Security Tests To Add**
Add these exact tests:

```text
Tenant A token + tenant-b header -> only Tenant A
Tenant A token + tenant_id in body -> ignored
Tenant A token + Tenant B doc_id -> 404 or empty, never leaked
Member token -> /memory denied
Admin token -> /memory allowed
Invalid role -> denied
Missing tenant_id claim -> denied
Malformed doc_id with slash -> denied
Signed URL for nonexistent doc -> 404
Signed URL for cross-tenant doc -> 404
DELETE cross-tenant doc -> no-op/404, no leakage
Huge query/history -> 413 or 422
Rate limit exceeded -> 429
```

**How To Implement Without Breaking Current Work**
Do it in this order:

1. Add auth module and tests.
2. Patch retrieval tests to use fake JWT auth dependency.
3. Replace `tenant_id: Header(...)` with `auth.tenant_id`.
4. Keep store methods unchanged because they already accept `tenant_id`.
5. Add ID validators before Firestore/GCS/Qdrant calls.
6. Add sessions endpoints using Firestore.
7. Add signed URL endpoint with mocked tests.
8. Add QA JWT auth only to `/memory`.
9. Leave ingestion Pub/Sub routes untouched.
10. Only after local tests pass, change Cloud Run exposure/load balancer settings.

**What Might Break And How To Fix**
```text
Break: frontend/eval scripts still send tenant-id header
Fix: send Authorization: Bearer <Firebase ID token>

Break: Cloud Run blocks browser calls with --no-allow-unauthenticated
Fix: either use HTTPS LB route or temporarily allow unauthenticated + app JWT

Break: Pub/Sub ingestion starts returning 401
Fix: remove Firebase auth from POST / and POST /ingest; keep Cloud Run IAM

Break: Firestore rules deny frontend reads
Fix: ensure every doc under /tenants/{tenant_id}/... stores tenant_id field

Break: signed URL fails in Cloud Run
Fix: grant retrieval-api SA serviceAccountTokenCreator on itself or use IAMCredentials signing path

Break: tests become painful due to Firebase Admin
Fix: patch verify_firebase_token in tests; do not mint real tokens for unit tests

Break: users can query all tenant docs
Fix: session_id loads session.document_ids and intersects request.doc_ids
```

**Actionplan Placement**
Update Phase 4.0 like this:

```text
Phase 4.0 — Auth & Multi-Tenant Security
  4.1 Firebase JWT verification
  4.2 Tenant rewrite from JWT
  4.3 ID validation and anti-IDOR rules
  4.4 Session CRUD + session document authorization
  4.5 Signed GCS URL endpoint
  4.6 QA admin route hardening
  4.7 Request size and cost limits
  4.8 Local rate limiting
  4.9 Firestore rules + emulator tests
  4.10 Cloud Run exposure decision
  4.11 IAM least-privilege cleanup
  4.12 Penetration test suite
```

Then in later phases:

```text
Phase 5:
  frontend Firebase login
  frontend sends ID token
  citation UI consumes /query and signed URLs

Phase 6:
  session-scoped retrieval becomes mandatory/default
  chat history access scoped by auth.uid/role

Phase 7:
  real quota/billing limits, not just in-memory rate limit

Phase 16:
  full Cloud Armor/WAF tuning
  audit logs
  custom IAM roles
  org policies
  DR/security incident runbooks
```

My final recommendation: for real production security, choose **HTTPS Load Balancer + Cloud Armor + Cloud Run ingress restricted to LB + Firebase JWT verified inside app**. That is the clean path that won’t fight your Vercel frontend and won’t break Pub/Sub ingestion.