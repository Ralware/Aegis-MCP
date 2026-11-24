# Trust Gate — Hackathon MVP Tracker

> **Purpose:** A focused, checkbox-driven execution plan for delivering a working Trust Gate vertical slice. This file is intentionally much smaller than `Trust_Gate_Full_Product_Roadmap.md`.
>
> **MVP proof:** An authenticated MCP client calls tools through Trust Gate; Trust Gate sanitizes a sensitive document, remembers its classification/provenance, intercepts an attempted external send, requires approval for the exact operation, and proves that rejected operations never reach the upstream server.

---

## 0. How to use this tracker

Keep this file in the repository and update it during the hackathon. Check each status only when the evidence exists.

For every work package, track three independent states:

- **Implemented** — code is present and connected to the running system.
- **Tested** — the listed acceptance tests pass; record test IDs and evidence.
- **Audited** — another team member reviewed identity, authorization, failure behavior, data handling and bypass risks.

A green UI or a successful happy-path demo is not evidence that security enforcement works. Use mock-server execution counters and persisted audit events to prove the behavior.

### Work package status template

```md
- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Commit / PR:
- Test IDs:
- Evidence:
- Findings / follow-up:
```

### Timebox and team assumptions

This plan uses an **illustrative 72-hour hackathon** and **four workstreams** because the event duration and team size were not specified. Adjust the timeboxes to the actual event. If the team is smaller, combine roles; do not remove the security gates.

| Workstream | Primary ownership | Must coordinate with |
|---|---|---|
| A — Gateway/backend | FastAPI, auth, MCP server/client, routing, PostgreSQL | Security and integration |
| B — Security | Policy engine, DLP, artifact lineage/taint, approval verification | Gateway/backend |
| C — Frontend | Minimal authenticated approval page and activity view | Backend/API |
| D — Integration/demo/QA | Mock MCP servers, counters, scripted client, test fixtures, Docker/demo | All workstreams |

### MVP non-goals

- [ ] Real Gmail/Google Drive OAuth integrations.
- [ ] Web Push notifications or a mobile app.
- [ ] Redis, Kubernetes or microservices.
- [ ] Enterprise multi-tenant delegation or multiple identity providers.
- [ ] Advanced ML anomaly detection.
- [ ] Full SIEM integration or a complete enterprise administration dashboard.
- [ ] Claims of perfect prompt-injection or PII detection.

Use synthetic data only. The real product roadmap remains in `Trust_Gate_Full_Product_Roadmap.md`.

---

# 1. MVP definition and acceptance target

## 1.1 The vertical slice

The demo follows one end-to-end story:

1. A user/client authenticates to Trust Gate.
2. The AI client discovers and invokes approved namespaced Gmail/Drive tools through Trust Gate.
3. A document is retrieved from the mock Drive server.
4. DLP redacts sensitive identifiers before the result reaches the AI and records the document as `CONFIDENTIAL` with a stable artifact ID.
5. A malicious email is retrieved and marked as untrusted.
6. The AI/demo client attempts to send the confidential artifact to an external recipient by stable artifact ID.
7. Trust Gate resolves the artifact's classification/taint and returns `REQUIRE_APPROVAL` without calling the mock Gmail send tool.
8. The user rejects the request; the upstream send counter stays at zero.
9. A separate legitimate test request is approved; Trust Gate executes the exact frozen payload once.
10. The audit/activity view shows the full chain of decisions and outcomes.

## 1.2 Mandatory MVP acceptance criteria

- [ ] A client authenticates before using the protected MCP endpoint.
- [ ] The principal is derived from verified auth context; no tool argument can choose `user_id`.
- [ ] At least one approved tool from each mock upstream server is discoverable through Trust Gate.
- [ ] Every tool invocation passes through one central execution service.
- [ ] A blocked call never reaches the upstream mock server (verified by a counter).
- [ ] Every model-facing response is inspected; if inspection fails, raw result content is withheld.
- [ ] A retrieved confidential document is associated with a stable artifact ID and taint record.
- [ ] An outbound send resolves attachment IDs and uses artifact classification/taint before policy evaluation.
- [ ] A confidential external send returns `REQUIRE_APPROVAL` before upstream execution.
- [ ] Approval is authenticated and bound to the exact user, server, tool, recipient, arguments, artifact IDs and content hashes.
- [ ] Rejected, expired, modified or replayed approvals do not execute.
- [ ] An approved frozen operation can execute at most once in the controlled test environment.
- [ ] Audit events are persisted in PostgreSQL and do not expose raw secrets or confidential document contents.
- [ ] The scripted demo can reproduce the complete story without relying on unpredictable LLM behavior.

