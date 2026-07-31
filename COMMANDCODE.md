# Command Code — project instructions (auto-loaded each session)

## First, read the shared context

Read **`CONTEXT.md`** in the repository root before doing any work. It is the living handoff note shared between AI assistants working on this project (Command Code, Antigravity). It contains: current phase, binding design decisions, session log, gotchas, and open questions.

For depth, consult in order:
1. `CONTEXT.md` — living state (start here)
2. `README.md` — architecture overview, ingestion/retrieval pipelines
3. `SRS.md` — formal requirements (FR-1…FR-10, NFRs, data model)
4. `ACTIONPLAN.md` — phase-by-phase build plan with benchmarks and exit criteria

## STRICT TEMPLATE RULES for CONTEXT.md (mandatory)

`CONTEXT.md` uses a numbered, frozen template. You MUST follow the rules embedded in its header comment block:
- **Section headers (## 1. … ## 6.) are FIXED.** Never rename, reorder, merge, or add sections.
- **Sections 1 and 3 are FROZEN** (derived from README/SRS/ACTIONPLAN). Only the user may authorize changes.
- **Section 4 (Session Log) is append-only:** add ONE bullet per session at the bottom, never edit or delete old bullets.
- **Do not reformat the file** (headings, bullets, bold markers, dividers, comment block).
- If you believe the template itself must change, propose it to the user — never change it unilaterally.

## Working agreement

- **Never** take actions that violate the "Key Decisions" section of `CONTEXT.md` (tenant isolation at engine level, `ModelProvider` for all model calls, cost caps, VLM router rules).
- When you complete work or learn something durable, update `CONTEXT.md` → Section 4 Session Log (date · tool · what was done · decisions · next). Keep it to 3 lines max.
- Do not rewrite `README.md`, `SRS.md`, or `ACTIONPLAN.md` without explicit request — they are the canonical specs.
- MVP boundary is end of Phase 5.0 (see `ACTIONPLAN.md`). Phases 9.0 → 10.0 → 11.0 form a strict dependency chain.
