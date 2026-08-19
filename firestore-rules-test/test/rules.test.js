/*
 * IRIS Phase 4.0 — Firestore Security Rules tests.
 *
 * Runs against the local Firebase Emulator:
 *   1. npx firebase emulators:exec --only firestore "npm test"
 *      (from repo root; loads firestore.rules via firebase.json)
 *   2. or: start the emulator manually, then npm test.
 *
 * Verifies the tenant-scoping rules in firestore.rules:
 *   - same-tenant read allowed
 *   - cross-tenant read denied
 *   - write with matching tenant_id allowed
 *   - write with mismatched tenant_id denied
 *   - unauthenticated denied
 *   - nested messages subcollection cross-tenant denied
 */

const { initializeTestEnvironment, assertFails, assertSucceeds } = require('@firebase/rules-unit-testing');
const fs = require('fs');
const path = require('path');

const PROJECT_ID = 'iris-rules-test';
// firestore.rules lives at the repo root, one level above this test file.
const RULES_PATH = path.resolve(__dirname, '..', '..', 'firestore.rules');

let testEnv;

before(async () => {
  const rules = fs.readFileSync(RULES_PATH, 'utf8');
  testEnv = await initializeTestEnvironment({
    projectId: PROJECT_ID,
    firestore: { rules, host: '127.0.0.1', port: 8088 },
  });
});

after(async () => {
  await testEnv.cleanup();
});

function authed(tenantId, uid = `user-${tenantId}`) {
  return testEnv.authenticatedContext(uid, {
    tenant_id: tenantId,
    role: 'member',
  });
}

function unauthed() {
  return testEnv.unauthenticatedContext();
}

describe('IRIS Firestore security rules', () => {
  // Seed data through the rules-disabled admin SDK so rule tests start clean.
  async function seed() {
    await testEnv.withSecurityRulesDisabled(async (admin) => {
      const db = admin.firestore();
      await db.doc('tenants/tenant-a/sessions/s1').set({
        tenant_id: 'tenant-a',
        name: 'Budget review',
      });
      await db.doc('tenants/tenant-a/sessions/s1/messages/m1').set({
        tenant_id: 'tenant-a',
        text: 'seed message',
      });
      await db.doc('tenants/tenant-b/sessions/s1').set({
        tenant_id: 'tenant-b',
        name: 'Tenant B session',
      });
    });
  }

  beforeEach(seed);

  it('allows same-tenant read of a session document', async () => {
    const db = authed('tenant-a').firestore();
    await assertSucceeds(db.doc('tenants/tenant-a/sessions/s1').get());
  });

  it('denies cross-tenant read', async () => {
    const db = authed('tenant-b').firestore();
    await assertFails(db.doc('tenants/tenant-a/sessions/s1').get());
  });

  it('denies unauthenticated read', async () => {
    const db = unauthed().firestore();
    await assertFails(db.doc('tenants/tenant-a/sessions/s1').get());
  });

  it('allows create with matching tenant_id', async () => {
    const db = authed('tenant-a').firestore();
    await assertSucceeds(db.doc('tenants/tenant-a/sessions/s2').set({
      tenant_id: 'tenant-a',
      name: 'New session',
    }));
  });

  it('denies create with mismatched tenant_id', async () => {
    const db = authed('tenant-a').firestore();
    await assertFails(db.doc('tenants/tenant-b/sessions/s2').set({
      tenant_id: 'tenant-b',
      name: 'Sneaky session',
    }));
  });

  it('denies create whose data.tenant_id mismatches the token', async () => {
    const db = authed('tenant-a').firestore();
    await assertFails(db.doc('tenants/tenant-a/sessions/s3').set({
      tenant_id: 'tenant-b',
      name: 'Claim mismatch',
    }));
  });

  it('denies update that changes tenant_id', async () => {
    const db = authed('tenant-a').firestore();
    await assertFails(db.doc('tenants/tenant-a/sessions/s1').update({
      tenant_id: 'tenant-b',
    }));
  });

  it('denies cross-tenant read of nested messages subcollection', async () => {
    const db = authed('tenant-b').firestore();
    await assertFails(db.doc('tenants/tenant-a/sessions/s1/messages/m1').get());
  });

  it('allows same-tenant read of nested messages', async () => {
    const db = authed('tenant-a').firestore();
    await assertSucceeds(db.doc('tenants/tenant-a/sessions/s1/messages/m1').get());
  });

  it('denies write to ingestion_progress (server-only)', async () => {
    const db = authed('tenant-a').firestore();
    await assertFails(db.doc('ingestion_progress/tenant-a/documents/d1').set({
      total_pages: 10,
    }));
  });
});