## 1.3 Canonical vocabulary — do not vary these values

| Concept | Canonical values |
|---|---|
| Policy decision | `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK` |
| Classification | `PUBLIC`, `INTERNAL`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED` |
| Approval status | `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, `CONSUMED`, `CANCELLED` |
| Execution status | `NOT_STARTED`, `EXECUTING`, `SUCCEEDED`, `FAILED`, `UNKNOWN`, `RECONCILIATION_REQUIRED` |
| Tool review status | `PENDING_REVIEW`, `APPROVED`, `REVIEW_REQUIRED`, `QUARANTINED`, `REJECTED`, `DISABLED` |

**Tool naming:** Use `(server_id, upstream_tool_name)` as the canonical internal key. Store `exposed_tool_name` as the namespaced name presented to the AI, e.g. `gmail_send_email`. Do not mix these identities in policy rules or audit records.

---

# 2. Architecture decisions to lock before implementation

## 2.1 Minimal MVP architecture

```text
Scripted MCP demo client / optional AI host
          |
          | Bearer token over Streamable HTTP
          v
Northbound auth middleware / token verifier
          |
          v
Trust Gate low-level MCP Server
  on_list_tools -> approved dynamic registry
  on_call_tool  -> central execution service
          |
          v
Central execution pipeline
  principal + tool + schema validation
  resolve attachment/artifact IDs
  retrieve classification + taint
  threat signal + deterministic policy
      |              |              |
    ALLOW      REQUIRE_APPROVAL    BLOCK
      |              |              |
      |         frozen payload      no upstream call
      |         + approval UI
      |              |
      +------ approved executor
                     |
                     v
             Mock Gmail / Drive MCP
                     |
                     v
          Response inspection + DLP
                     |
          +----------+----------+
          |                     |
     Sanitized result      Inspection error
          |                 (withhold raw data)
          v
        MCP client

PostgreSQL: principals/tokens, server & tool registry,
invocations, artifacts/taint, approvals, audit events
```

## 2.2 Northbound identity for the MVP

- [ ] Use Streamable HTTP for the demo gateway so there is an explicit HTTP authentication boundary.
- [ ] Create one development-only bearer token in `.env` or seed configuration.
- [ ] Map the verified token to a single seeded principal such as `demo-user`.
- [ ] Prefer the pinned MCP SDK's token verifier/auth middleware; if a small custom verifier is needed, validate it at the ASGI/HTTP boundary before MCP handling.
- [ ] Inject the principal into trusted request context.
- [ ] Do not accept `user_id`, principal, tenant or role from model-controlled tool arguments.
- [ ] Keep the token out of source control, prompts, browser bundles, tool results and logs.
- [ ] Protect approval-page APIs with authentication and the same principal ownership check.
- [ ] Test the scripted MCP client with the bearer token. Treat connection to a third-party desktop host as optional unless its auth configuration is verified.

This is a demo-only token arrangement, not production OAuth. The full product roadmap defines the production OAuth 2.1 resource-server work.

## 2.3 Execution workspace and taint scope

- [ ] Assign a server-side demo workspace to the authenticated principal.
- [ ] Do not accept an unverified `execution_context_id` from tool arguments.
- [ ] Associate retrieved artifacts with the authenticated principal and this trusted workspace.
- [ ] For the MVP, use this conservative per-principal workspace rather than pretending a generic MCP session ID proves agent-run isolation.
- [ ] Document that finer execution-context tracking requires a trustworthy context binding from the host/client.

## 2.4 Outbound artifact resolution rule

- [ ] Mock Drive returns a stable `artifact_id`/`file_id`, classification-relevant content and content hash.
- [ ] Trust Gate stores artifact ownership, source server/tool, classification, workspace and content hash.
- [ ] Mock Gmail `send_email` accepts `attachment_ids`, not only a display filename.
- [ ] Before a send, Trust Gate resolves every attachment ID against the artifact registry and verifies owner/workspace.
- [ ] A filename alone is not evidence of identity or classification.
- [ ] Unknown/unresolvable attachments are not silently considered `PUBLIC`; block or require review by explicit policy.
- [ ] For any later production connector, re-resolve/re-hash attachment content immediately before delayed execution where supported.

