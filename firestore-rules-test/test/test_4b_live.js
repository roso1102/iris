/* Test 4-B: live Firestore rules cross-tenant test.
 * Uses the Firebase Web SDK directly against production Firestore with the
 * test users' ID tokens. Proves rules enforce tenant isolation.
 */
const { initializeApp } = require("firebase/app");
const { getFirestore, doc, getDoc, setDoc, collection, getDocs } = require("firebase/firestore");
const fs = require("fs");

const API_KEY = "AIzaSyBpg_eigHY8GIjf7Tsz4-M8a8f0cSJnl90";
const PROJECT = "naturepivot-rag";
const AUTH_DOMAIN = "naturepivot-rag.firebaseapp.com";

const tokenA = fs.readFileSync(process.env.TEMP + "\\token_a.txt", "utf8").trim();
const tokenB = fs.readFileSync(process.env.TEMP + "\\token_b.txt", "utf8").trim();

// The Firestore Web SDK needs the ID token passed via a custom auth token.
// We use the REST API directly instead (firestore.googleapis.com) which
// accepts `Authorization: Bearer <ID token>` — the same enforcement path
// the Web SDK uses (rules apply identically).

const BASE = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents`;

async function fsGet(token, path) {
  const resp = await fetch(`${BASE}/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return resp.status;
}

async function fsWrite(token, path, data) {
  const resp = await fetch(`${BASE}/${path}?updateMask.fieldPaths=x`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields: { x: { stringValue: "y" }, tenant_id: { stringValue: path.split("/")[1] } } }),
  });
  return resp.status;
}

async function main() {
  let pass = 0, fail = 0;

  async function check(name, cond) {
    if (cond) { console.log(`  PASS: ${name}`); pass++; }
    else { console.log(`  FAIL: ${name}`); fail++; }
  }

  // Tenant A session created earlier via API.
  const sessionA = "2b6de03f-6d16-40e3-9a6b-b32b73cefe59";
  const sessionB = "766d2411-4b82-4772-b843-0322352b9f58";
  const pathA = `tenants/tenant-a/sessions/${sessionA}`;
  const pathB = `tenants/tenant-b/sessions/${sessionB}`;

  console.log("== Test 4-B: Firestore rules (live) ==");
  console.log("1. Tenant A reads own session (expect 200):");
  const r1 = await fsGet(tokenA, pathA);
  await check("same-tenant read allowed", r1 === 200);

  console.log("2. Tenant A reads Tenant B session (expect 403):");
  const r2 = await fsGet(tokenA, pathB);
  await check("cross-tenant read denied", r2 === 403);

  console.log("3. Tenant A writes to Tenant B path (expect 403):");
  const r3 = await fsWrite(tokenA, pathB, {});
  await check("cross-tenant write denied", r3 === 403);

  console.log("4. Tenant A writes to own path (expect 200):");
  const r4 = await fsWrite(tokenA, pathA, {});
  await check("same-tenant write allowed", r4 === 200);

  console.log("5. Unauthenticated read (expect 403):");
  const r5 = await fsGet("", pathA);
  await check("unauthenticated read denied", r5 === 403);

  console.log(`\nRESULT: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error("ERROR:", e.message); process.exit(2); });