## 2.5 Fail-closed rules

- [ ] Missing/invalid auth: reject before tool execution.
- [ ] Policy engine unavailable: do not execute protected tools.
- [ ] Mandatory response inspection/DLP unavailable: withhold raw tool result content, including for reads; return a sanitized error only.
- [ ] Outbound attachment cannot be resolved/classified: do not silently allow the write.
- [ ] Approval service/database unavailable: do not execute an approval-required operation.
- [ ] Tool definition is unknown, unreviewed or quarantined: do not execute it.
- [ ] Never convert an unknown execution outcome into a blind retry.

---

# 3. Implementation sprint — 72-hour example

The suggested schedule assumes four people working in parallel. Reassign owners and adjust durations to fit the actual hackathon. Keep the dependency order: auth + audit boundary → gateway → policy → DLP/taint → approval → UI/demo → adversarial QA.

| Timebox | Work package | Primary owner | Exit condition |
|---|---|---|---|
| T+0–4h | Scope lock, repo, contracts, environment, DB and audit skeleton | All / A | App starts, migrations run, event interface exists |
| T+4–14h | Authenticated MCP gateway and mock servers | A + D | Authenticated client invokes mock read through Trust Gate |
| T+14–22h | Tool registry, central execution service and policy engine | A + B | Allow/block/approval decisions enforced; counter proves block |
| T+22–32h | Presidio response DLP, artifact registry and taint | B + D | Confidential Drive result is sanitized and tainted |
| T+32–42h | Approval persistence, exact-operation verification and minimal UI | A + B + C | Rejected send never executes; exact approved send executes once |
| T+42–52h | Audit/activity UI, prompt-injection fixture and scripted demo client | C + D | One-click repeatable demo with real backend events |
| T+52–64h | Required security tests, failure injection and fixes | All | MVP test gate passes; no known critical bypass |
| T+64–72h | Freeze build, reset script, rehearsal, slides and backup demo | C + D / All | Stable live demonstration and evidence package |

If the event is shorter than 72 hours, remove optional UI polish and schema-change demonstration before removing auth, response withholding, taint tracking or exact-operation approval.

---

# 4. Work packages and checklists

## WP-0 — Scope, contracts and repository foundation

**Goal:** A reproducible local project, shared contracts and early audit instrumentation.

- [ ] Create repository and branch/PR conventions.
- [ ] Create `backend/`, `frontend/`, `mock_servers/`, `docs/`, `planning/` and `tests/` folders.
- [ ] Initialize FastAPI and React + TypeScript.
- [ ] Pin Python, Node, official MCP Python SDK and Presidio versions.
- [ ] Record the protocol version and target client version.
- [ ] Create `.env.example`; keep actual secrets out of Git.
- [ ] Start PostgreSQL with Docker Compose.
- [ ] Add SQLAlchemy models and Alembic initial migration.
- [ ] Create request/correlation ID middleware.
- [ ] Define a central `AuditWriter` interface and persist a simple startup/request event.
- [ ] Define shared enums and request/response contracts before parallel development.
- [ ] Document one-command startup and test commands.

**Exit gate:** A clean checkout starts the backend, frontend and PostgreSQL; migrations and a basic test run pass; no real credentials are required.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Commit / PR:
- Evidence:

## WP-1 — Mock MCP servers and northbound authentication

**Goal:** A controlled, authenticated test environment.

### Mock Gmail MCP server

- [ ] Implement `search_emails`.
- [ ] Implement `read_email`.
- [ ] Implement `send_email` with attachment IDs.
- [ ] Maintain a durable/in-memory send invocation counter visible to tests.
- [ ] Provide benign and malicious email fixtures.

### Mock Drive MCP server

- [ ] Implement `search_files` or a deterministic fixture lookup.
- [ ] Implement `read_file` returning stable `file_id`/`artifact_id` and synthetic document content.
- [ ] Include one confidential financial statement with fake PAN/Aadhaar/phone/account values and useful expense data.
- [ ] Maintain a read counter and expose test-only state to the QA harness.

### Northbound identity

- [ ] Implement development bearer token verification over the HTTP MCP endpoint.
- [ ] Map the verified token to `demo-user` in trusted request context.
- [ ] Reject absent, invalid and expired tokens.
- [ ] Ensure tool schemas do not contain an authoritative `user_id` input.
- [ ] Protect the minimal approval API with the same principal check.

**Exit gate:** The scripted MCP client cannot call Trust Gate without the valid demo token; with the token it can connect and reach a mock server.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T01, T02, T11
- Evidence:

## WP-2 — MCP gateway, tool registry and central execution path

**Goal:** Every call passes through a single gate.

- [ ] Implement upstream MCP clients for mock Gmail and Drive.
- [ ] Prototype/use the official SDK low-level `Server` API for dynamic `on_list_tools` and centralized `on_call_tool` dispatch.
- [ ] Preserve discovered JSON Schemas; do not require one statically written Python function per upstream tool.
- [ ] Store both canonical `(server_id, upstream_tool_name)` and namespaced `exposed_tool_name`.
- [ ] Expose only the initially approved mock tools.
- [ ] Validate arguments against the stored tool schema.
- [ ] Reject unknown/unregistered tool names in the call handler even if a client submits them directly.
- [ ] Route all invocations to one `execute_tool` service.
- [ ] Add upstream invocation counters for each mock tool.
- [ ] Emit request, decision and execution audit events.
- [ ] Add timeout and safe upstream error handling.

**Exit gate:** Normal read executes through Trust Gate; blocked operation is rejected before upstream and its upstream counter remains unchanged.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T02, T03, T12, T20
- Evidence:

## WP-3 — Deterministic policy engine

**Goal:** The backend decides `ALLOW`, `REQUIRE_APPROVAL` or `BLOCK`.

- [ ] Define typed policy input using verified principal, server ID, upstream tool name, exposed name, arguments, resolved artifacts, classification/taint, destination and threat signals.
- [ ] Implement the three canonical decisions only: `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`.
- [ ] Add allow rule for permitted mock Gmail search and Drive read.
- [ ] Add block rule for an unauthorized destructive operation.
- [ ] Add require-approval rule for confidential/tainted attachment to an external recipient.
- [ ] Add safe default for unknown tools, missing identity, unresolved attachment or unknown classification.
- [ ] Record policy ID/version and human-readable reason.
- [ ] Ensure an LLM/threat classifier cannot grant access or override policy.

**Exit gate:** Each decision is observed in the backend and proven by upstream counters, not only by UI text.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T02, T03, T07, T17
- Evidence:

## WP-4 — Response DLP, artifact registry and taint tracking

**Goal:** Protect information before it reaches the model and remember sensitive artifact provenance for later outbound decisions.

### Response inspection

- [ ] Integrate Presidio Analyzer and Anonymizer.
- [ ] Inspect the pinned Presidio package for built-in `IN_PAN` and `IN_AADHAAR` recognizers; enable/register and test them if present before writing replacements.
- [ ] Add only verified missing custom recognizers.
- [ ] Apply redaction to the Drive fixture before returning it to the MCP client.
- [ ] Preserve task-relevant expense amounts while redacting unnecessary identifiers.
- [ ] Ensure audit logs contain entity types/actions, not original sensitive values.
- [ ] Simulate DLP failure; raw response content must be withheld and only a sanitized error returned.

### Data lineage / taint

- [ ] Create `data_artifacts` and `artifact_taint` tables (or equivalent tables with the same information).
- [ ] Store stable artifact ID, owner principal, source server/tool, upstream object ID, classification, content hash, trusted demo workspace and timestamps.
- [ ] Add a server-assigned workspace to authenticated request context; do not accept it from model arguments.
- [ ] Register confidential classification/taint when the Drive artifact response is inspected.
- [ ] Make mock Gmail `send_email` accept `attachment_ids`.
- [ ] Resolve each attachment ID to its artifact and verify owner/workspace.
- [ ] Retrieve taint/classification before evaluating the send.
- [ ] Reject filename-only or unknown references as unclassified; do not assume `PUBLIC`.
- [ ] Include relevant artifact IDs and hashes in a pending approval payload.

**Exit gate:** Read the confidential file; the client sees a redacted response; the database records its confidential artifact identity; a later send referencing that artifact is recognized as sensitive.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T04, T05, T06, T16, T18
- Evidence:

## WP-5 — Exact-operation human approval

**Goal:** Pause before side effect, authenticate the decision-maker and execute only the frozen approved operation.

### Database fields required

- [ ] `user_id`, `invocation_id`, `server_id`, `upstream_tool_name`, `exposed_tool_name`.
- [ ] `encrypted_frozen_payload` and canonical `payload_hash`.
- [ ] `artifact_ids` and `artifact_hashes`.
- [ ] `status`, `expires_at`, `decided_by`, `decided_at`, `consumed_at`.
- [ ] `execution_status`, `executed_at` and upstream result/correlation metadata.

### Backend lifecycle

- [ ] When policy returns `REQUIRE_APPROVAL`, freeze the canonical arguments and relevant attachment identities/hashes before any upstream call.
- [ ] Encrypt the frozen payload at rest.
- [ ] Persist the approval in PostgreSQL.
- [ ] Return `approval_required`/pending reference to the calling client; never leave the upstream operation running while waiting.
- [ ] Implement authenticated list/detail/approve/reject endpoints.
- [ ] Enforce principal ownership on every approval route.
- [ ] Atomically transition approval state so concurrent consumers cannot both execute.
- [ ] Revalidate the exact payload hash, principal, expiry, tool review status, recipient and artifact hashes.
- [ ] Execute only the frozen stored payload.
- [ ] Record `SUCCEEDED`, `FAILED` or `UNKNOWN`; do not blindly retry ambiguous external side effects.
- [ ] Reject modified, expired, rejected, replayed and already-consumed approvals.
- [ ] Do not expose a model-callable approval tool.

### Minimal approval UI

- [ ] Build a single authenticated approval queue page.
- [ ] Show recipient, subject, attachment name/ID, classification, risk, policy reason and expiry.
- [ ] Show exact action details, not just a vague summary.
- [ ] Add approve and reject actions.
- [ ] Show result and execution state after the decision.

**Exit gate:** Rejection keeps Gmail send counter at zero; approval executes the exact frozen operation once; modified/replayed approval cannot execute.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T07, T08, T09, T10, T11, T12
- Evidence:

## WP-6 — Minimal audit/activity view

**Goal:** Make the security behavior verifiable in the demo.

- [ ] Persist events at request receipt, auth outcome, policy decision, DLP action, artifact/taint registration, approval creation/decision and upstream execution outcome.
- [ ] Include request/invocation ID, verified principal, both tool names, policy ID/version, decision, approval/execution states and timestamp.
- [ ] Sanitize event payloads before storing.
- [ ] Build a minimal activity timeline backed by PostgreSQL.
- [ ] Show upstream execution counter/result next to blocked/pending actions in demo mode.
- [ ] Ensure counts are derived from actual backend records/counters, never invented sample data.
- [ ] Add a simple audit evidence export or JSON view if time permits.

**Exit gate:** An observer can trace one request from authentication through DLP/policy/approval to upstream outcome.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T08, T09, T16
- Evidence:

## WP-7 — Scripted demo client, adversarial QA and freeze

**Goal:** A deterministic presentation that uses the actual running gateway and mock servers.

- [ ] Create a scripted MCP client that connects to Trust Gate using the demo bearer token.
- [ ] Do not rely on LLM behavior for the core attack path; optionally add an LLM interface as a secondary layer.
- [ ] Implement named scenarios: `NORMAL_SEARCH`, `READ_CONFIDENTIAL_FILE`, `PROMPT_INJECTION_EMAIL`, `REJECT_EXTERNAL_SEND`, `APPROVE_LEGITIMATE_SEND`, `DLP_FAILURE`.
- [ ] Verify the prompt-injection fixture is flagged and treated as untrusted; do not claim the detector alone stops exfiltration.
- [ ] Verify policy/taint controls stop the subsequent external send.
- [ ] Run all MVP-required tests and record evidence.
- [ ] Fix every critical/high finding or explicitly record why the demo must not proceed.
- [ ] Write a reset script that clears test approvals and restores mock counters/data.
- [ ] Pin dependencies and record the commit used in the demo.
- [ ] Rehearse with the network disabled if possible (mock-only core flow).
- [ ] Prepare a short screen recording or screenshots as a backup.

**Exit gate:** The full demo runs repeatedly from a clean reset and all displayed values come from the running system.

- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Owner:
- Test IDs: T01–T12, T16–T20
- Evidence:

---

# 5. MVP security test matrix

Use the same T01–T20 identifiers as the full product roadmap. `MVP gate` identifies tests that must pass for the demo. Integrity-monitoring tests T13–T15 can be treated as stretch only if the presentation does not claim those capabilities are implemented.

| ID | Scenario | Expected result | MVP gate | Implemented | Tested/pass | Audited | Evidence |
|---|---|---|---|---|---|---|---|
| T01 | Missing, invalid or expired northbound token | Rejected before tool handler | Required | [ ] | [ ] | [ ] | |
| T02 | Normal permitted Gmail search | Allowed through Trust Gate | Required | [ ] | [ ] | [ ] | |
| T03 | Unpermitted tool/operation | Blocked; upstream counter unchanged | Required | [ ] | [ ] | [ ] | |
| T04 | Sensitive Drive document returned | Policy-required fields redacted | Required | [ ] | [ ] | [ ] | |
| T05 | DLP/response inspection unavailable | Raw response withheld; sanitized error only | Required | [ ] | [ ] | [ ] | |
| T06 | Confidential artifact read then sent by stable ID | Taint/classification resolves in outbound path | Required | [ ] | [ ] | [ ] | |
| T07 | Tainted confidential artifact sent externally | `REQUIRE_APPROVAL`; no initial upstream send | Required | [ ] | [ ] | [ ] | |
| T08 | User rejects pending send | Rejected; send counter remains zero | Required | [ ] | [ ] | [ ] | |
| T09 | User approves exact frozen send | Exact payload executes once | Required | [ ] | [ ] | [ ] | |
| T10 | Recipient/attachment changed, expired or replayed approval | Rejected; no unintended execution | Required | [ ] | [ ] | [ ] | |
| T11 | Cross-user approval/artifact access | Denied | Required | [ ] | [ ] | [ ] | |
| T12 | Upstream result ambiguous after timeout | `UNKNOWN`/reconciliation; no blind retry | Required | [ ] | [ ] | [ ] | |
| T13 | Malicious first-registration tool description | Not exposed/executable until review | Stretch | [ ] | [ ] | [ ] | |
| T14 | Previously approved tool definition changes | Quarantined/review required | Stretch | [ ] | [ ] | [ ] | |
| T15 | Tool-list notification missed/unsupported | Reconciliation detects drift | Stretch | [ ] | [ ] | [ ] | |
| T16 | Tool output contains secrets/PII | Redacted and absent from logs | Required | [ ] | [ ] | [ ] | |
| T17 | Policy engine unavailable | Protected operation fails closed | Required | [ ] | [ ] | [ ] | |
| T18 | DLP unavailable | Response withheld and protected write blocked | Required | [ ] | [ ] | [ ] | |
| T19 | Malicious email instructions | Flagged/untrusted; cannot alter policy/authorize follow-on call | Required | [ ] | [ ] | [ ] | |
| T20 | Direct upstream bypass | Protected client configuration routes through Trust Gate only | Required | [ ] | [ ] | [ ] | |

### Test evidence record template

```md
### Test TXX — [scenario]
- Date/time:
- Commit:
- Environment:
- Fixture:
- Expected:
- Actual:
- Result: PASS / FAIL / BLOCKED
- Upstream counter before/after:
- Sanitized logs / screenshot:
- Reviewer:
- Related issue:
```

---

# 6. Live demo runbook (5–7 minutes)

## Pre-demo setup

- [ ] Start PostgreSQL, mock Gmail, mock Drive, backend and frontend.
- [ ] Run migrations and seed the single demo principal/tool allowlist/policies.
- [ ] Load synthetic email and document fixtures.
- [ ] Reset send counter to zero and clear old approvals/audit events.
- [ ] Verify the bearer token works and a missing token is rejected.
- [ ] Open the approval page and activity timeline.
- [ ] Start the scripted demo client and verify it connects to Trust Gate, not directly to mocks.

## Scenario 1 — ordinary operation (30–45 seconds)

Prompt/action: “Find my latest train ticket confirmation.”

Show: authenticated tool request → `ALLOW` → mock Gmail search counter increments → sanitized result → audit event.

## Scenario 2 — sensitive read and DLP (45–60 seconds)

Prompt/action: “Read the financial statement and summarize expenses.”

Show: original synthetic document held in mock Drive → Presidio detection → PAN/Aadhaar/phone/account fields redacted → expense amount retained → artifact ID, `CONFIDENTIAL` classification and taint record persisted.

## Scenario 3 — malicious instruction (45–60 seconds)

Open/read the malicious email containing instructions to send the financial document externally.

Show: content inspection flags suspicious instructions and marks the content untrusted. Explain that detection is a signal, not the final security boundary.

## Scenario 4 — exfiltration attempt and rejection (60–90 seconds)

Action: attempt `gmail_send_email` using the stable confidential `artifact_id` and an external recipient.

Show: Trust Gate resolves taint → policy returns `REQUIRE_APPROVAL` → pending approval card appears → Gmail send counter remains zero → user rejects → counter remains zero.

## Scenario 5 — exact legitimate approval (60–90 seconds)

Action: run a separate approved test operation with a verified demo recipient.

Show: exact recipient/attachment/payload → user approves → frozen hash revalidated → one upstream send → success audit event. Do not reuse the rejected approval by mutating it.

## Closing proof points

- [ ] Trust Gate was in the actual execution path.
- [ ] The user identity was derived from authentication, not model input.
- [ ] Sensitive response data was redacted before reaching the model/client.
- [ ] Artifact lineage informed the outbound decision.
- [ ] The unauthorized send was not executed before approval.
- [ ] Approval was tied to the exact payload and used once.
- [ ] The audit timeline reflects real backend events.

---

# 7. Final release gate and handoff

- [ ] All mandatory MVP acceptance criteria pass.
- [ ] Required tests T01–T12 and T16–T20 pass with evidence.
- [ ] No unresolved critical security finding remains.
- [ ] Any unimplemented stretch feature is not claimed in the presentation.
- [ ] No real secrets, tokens or personal data are committed.
- [ ] All synthetic data is clearly marked as synthetic.
- [ ] A clean reset and startup procedure works.
- [ ] Demo uses the same commit/build that was tested.
- [ ] The team has rehearsed the full demo and the backup recording is ready.
- [ ] Update the full-product roadmap with deferred tasks and lessons learned.

## 7.1 Milestone and evidence log

| Time / date | Work package | Commit / PR | Implemented by | Tested by | Audited by | Evidence / issues |
|---|---|---|---|---|---|---|
| | WP-0 foundation | | | | | |
| | WP-1 identity + mocks | | | | | |
| | WP-2 gateway | | | | | |
| | WP-3 policy | | | | | |
| | WP-4 DLP + taint | | | | | |
| | WP-5 approval | | | | | |
| | WP-6 audit UI | | | | | |
| | WP-7 demo + QA | | | | | |

## 7.2 Open findings

| ID | Finding | Severity | Owner | Status | Fix / evidence |
|---|---|---|---|---|---|
| SEC-001 | | | | Open | |
| SEC-002 | | | | Open | |
| SEC-003 | | | | Open | |

---

# 8. Post-hackathon handoff

Move deferred work into the full product roadmap rather than expanding the hackathon tracker during the event.

- [ ] Complete first-registration metadata scanning and reviewer workflow if not in MVP.
- [ ] Complete schema fingerprinting, supported list-change notifications and reconciliation.
- [ ] Replace the static demo token with production OAuth 2.1/resource-server integration.
- [ ] Add real Gmail/Drive integrations and server-specific credential management.
- [ ] Expand dashboard pages for servers, tools, policies, threat findings and artifact lineage.
- [ ] Add append-only/tamper-evident audit hardening.
- [ ] Add KMS/Vault-backed key management and credential rotation.
- [ ] Evaluate Redis/background jobs only when justified by measured load.
- [ ] Add broader integration, authorization and adversarial test coverage.
- [ ] Review threat model and update product claims against verified capabilities.

---

# 9. Development references

- [Official MCP specification](https://modelcontextprotocol.io/specification)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Python SDK — low-level Server](https://py.sdk.modelcontextprotocol.io/v2/advanced/low-level-server/)
- [MCP Python SDK — authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/)
- [MCP Python SDK — context and tool-list updates](https://py.sdk.modelcontextprotocol.io/handlers/context/)
- [MCP server tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)
- [Microsoft Presidio supported entities](https://github.com/microsoft/presidio/blob/main/docs/supported_entities.md)
- [Microsoft Presidio documentation](https://microsoft.github.io/presidio/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Docker Compose documentation](https://docs.docker.com/compose/)

---

**Implementation rule:** Prove the authenticated gateway and block counter first. Then prove response withholding and artifact taint. Then prove exact-operation approval. Everything else is secondary to these security properties.
