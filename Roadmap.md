# AegisMCP — Full Product Roadmap & Corrected Architecture

> **Project:** AegisMCP — MCP Security Gateway and AI Agent Governance Platform  
> **Purpose:** The canonical long-term product backlog and architecture reference for building, testing, auditing, deploying, and evolving AegisMCP. Use the companion `AegisMCP_Hackathon_MVP_Tracker.md` for the deliberately smaller hackathon scope.  
> **Project objective:** Place an independently enforced security gateway between AI applications and their connected MCP servers. Inspect tool calls and responses, enforce permissions, protect sensitive information, and require human approval for high-risk operations.

---

## How to use this file

This is the full-product backlog, not the hackathon sprint board. Preserve its broad scope for post-hackathon development. Update the checkboxes as work progresses and commit changes regularly. During the hackathon, work only from the companion `AegisMCP_Hackathon_MVP_Tracker.md`; do not try to complete this entire backlog in the event.

### Status legend

For each deliverable, use the three independent status checkboxes:

- **Implemented** — the feature exists in the codebase and is connected to the application.
- **Tested** — the feature has passed the relevant unit, integration, end-to-end, or adversarial tests. Record test IDs and evidence.
- **Audited** — the implementation has been reviewed for security, authorization, failure handling, and unintended bypasses. Record reviewer and findings.

A feature is not complete merely because it has been coded. Do not mark **Tested** or **Audited** without evidence. The single checkboxes throughout this long-form backlog are task completion markers; use the three-status milestone tables and the status template for work packages requiring formal implementation, test, and security-review sign-off.

### Status template

Copy this template for new work items:

```md
- [ ] Implemented
- [ ] Tested
- [ ] Audited
- Evidence / PR / test run:
- Owner:
- Notes:
```

### Project-wide rules

- [ ] Every protected MCP tool invocation passes through one centralized security execution pipeline.
- [ ] Every tool response is inspected before it is returned to the AI host.
- [ ] No protected integration is connected directly to the AI host in a way that bypasses AegisMCP.
- [ ] The policy engine, not the LLM, makes the final authorization decision.
- [ ] Every model-facing tool response is inspected before forwarding; if mandatory response inspection is unavailable, withhold the response content and return only a sanitized error.
- [ ] Sensitive reads and writes fail closed when their mandatory security controls are unavailable.
- [ ] Every MCP request is tied to a principal derived from verified transport authentication; never trust a model-supplied `user_id`.
- [ ] Outbound writes resolve attachment/document references and evaluate their classification and provenance before policy authorization.
- [ ] Human approval is bound to the exact principal, server, tool, destination, arguments, artifact identities, and content hashes.
- [ ] Raw secrets and unnecessary personal information are not written to logs.
- [ ] All demonstration data is synthetic unless a specifically approved, controlled test account is being used.

---

> **Documentation governance:** This file is the full product roadmap and corrected architecture reference. Keep `README.md` short and setup-oriented. The architecture should live in `docs/ARCHITECTURE.md` in the project repository; treat the design in Section 2 and the database/API sections here as the approved starting baseline, and keep detailed architecture decisions synchronized through ADRs. The companion hackathon tracker is a time-boxed execution subset, not a second architecture specification.

# 1. Project Definition and Scope

## 1.1 Product definition

**AegisMCP** is an MCP-aware broker with two interfaces:

- **Northbound:** Exposes a protected MCP interface to AI applications and MCP-compatible hosts.
- **Southbound:** Maintains individual MCP client connections to approved upstream MCP servers.

AegisMCP understands MCP tool discovery, schemas, invocation, and responses. It is not intended to be only a generic HTTP proxy that inspects raw JSON-RPC traffic.

### Core security principle

> Every protected MCP tool call must pass through an independently enforced security decision before execution, and every tool response must pass through an inspection and data-protection pipeline before reaching the AI.

## 1.2 Primary problem

AI agents can access connected services and perform operations on a user's behalf. This introduces risks including:

- Malicious instructions embedded in emails, documents, or other external content.
- Unnecessary exposure of personal, confidential, or restricted information.
- Unauthorized or unintended tool execution.
- Excessive permissions granted to agents or integrations.
- Changes to advertised MCP tool definitions after they have been reviewed.
- Inadequate visibility into what an agent attempted, what was permitted, and what actually executed.

## 1.3 Product outcome

AegisMCP should provide:

- Centralized MCP tool routing.
- Tool and parameter inspection.
- Deterministic policy enforcement.
- Sensitive-data detection and redaction.
- Suspicious-content and tool-integrity monitoring.
- Human approval for designated high-risk actions.
- Sanitized, traceable audit records.
- A dashboard for managing integrations, policies, approvals, threats, and audit history.

## 1.4 MVP scope

### Must-have for the hackathon MVP

- [ ] Authenticated northbound MCP endpoint and principal derived from verified auth context.
- [ ] Working downstream Aegis MCP server and upstream MCP clients.
- [ ] At least two controlled mock upstream integrations, initially Gmail and Drive.
- [ ] Approved tool discovery, namespaced registry and routing.
- [ ] Centralized policy evaluation with `ALLOW`, `REQUIRE_APPROVAL`, and `BLOCK` outcomes.
- [ ] Proof that blocked operations never reach the upstream server.
- [ ] Response DLP and policy-based redaction before any model-facing response is forwarded.
- [ ] Response content withheld if mandatory inspection is unavailable.
- [ ] Stable artifact identity, provenance, classification and outbound taint lookup.
- [ ] Human approval and rejection workflow for one exact high-risk send operation.
- [ ] Approval bound to authenticated principal, frozen arguments, destination, artifact IDs and content hashes.
- [ ] Minimal authenticated approval UI and persisted audit/activity view.
- [ ] Repeatable scripted MCP demonstration scenarios.

### Should-have for the MVP

- [ ] Prompt-injection inspection and untrusted-content marking.
- [ ] Tool schema fingerprinting and quarantine on change.
- [ ] Live dashboard updates.
- [ ] Server health monitoring.
- [ ] Mobile-friendly approval page; external Web Push notifications are a later enhancement.

### Defer until after the MVP

- [ ] Advanced ML-based anomaly detection.
- [ ] Enterprise-scale policy administration.
- [ ] Multiple identity providers.
- [ ] Complex multi-user delegation.
- [ ] SIEM integration.
- [ ] Large-scale distributed microservices.
- [ ] Kubernetes deployment.
- [ ] Broad integrations beyond the initial controlled connectors.

## 1.5 Operating modes

- [ ] **Gateway mode (primary):** External AI application connects to AegisMCP as its MCP server; AegisMCP connects to approved upstream servers.
- [ ] **Managed-host mode (future):** AegisMCP provides its own AI interface and manages all MCP clients.

**Scope decision:** Build gateway mode first. Managed-host mode is not required for the first MVP.

---

# 2. Corrected Architecture and End-to-End Workflows

## 2.1 High-level architecture

```text
                 AI APPLICATION / MCP HOST
                           |
             Authorization: Bearer <access-token>
                           |
                           v
              NORTHBOUND AUTHENTICATION
             Verify token, audience/resource,
             expiry, scopes and authenticated subject
                           |
                           v
+------------------------------------------------------------------+
|                         AEGISMCP GATEWAY                         |
|                                                                  |
|  Authenticated principal + trusted execution workspace           |
|                           |                                      |
|                           v                                      |
|  Dynamic tool inventory / approved definition registry           |
|                           |                                      |
|                           v                                      |
|  Request + schema + argument inspection                          |
|                           |                                      |
|                           v                                      |
|  Outbound content resolution + artifact lineage / taint lookup   |
|                           |                                      |
|                           v                                      |
|  Threat signals + deterministic policy engine                   |
|                 /              |                \                |
|              ALLOW       REQUIRE_APPROVAL       BLOCK            |
|                |              |                  |              |
|                |       Frozen exact action       |              |
|                |       Authenticated review      |              |
|                |       One-time execution        |              |
|                +--------------+------------------+              |
|                               |                                  |
|                   Controlled upstream execution                 |
|                               |                                  |
|                               v                                  |
|                  Upstream MCP client manager                     |
|                               |                                  |
|                               v                                  |
|                 Gmail / Drive / other MCP servers                |
|                               |                                  |
|                               v                                  |
|               Response inspection + DLP + redaction             |
|                               |                                  |
|                 +-------------+-------------+                    |
|                 |                           |                    |
|          Register classified          Withhold content           |
|          artifact lineage / taint     if inspection fails        |
|                 |                           |                    |
|                 +-------------+-------------+                    |
|                               |                                  |
|                    Sanitized model-facing result                 |
|                                                                  |
|  Audit events emitted at request, decision and execution stages  |
+------------------------------------------------------------------+
                           |
                  PostgreSQL source of truth
       Users / tokens / tool registry / artifacts / taint /
       invocations / policies / approvals / audit / findings
```

**Deployment constraint:** Every protected integration must be routed through AegisMCP. An MCP server connected separately and directly to the AI host can bypass the gateway. AegisMCP cannot claim to protect connections it does not control.

## 2.2 Authentication and northbound identity

The policy engine must never accept a caller-supplied or model-generated `user_id` as proof of identity. The user principal is derived from transport authentication before the MCP request reaches a tool handler.

### Hackathon implementation

- [ ] Use Streamable HTTP for the northbound MCP endpoint so an HTTP authentication boundary exists.
- [ ] Use a development-only bearer token supplied through an environment variable or seeded credential record.
- [ ] Verify the token in HTTP middleware or the pinned MCP SDK's token-verifier integration.
- [ ] Map the verified token to one seeded demo principal, such as `demo-user`.
- [ ] Inject the authenticated principal into trusted request context; do not expose `user_id` as a tool argument.
- [ ] Use a server-assigned demo workspace/execution context for artifact tracking.
- [ ] Require the dashboard approval routes to authenticate as the same principal.
- [ ] Keep the demo token out of source control, browser bundles, prompts, tool results, screenshots and logs.

This static-token arrangement is only a controlled MVP authentication mechanism. It is not production OAuth and must not be described as such.

### Product implementation

- [ ] Integrate an OAuth 2.1-compatible authorization server/identity provider.
- [ ] Validate token signature or introspection result, issuer, expiry, audience/resource and required scopes.
- [ ] Derive principal identity from the verified token subject and trusted claims.
- [ ] Enforce server ownership and per-tool permissions for every request.
- [ ] Ensure the dashboard and MCP gateway use a consistent principal/tenant model.
- [ ] Define token revocation, key rotation, session expiry and identity-provider outage behavior.
- [ ] Treat `client_id` and `subject` as different identities; use the authenticated user/subject for user ownership and the client identity for client-level restrictions.

For HTTP MCP servers, the official Python SDK describes the server as an OAuth 2.1 resource server: it verifies tokens issued by an authorization server and exposes the authenticated caller to handlers. Pin the SDK version and follow its matching authorization documentation.

## 2.3 Canonical identity and tool naming

Use two names for each dynamically discovered tool, and never confuse them:

| Field | Example | Purpose |
|---|---|---|
| `server_id` | `gmail-prod` | Stable upstream server identity |
| `upstream_tool_name` | `send_email` | Exact name advertised by the upstream server |
| `exposed_tool_name` | `gmail_send_email` | Namespaced name presented by AegisMCP to the AI host |

The canonical policy and registry key is `(server_id, upstream_tool_name)`. The namespaced `exposed_tool_name` is the public tool identifier at the northbound boundary. Persist both, and include both in audit events.

Policy decisions use exactly these values:

- `ALLOW` — operation may proceed after mandatory checks.
- `REQUIRE_APPROVAL` — stop before upstream execution and create a pending approval.
- `BLOCK` — reject; do not execute upstream.

Approval lifecycle status and execution status are separate state machines; they are not policy decisions.

## 2.4 Data lineage and outbound taint tracking

Response-only DLP is insufficient. AegisMCP must remember which retrieved artifacts were classified as sensitive so it can evaluate later outbound operations that reference those artifacts.

### Artifact and taint model

- [ ] Give each retrieved document/attachment a stable `artifact_id` independent of its filename.
- [ ] Record its authenticated `user_id`, server, upstream object ID, source tool, classification, classification evidence, content hash when available, and timestamps.
- [ ] Associate the artifact with a trusted execution workspace/context. Do not accept an unverified context ID supplied in model-controlled tool arguments.
- [ ] In the MVP, use one server-assigned workspace per authenticated demo principal. This is deliberately conservative and avoids pretending the MCP session identifier is a trustworthy agent-run identity.
- [ ] In the full product, support narrower execution-context taint where the host provides a trustworthy context binding; otherwise apply the conservative principal/workspace scope.
- [ ] Maintain artifact-to-context taint associations in PostgreSQL.
- [ ] Resolve outbound attachment/document IDs against the artifact registry or upstream connector before evaluating a write.
- [ ] Do not infer sensitivity from a filename alone.
- [ ] Re-fetch or verify attachment identity/content hash immediately before a delayed approved execution when the connector permits it.
- [ ] If an external attachment cannot be resolved or inspected, do not silently classify it as `PUBLIC`; block or require a defined high-risk review policy.

### Outbound example

1. The AI reads `drive_file_001` through AegisMCP.
2. Response DLP classifies the document as `CONFIDENTIAL` and stores its stable artifact identity and content hash.
3. AegisMCP records that `drive_file_001` is tainted in the demo principal's trusted workspace.
4. A later `gmail_send_email` invocation references `drive_file_001` in `attachment_ids`.
5. Aegis resolves the ID, retrieves the classification/taint record, checks the recipient and evaluates policy.
6. External transmission of the confidential artifact returns `REQUIRE_APPROVAL` before Gmail is called.

If an agent tries to send an artifact it has not previously read, the gateway must still resolve and inspect it through trusted upstream metadata/content where possible. If it cannot establish the artifact's classification, it must not assume the artifact is safe.

## 2.5 Centralized tool execution pipeline

Every protected `tools/call` must pass through one service. No connector or alternate handler may call an upstream server directly.

1. Authenticate the request and derive the principal from verified transport context.
2. Resolve `server_id`, `upstream_tool_name`, and `exposed_tool_name` from the approved tool registry.
3. Validate the current tool status and compare its definition with the approved definition/fingerprint.
4. Validate tool arguments against the canonical upstream schema.
5. Inspect arguments and resolve outbound attachment/document references.
6. Look up artifact classification and taint for all outbound content; inspect supplied content where supported.
7. Run threat/content checks and collect findings as policy inputs, not as authorization decisions.
8. Evaluate deterministic policy: `ALLOW`, `REQUIRE_APPROVAL`, or `BLOCK`.
9. If `BLOCK`, do not call upstream. If `REQUIRE_APPROVAL`, freeze and persist the exact operation without executing it. If `ALLOW`, proceed only after mandatory pre-execution checks pass.
10. Execute the upstream operation using the server-specific client and credential.
11. Inspect every model-facing tool response, apply DLP and policy-based redaction, and register classified artifacts/taint before forwarding.
12. If mandatory response inspection is unavailable or fails, withhold the response content and return only a sanitized inspection-unavailable error.
13. Emit sanitized audit events throughout the lifecycle, including failures and blocked attempts.

## 2.6 Read and response workflow

Example: “Read my bank statement and summarize my expenses.”

- [ ] Authenticate the caller and derive the user principal.
- [ ] Check the user can access the requested server and tool.
- [ ] Validate the current approved tool definition and arguments.
- [ ] Evaluate read permission before upstream execution.
- [ ] Retrieve the source document through the correct upstream client.
- [ ] Run response content extraction, DLP detection, classification and task-aware redaction.
- [ ] Record artifact identity, provenance, classification and available content hash.
- [ ] Record the artifact's taint in the trusted principal/workspace context.
- [ ] Return only the sanitized, policy-permitted content to the AI host.
- [ ] If response inspection is unavailable, withhold the raw result; never forward uninspected content.
- [ ] Record a sanitized audit event without storing the full confidential document.

## 2.7 High-risk outbound workflow

Example: “Send my bank statement to this external address.”

- [ ] Intercept the outbound tool invocation before any side effect.
- [ ] Authenticate the caller and verify server/tool permissions.
- [ ] Resolve all attachment IDs to stable artifact records and content identities.
- [ ] Retrieve classification and taint information; inspect content when needed and supported.
- [ ] Determine whether the destination is external/allowed and whether the operation is high-risk.
- [ ] Return `REQUIRE_APPROVAL` without calling the upstream server.
- [ ] Freeze the canonical tool identity, recipient, subject/body, attachment IDs, attachment hashes, relevant headers and all execution arguments.
- [ ] Persist the frozen payload encrypted at rest, its canonical hash, user, expiry and state.
- [ ] Present the exact action in an authenticated approval UI.
- [ ] On approval, atomically consume the approval, revalidate the tool definition, policy, recipient, artifact identity and content hashes, then execute only the stored frozen payload.
- [ ] On rejection, expiry, modification, replay, authentication failure or unavailable approval service, never execute upstream.
- [ ] Record the actual execution outcome. If the external result is ambiguous, use `UNKNOWN`/reconciliation rather than blindly retrying.

---

# 3. Technology Stack and Engineering Decisions

## 3.1 Recommended product stack

| Layer | Technology | Responsibility | MVP decision |
|---|---|---|---|
| Frontend | React + TypeScript | Approval page and administration dashboard | Minimal approval queue first |
| Styling | Tailwind CSS | UI styling | Use existing team capability |
| Backend | Python + FastAPI | REST APIs, auth boundary and application services | Required |
| MCP | Official MCP Python SDK | Downstream server and upstream clients | Pin exact version |
| Dynamic gateway server | SDK low-level `Server` API prototype | Runtime tool listing and centralized dispatch | Recommended technical spike |
| Transport | Streamable HTTP for remote northbound gateway; stdio where appropriate for local connectors | MCP communication | Test exact host/client |
| Database | PostgreSQL | Durable users, tools, artifacts, taint, approvals, invocations and audit | Required |
| ORM/migrations | SQLAlchemy + Alembic | Models and migrations | Recommended |
| DLP | Microsoft Presidio + custom rules only where needed | PII detection and anonymization | Required for text fixtures |
| Cache/jobs | Redis | Optional transient state, caching and background jobs | Deferred; PostgreSQL is sufficient for MVP |
| Notifications | Dashboard polling/SSE/WebSocket | Approval status and activity updates | Dashboard only; no Web Push |
| Authentication | Development bearer-token verifier for MVP; OAuth 2.1 resource-server integration for product | Northbound identity and dashboard access | Authenticated MVP token required |
| Secret management | Environment-based demo secret; production KMS/Vault or equivalent | Credential/token protection | No production credentials in MVP |
| Containers | Docker + Docker Compose | Repeatable local/demo deployment | Required if time permits |
| Tests | Pytest + MCP integration client | Unit/integration/security testing | Required |

## 3.2 Version and compatibility decisions

- [ ] Select and pin the MCP Python SDK version before implementing the gateway.
- [ ] Record the MCP protocol version(s) supported by the pinned SDK.
- [ ] Select the first target MCP host/client and record its version.
- [ ] Test the selected transport and authentication method with that exact host/client.
- [ ] Prototype the SDK low-level `Server` API for dynamically generated tool definitions and one centralized `on_call_tool` dispatcher.
- [ ] Keep the high-level server API as an alternative if the prototype demonstrates that the dynamic registry requirements can be met cleanly.
- [ ] Record client-specific limitations for tool-list changes, authentication and transport behavior.
- [ ] Pin Python, Node.js, frontend, backend and database dependencies.
- [ ] Add dependency lockfiles and a repeatable setup command.
- [ ] Re-test protocol/SDK upgrades before adoption.

The SDK and MCP specification evolve. Do not copy API names or protocol assumptions from an unpinned tutorial. Consult documentation matching the exact SDK version selected by the project.

## 3.3 Architecture decisions to record

- [ ] Use a modular monolith for the initial product; do not introduce microservices prematurely.
- [ ] Use gateway mode as the primary operating mode.
- [ ] Derive the user principal from verified transport authentication, never from an AI-supplied `user_id` argument.
- [ ] Keep canonical tool identity as `(server_id, upstream_tool_name)` and separately store the namespaced `exposed_tool_name`.
- [ ] Use `ALLOW`, `REQUIRE_APPROVAL`, and `BLOCK` as the only policy decisions.
- [ ] Keep approval state and execution state separate from the policy decision.
- [ ] Make backend policy, not the LLM, the final authorization authority.
- [ ] Route every invocation through one centralized execution service.
- [ ] Inspect every model-facing tool response before forwarding it.
- [ ] Withhold response content if mandatory inspection is unavailable; return only a sanitized error.
- [ ] Track document/artifact lineage and taint to make outbound decisions data-aware.
- [ ] Bind any approval to the exact frozen operation and verified user principal.
- [ ] Use PostgreSQL as the durable source of truth for approvals, artifact metadata, taint and audit records.
- [ ] Defer Redis until a measured need exists.
- [ ] Isolate credentials per user and upstream server.
- [ ] Emit audit events from the first gateway milestone, not only when the dashboard is built.
- [ ] Keep mock MCP servers as permanent regression fixtures after real integrations are added.

---

# 4. Repository and Development Environment Setup

## 4.1 Proposed repository structure

```text
aegismcp/
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── tests/
│
├── backend/
│   ├── gateway/
│   ├── security/
│   ├── policy/
│   ├── approvals/
│   ├── identity/
│   ├── data_lineage/
│   ├── connectors/
│   ├── credentials/
│   ├── audit/
│   ├── api/
│   ├── database/
│   └── tests/
│
├── mock_servers/
│   ├── gmail_mock/
│   ├── drive_mock/
│   └── malicious_mock/
│
├── infrastructure/
│   ├── docker/
│   ├── scripts/
│   └── deployment/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY_DESIGN.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_SPECIFICATION.md
│   ├── THREAT_MODEL.md
│   └── DEMO_GUIDE.md
├── planning/
│   ├── COMPLETE_ROADMAP.md
│   └── HACKATHON_MVP_TRACKER.md
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── README.md
└── AegisMCP_Complete_Development_Roadmap.md
```

## 4.2 Foundation checklist

### Repository and project management

- [ ] Create Git repository.
- [ ] Add `main` branch protection or an equivalent review rule.
- [ ] Define branch naming and pull-request conventions.
- [ ] Add `.gitignore` for Python, Node, IDE, build, and local environment files.
- [ ] Add `.env.example` with variable names only and safe example placeholders.
- [ ] Confirm no real credentials or sensitive test data are committed.
- [ ] Keep `README.md` short and setup-oriented; put the architecture in `docs/ARCHITECTURE.md` and keep this full backlog in `planning/COMPLETE_ROADMAP.md`.
- [ ] Add issue labels for `backend`, `frontend`, `security`, `testing`, `documentation`, and `blocked`.
- [ ] Establish owners for the gateway, security, frontend, and integration workstreams.

### Local environment

- [ ] Install the supported Python version.
- [ ] Install the supported Node.js version and package manager.
- [ ] Install Docker and Docker Compose.
- [ ] Create Python virtual environment and dependency manager configuration.
- [ ] Initialize React + TypeScript frontend.
- [ ] Initialize FastAPI backend.
- [ ] Configure linting and formatting for Python.
- [ ] Configure linting and formatting for TypeScript.
- [ ] Configure type checking.
- [ ] Configure test commands.
- [ ] Verify frontend and backend start locally.
- [ ] Verify PostgreSQL container starts and accepts connections.
- [ ] Add a simple health endpoint.
- [ ] Document a clean-machine setup procedure.

### Foundation quality gate

- [ ] A new developer can clone the repository and follow the setup guide.
- [ ] The frontend starts successfully.
- [ ] The backend starts successfully.
- [ ] Database connectivity succeeds.
- [ ] Automated tests can be run with one documented command.
- [ ] No secrets are required to run the mock-only development setup.

---

# 5. Database Architecture and Data Models

PostgreSQL is the only required database for the MVP and the durable source of truth for the product. Do not introduce Redis until a measured need for transient coordination, caching or background jobs exists. Approval authorization must never depend on Redis.

## 5.1 Canonical tables

| Table | Important fields | Purpose |
|---|---|---|
| `users` | `id`, `email`, `status`, `created_at` | Principal ownership |
| `api_clients` / `access_tokens` | `id`, `user_id`, `token_hash`, `scopes`, `expires_at`, `revoked_at` | MVP/client token records where applicable; never store raw bearer tokens |
| `mcp_servers` | `id`, `user_id`, `name`, `endpoint`, `transport`, `status` | Registered upstream servers |
| `server_credentials` | `id`, `server_id`, `user_id`, `encrypted_secret`, `scopes`, `key_version` | Isolated upstream credentials |
| `tool_registry` | `id`, `server_id`, `upstream_tool_name`, `exposed_tool_name`, `approved_definition_json`, `current_definition_json`, `approved_schema_hash`, `current_schema_hash`, `review_status`, `version`, `reviewed_by`, `reviewed_at` | Full reviewed definitions and fingerprints; permits before/after diff |
| `security_policies` | `id`, `user_id`/`tenant_id`, `rule`, `decision`, `version`, `enabled` | Deterministic policy configuration |
| `tool_invocations` | `id`, `user_id`, `client_id`, `execution_context_id`, `server_id`, `upstream_tool_name`, `exposed_tool_name`, `arguments_hash`, `decision`, `policy_id`, `policy_version`, `execution_status`, timestamps | Identity-bound invocation and outcome record |
| `data_artifacts` | `id`, `user_id`, `execution_context_id`, `server_id`, `upstream_object_id`, `source_tool`, `classification`, `content_hash`, `metadata_json`, timestamps | Stable source artifact registry |
| `artifact_taint` | `id`, `artifact_id`, `user_id`, `execution_context_id`, `classification`, `source_invocation_id`, `expires_at` | Provenance/taint association for later outbound checks |
| `data_classifications` | `id`, `invocation_id`, `artifact_id`, `entity_type`, `classification`, `confidence`, `action` | DLP findings without raw sensitive values |
| `threat_events` | `id`, `invocation_id`, `server_id`, `tool_name`, `threat_type`, `severity`, `sanitized_evidence` | Threat findings |
| `approval_requests` | `id`, `user_id`, `invocation_id`, `server_id`, `upstream_tool_name`, `exposed_tool_name`, `encrypted_frozen_payload`, `payload_hash`, `artifact_hashes_json`, `status`, `expires_at`, `decided_by`, `decided_at`, `consumed_at`, `execution_status`, `executed_at` | Exact-operation approval and controlled execution |
| `approval_decisions` | `id`, `approval_id`, `user_id`, `decision`, `timestamp`, `decision_metadata` | Immutable human decision record |
| `audit_events` | `id`, `user_id`, `invocation_id`, `event_type`, `sanitized_payload`, `previous_hash`, `event_hash`, `created_at` | Durable security timeline |

Names in this table are logical schema names. Define exact SQLAlchemy types, indexes, constraints and JSON representation in `docs/DATABASE_SCHEMA.md` before migrations.

## 5.2 State vocabulary

**Policy decision:** `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`.

**Approval status:** `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, `CONSUMED`, `CANCELLED`.

**Execution status:** `NOT_STARTED`, `EXECUTING`, `SUCCEEDED`, `FAILED`, `UNKNOWN`, `RECONCILIATION_REQUIRED`.

**Tool review status:** `PENDING_REVIEW`, `APPROVED`, `REVIEW_REQUIRED`, `QUARANTINED`, `REJECTED`, `DISABLED`.

**Data classification:** `PUBLIC`, `INTERNAL`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED`.

Do not use one status column to represent policy outcome, human approval, and external execution outcome.

## 5.3 Approval integrity constraints

- [ ] Store the frozen canonical operation payload encrypted at rest or store a durable encrypted reference to it.
- [ ] Store a cryptographic hash of the canonical payload and relevant attachment content hashes.
- [ ] Include the verified `user_id`, invocation, server and upstream tool identity.
- [ ] Use a conditional atomic state transition so only one worker can move an eligible approval into execution.
- [ ] Enforce one-time consumption with `consumed_at` and a unique invocation/approval execution constraint as appropriate.
- [ ] Execute the frozen database payload, never re-use mutable arguments supplied by the AI after approval.
- [ ] Record ambiguous upstream outcomes as `UNKNOWN` or `RECONCILIATION_REQUIRED`; do not blindly retry a potentially completed side effect.

## 5.4 Database implementation checklist

- [ ] Define UUID-based primary keys where appropriate.
- [ ] Define foreign keys and ownership relationships.
- [ ] Add user/tenant ownership constraints and indexes.
- [ ] Add uniqueness constraints for server/tool identities and one-time approval consumption.
- [ ] Create SQLAlchemy models and Alembic migrations.
- [ ] Verify migrations against an empty database and a prior schema version.
- [ ] Store full approved and current tool definitions, not only hashes.
- [ ] Persist invocation identity, decision, policy ID/version and execution status.
- [ ] Persist encrypted frozen approval payloads, hashes, user ownership and consumption/execution timestamps.
- [ ] Persist artifact identity, classification, content hash and taint provenance.
- [ ] Keep audit payloads sanitized and minimize sensitive retention.
- [ ] Define retention/deletion behavior for tokens, artifacts, approvals and audit records.
- [ ] Add database backup and restore instructions.

### Database quality gate

- [ ] A user cannot retrieve another user's servers, credentials, artifacts, approvals or audit events.
- [ ] An approved operation can be reconstructed only from its encrypted frozen payload/reference.
- [ ] Concurrent approval consumers cannot execute the same approval twice.
- [ ] Tool-definition diffs can be generated from stored snapshots.
- [ ] Artifact lineage can be resolved during a later outbound operation.
- [ ] Audit data contains sanitized evidence only.

---

# 6. Build Controlled Mock MCP Servers

**Purpose:** Build and test the security pipeline without depending on real Google accounts or external services. Keep these mock servers as permanent test fixtures.

## 6.1 Mock Gmail MCP server

Initial tools:

- `search_emails`
- `read_email`
- `send_email`

Checklist:

- [ ] Create mock Gmail MCP server using the official SDK.
- [ ] Create synthetic email dataset.
- [ ] Implement email search.
- [ ] Implement email retrieval.
- [ ] Implement controlled email sending.
- [ ] Store sent-email records in mock state or database.
- [ ] Add a send counter so tests can prove a blocked operation was not executed.
- [ ] Add fixtures for ordinary emails.
- [ ] Add a fixture containing synthetic sensitive information.
- [ ] Add a malicious prompt-injection email fixture.
- [ ] Add failure simulation for unavailable upstream service.
- [ ] Add tests for each mock tool.

## 6.2 Mock Drive MCP server

Initial tools:

- `search_files`
- `read_file`
- Optional later: `share_file`, `delete_file`

Checklist:

- [ ] Create mock Drive MCP server using the official SDK.
- [ ] Create synthetic document dataset.
- [ ] Implement file search.
- [ ] Implement document retrieval.
- [ ] Add a synthetic financial statement.
- [ ] Add documents containing email, phone, PAN-like, Aadhaar-like, bank-account-like, and secret-like test values.
- [ ] Add a mock external-sharing tool only when the approval workflow is ready.
- [ ] Add an execution counter for write operations.
- [ ] Add upstream failure simulation.
- [ ] Add tests for each mock tool.

## 6.3 Malicious MCP server

Checklist:

- [ ] Create a separate malicious test MCP server.
- [ ] Add a tool with a suspicious or poisoned description.
- [ ] Add a mode that changes a tool schema after initial approval.
- [ ] Add a tool result containing untrusted instructions.
- [ ] Add unexpected or malformed arguments/results for validation testing.
- [ ] Keep this environment isolated from real accounts and real external side effects.
- [ ] Document how to start and reset all mock servers.

### Mock-server quality gate

- [ ] Mock servers run locally and in the test environment.
- [ ] Their behavior is deterministic and repeatable.
- [ ] All data is synthetic.
- [ ] Execution counters prove whether upstream writes occurred.
- [ ] Tests do not depend on public internet availability.

---

# 7. Build the MCP Gateway

**Priority: First major runtime subsystem.** The initial milestone is a working MCP client/server path through AegisMCP, with authentication and audit hooks present from the start.

## 7.1 Downstream Aegis MCP server

- [ ] Prototype the official Python SDK's low-level `Server` API for dynamic tools and centralized dispatch.
- [ ] Implement `on_list_tools` from the approved dynamic tool registry.
- [ ] Implement one `on_call_tool` dispatcher that resolves the exposed name to `(server_id, upstream_tool_name)` and calls the central execution service.
- [ ] Reject unknown tool names even if a client sends a `tools/call` for a tool not currently advertised.
- [ ] Advertise only tools approved for the authenticated principal.
- [ ] Preserve upstream JSON Schema definitions rather than deriving all schemas from static Python signatures.
- [ ] Implement the target transport and authentication boundary.
- [ ] Return structured, sanitized results/errors for `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, inspection unavailable, upstream failure and approval pending.
- [ ] Avoid exposing internal credentials, hidden payloads or raw DLP evidence in tool descriptions/results.

## 7.2 Upstream MCP client manager

- [ ] Implement one MCP client connection to the mock Gmail server.
- [ ] Implement one MCP client connection to the mock Drive server.
- [ ] Keep server connections and credentials isolated per user/server.
- [ ] Implement connection startup and shutdown.
- [ ] Implement reconnection or safe failure behavior.
- [ ] Implement server health status.
- [ ] Implement tool discovery and invocation.
- [ ] Implement timeouts and cancellation behavior where supported.
- [ ] Handle upstream protocol/transport errors without returning false success.

## 7.3 Server registry and tool discovery

- [ ] Implement server registration and ownership checks.
- [ ] Validate server configuration and endpoint; apply SSRF/egress restrictions before connecting.
- [ ] Discover upstream tools and persist complete definitions.
- [ ] Persist input schema, output schema when available, annotations and metadata.
- [ ] Assign both `upstream_tool_name` and namespaced `exposed_tool_name`.
- [ ] Run initial tool metadata/description inspection before first exposure.
- [ ] Require explicit human review/allowlisting before an initially discovered tool becomes executable.
- [ ] Support manual refresh and full reconciliation of upstream tool lists.
- [ ] Handle `notifications/tools/list_changed` or the equivalent subscription mechanism when supported by the pinned SDK, protocol version and selected transport.
- [ ] Treat a change notification as a trigger to fetch `tools/list` again; do not trust the notification as a full change record.
- [ ] Run periodic or reconnect-time reconciliation in case notifications are missed or unsupported.
- [ ] Compare full new definitions with the last approved definition and quarantine changed/new tools until review.

## 7.4 First end-to-end gateway milestone

- [ ] Authenticate the test client and derive the principal from verified transport context.
- [ ] Connect an MCP-compatible test host/client to AegisMCP.
- [ ] Confirm the host discovers one approved namespaced Gmail search tool.
- [ ] Invoke the tool through AegisMCP.
- [ ] Confirm AegisMCP calls the mock Gmail MCP server.
- [ ] Confirm the result returns only after response inspection.
- [ ] Record an invocation ID and sanitized audit event.
- [ ] Verify the protected host configuration does not also connect directly to the upstream mock server.

### Gateway quality gate

- [ ] A test MCP host connects to the authenticated AegisMCP endpoint.
- [ ] At least two mock upstream servers can be registered and distinguished.
- [ ] Dynamic tool discovery returns only approved namespaced tools.
- [ ] Every tool call reaches the central execution service.
- [ ] Unknown or quarantined tool calls cannot reach upstream.
- [ ] Upstream failures do not leak secrets or create false success responses.

---

# 8. Tool Registry, Initial Review, Schema Validation, and Integrity Monitoring

## 8.1 Canonical tool registry

- [ ] Define a canonical representation of each discovered tool.
- [ ] Include `server_id`, `upstream_tool_name`, `exposed_tool_name`, description, input schema, output schema when available, annotations and relevant metadata.
- [ ] Normalize the representation deterministically before hashing.
- [ ] Store the complete approved definition and the current discovered definition.
- [ ] Store approved and current fingerprints separately.
- [ ] Store who reviewed/approved a tool, when, and under which policy.
- [ ] Store status: `PENDING_REVIEW`, `APPROVED`, `REVIEW_REQUIRED`, `QUARANTINED`, `REJECTED` or `DISABLED`.

## 8.2 First-registration poisoning controls

Schema fingerprinting does not make the first definition trustworthy. Before a newly discovered tool is exposed or executed:

- [ ] Treat its name, description, schemas and annotations as untrusted external input.
- [ ] Validate schema structure, size, supported types and unexpected metadata.
- [ ] Scan descriptions and metadata for suspicious instructions, hidden routing requests, credential exfiltration language and attempts to alter agent/system behavior.
- [ ] Compare against a server/tool allowlist and the integration's declared purpose.
- [ ] Present the complete definition to an authenticated reviewer.
- [ ] Keep the tool `PENDING_REVIEW` or `QUARANTINED` until explicitly approved.
- [ ] Record review outcome, reviewer, timestamp, definition hash and evidence.

A clean scan is not proof that a description is safe. Human review and runtime policy enforcement remain necessary.

## 8.3 Schema fingerprinting and change notifications

- [ ] Calculate SHA-256 over the canonical complete tool definition.
- [ ] Store the approved fingerprint from the reviewed definition.
- [ ] Refresh current definitions on connection, manual refresh, supported list-change notification and periodic reconciliation.
- [ ] Recompute current fingerprints.
- [ ] Compare current and approved definitions.
- [ ] Generate a structured before/after diff for changed fields.
- [ ] Mark changed tools `REVIEW_REQUIRED` or `QUARANTINED` according to policy.
- [ ] Prevent changed tools from executing until the required review completes.
- [ ] Record schema-change events in audit history.
- [ ] Test description-only, input-schema, output-schema and annotation changes.
- [ ] Test a tool that retains its name while other definition fields change.
- [ ] Test missed notification/reconnect reconciliation.

**Known limitation:** A fingerprint detects changes to advertised definitions. It cannot prove the hidden server implementation has not changed while keeping the advertised definition identical. Runtime enforcement remains necessary.

### Integrity quality gate

- [ ] A malicious or unreviewed first registration is not silently approved.
- [ ] A changed tool definition is detected and quarantined/reviewed.
- [ ] The dashboard can show the prior approved definition and the new definition diff.
- [ ] Missed list-change events are recovered by reconciliation.
- [ ] Review decisions are attributable and auditable.

---

# 9. Build the Centralized Policy Engine

**Priority: Core security component.** All tool execution must go through a single enforcement path.

## 9.1 Decision model

| Decision | Meaning | Required behavior |
|---|---|---|
| `ALLOW` | Operation is permitted | Continue only after all mandatory pre-execution checks pass |
| `REQUIRE_APPROVAL` | Human authorization is required | Stop before upstream execution and persist the exact operation |
| `BLOCK` | Operation is prohibited | Reject; never call upstream |

Do not use `APPROVAL` or `require_approval` as alternate policy enum values. API field names may be `decision`, but the serialized values are exactly the three uppercase values above.

## 9.2 Canonical policy identity

Policies should match tools by `(server_id, upstream_tool_name)`, not by an ambiguous short tool name. The namespaced `exposed_tool_name` is used for MCP exposure, UI display and convenient logging.

Example:

```yaml
policies:
  - id: POL-001
    name: allow_gmail_search
    server_id: gmail-mock
    upstream_tool_name: search_emails
    decision: ALLOW

  - id: POL-002
    name: require_approval_for_sensitive_external_send
    server_id: gmail-mock
    upstream_tool_name: send_email
    condition: outbound_attachment_classification_includes_confidential
    destination: external
    decision: REQUIRE_APPROVAL

  - id: POL-003
    name: block_unapproved_delete
    server_id: drive-mock
    upstream_tool_name: delete_file
    condition: tool_not_explicitly_authorized
    decision: BLOCK
```

Illustrative rules only: production policy must bind to the authenticated principal, tool registry state, actual arguments, resolved artifacts and destination.

## 9.3 Inputs to the policy engine

- [ ] Authenticated principal derived from verified transport context.
- [ ] Authenticated client identity and granted scopes.
- [ ] Upstream server identity and ownership.
- [ ] `upstream_tool_name`, `exposed_tool_name` and tool integrity status.
- [ ] Validated tool arguments.
- [ ] Resolved outbound attachment/artifact identities.
- [ ] Artifact classification, provenance and taint records.
- [ ] External destination/recipient and destination policy.
- [ ] Threat findings and untrusted-content indicators.
- [ ] Operation impact, reversibility and configured risk.
- [ ] Existing exact-operation approval state, if execution is resuming from approval.

## 9.4 Policy implementation

- [ ] Define a typed policy input and response contract.
- [ ] Implement a deterministic Python evaluator.
- [ ] Return `decision`, `risk_level`, `reason`, `policy_id`, `policy_version` and safe remediation metadata.
- [ ] Keep the policy evaluator separate from MCP transport handling.
- [ ] Define deterministic rule precedence and conflict resolution.
- [ ] Fail closed for missing identity, unknown tools, unclassified external attachments and unavailable required policy evaluation.
- [ ] Add unit tests for every policy, conflict, malformed input and missing input.

## 9.5 Centralized execution service

- [ ] Create one service that all downstream tool handlers must call.
- [ ] Authenticate/resolve principal before policy evaluation.
- [ ] Validate ownership, server state, tool review status, schema and arguments.
- [ ] Resolve outbound files/attachments and data lineage before policy evaluation.
- [ ] Run threat/content checks as signals only.
- [ ] Call policy evaluator.
- [ ] On `BLOCK`, emit audit event and return without upstream call.
- [ ] On `REQUIRE_APPROVAL`, freeze and persist the action, emit audit event and return a pending status without upstream call.
- [ ] On `ALLOW`, execute through the server-specific upstream client.
- [ ] Inspect and sanitize every returned tool result before it reaches the AI host.
- [ ] If mandatory response inspection is unavailable, withhold result content.
- [ ] Ensure no alternate handler or connector path bypasses the service.

### Policy quality gate

- [ ] An allowed operation executes upstream.
- [ ] A blocked operation never reaches upstream.
- [ ] An approval-required operation is paused before upstream execution.
- [ ] Each decision includes its reason and policy reference.
- [ ] Model-provided identity or instructions cannot override backend authorization.

---

# 10. Build the DLP, Data Classification, and Data-Lineage Engine

## 10.1 Two-direction data-protection pipeline

**Inbound response: upstream MCP server → AegisMCP → AI host**

```text
Raw tool response
      |
      v
Content extraction / normalization
      |
      v
Sensitive-data detection and classification
      |
      v
Task-aware policy and redaction
      |
      v
Artifact identity + provenance + taint registration
      |
      v
Sanitized model-facing response
```

**Outbound operation: AI host → AegisMCP → upstream MCP server**

```text
Tool arguments / attachment references
      |
      v
Schema and argument validation
      |
      v
Resolve file IDs / attachment IDs to source artifacts
      |
      v
Look up classification, provenance and taint
      |
      v
Inspect supplied content where supported
      |
      v
Destination + policy evaluation
      |
      +---- ALLOW ------------> controlled execution
      +---- REQUIRE_APPROVAL -> freeze exact operation; do not execute
      +---- BLOCK ------------> reject; do not execute
```

## 10.2 Classification model

- [ ] `PUBLIC` — publicly available information.
- [ ] `INTERNAL` — internal information not intended for public distribution.
- [ ] `PERSONAL` — personal information.
- [ ] `CONFIDENTIAL` — financial, business, or similarly sensitive information.
- [ ] `RESTRICTED` — authentication secrets and especially sensitive data.

## 10.3 Initial detection coverage

- [ ] Email addresses.
- [ ] Phone numbers.
- [ ] Indian PAN (`IN_PAN`) where supported by the selected Presidio package/version.
- [ ] Indian Aadhaar (`IN_AADHAAR`) where supported by the selected Presidio package/version.
- [ ] Bank account identifiers.
- [ ] OTP-like values.
- [ ] Passwords.
- [ ] API keys and tokens.
- [ ] Additional custom entities required by the use case.

**Presidio implementation note:** Inspect the recognizers available in the exact pinned Presidio version before writing custom PAN/Aadhaar recognizers. The current supported-entities documentation lists `IN_PAN` and `IN_AADHAAR`; confirm they are installed, registered/enabled and covered by tests in the chosen analyzer configuration. Add custom recognizers only for gaps you verify.

## 10.4 Artifact registry and taint ledger

- [ ] Define a stable artifact ID independent of display filename.
- [ ] Store owner principal, source server, upstream object ID, source tool, classification, content hash when available, classifier/version and timestamps.
- [ ] Store a taint association between artifact, authenticated principal and trusted execution workspace/context.
- [ ] For the MVP, use a server-assigned workspace per demo principal; do not trust an `execution_context_id` supplied in model-controlled tool arguments.
- [ ] For the full product, narrow taint to an execution context only when that context has a trusted binding to the authenticated principal/client; otherwise use conservative principal/workspace scope.
- [ ] Resolve attachment/document IDs at the gateway before outbound policy evaluation.
- [ ] Do not use filename or a model-supplied classification as authoritative evidence.
- [ ] If an attachment cannot be resolved or its content cannot be inspected when policy requires inspection, block or require a defined human review; never silently default to `PUBLIC`.
- [ ] Revalidate artifact identity/content hash immediately before delayed approved execution when connector capabilities permit.
- [ ] Define taint retention, expiry, revocation and deletion behavior.

## 10.5 DLP implementation

- [ ] Install and configure Presidio analyzer and anonymizer.
- [ ] Select and configure a supported NLP engine/model if required by enabled recognizers.
- [ ] Confirm built-in recognizer availability and registration for the pinned version.
- [ ] Add custom recognizers only for missing entities; add validation/checksum logic where appropriate.
- [ ] Implement entity-specific confidence thresholds and handling.
- [ ] Define classification rules and policy precedence.
- [ ] Inspect every model-facing tool response before forwarding it.
- [ ] Apply task-aware redaction; retain necessary task information when policy permits.
- [ ] Record artifact identity, content hash and provenance for retrieved documents when possible.
- [ ] Inspect outbound arguments and resolve/inspect attachments before writes.
- [ ] Record sanitized DLP findings without raw original values.
- [ ] Define safe behavior for extraction, parser and DLP failures.
- [ ] If mandatory response inspection fails or is unavailable, withhold the response content and return a sanitized error—even for a read operation.
- [ ] If outbound content cannot be classified, do not allow a sensitive external write by default.

## 10.6 DLP test fixtures

- [ ] Normal public document.
- [ ] Document with email addresses.
- [ ] Document with phone numbers.
- [ ] Document with PAN-like values.
- [ ] Document with Aadhaar-like values.
- [ ] Document with bank account identifiers.
- [ ] Document with fake passwords/API keys.
- [ ] Document with mixed sensitive and task-relevant information.
- [ ] Document with false-positive-looking numeric strings.
- [ ] Attachment referenced by stable ID after it was retrieved/classified.
- [ ] Unknown attachment ID and filename-only attachment.
- [ ] Attachment content changed after an approval request was created.

### DLP quality gate

- [ ] Sensitive fields are detected in the controlled fixture set.
- [ ] Required redactions happen before model-facing response delivery.
- [ ] Useful task information is retained where policy permits.
- [ ] Retrieved confidential artifacts receive stable lineage/taint records.
- [ ] Later outbound operations resolve and enforce those records.
- [ ] Unknown/uninspectable outbound attachments are not silently allowed.
- [ ] DLP/response-inspection failure withholds raw response content.
- [ ] Logs do not reveal original sensitive values.

**Limitation:** Automated PII recognition is imperfect. Presidio and custom recognizers reduce risk but cannot guarantee detection of every sensitive value. Do not describe the DLP engine as infallible.

---

# 11. Build the Threat Detection and Tool-Integrity Engine

## 11.1 Prompt-injection and untrusted-content inspection

- [ ] Define all external tool outputs, retrieved email/document content and upstream descriptions as untrusted input.
- [ ] Implement a first-pass heuristic detector for suspicious instruction patterns.
- [ ] Detect likely instruction override, secret exfiltration, unauthorized external transmission, credential requests, concealment requests and attempts to alter security controls.
- [ ] Add model-assisted classification only as an optional signal; it must never make the final authorization decision.
- [ ] Preserve source/provenance and mark the internal result as untrusted.
- [ ] Keep untrusted text separate from trusted policy/authorization state.
- [ ] Record sanitized findings with severity and safe evidence.
- [ ] Independently evaluate every subsequent tool invocation.
- [ ] Add benign fixtures to measure false positives and malicious fixtures to measure detection coverage.
- [ ] Document bypasses and limitations.

## 11.2 Tool-description and metadata inspection at first registration

- [ ] Treat new tool descriptions, schemas, annotations and server-provided metadata as untrusted.
- [ ] Validate schema structure, size, types and metadata.
- [ ] Scan descriptions for prompt-injection-like language, hidden delegation, credential exfiltration or instruction override.
- [ ] Compare tools against server identity, declared purpose and explicit allowlists.
- [ ] Require authenticated human review of first-seen tools before exposure/execution.
- [ ] Store the complete reviewed definition and its fingerprint.
- [ ] Record reviewer, timestamp, findings and approval decision.

A clean description scan is not proof of safety. Initial review, least privilege and runtime enforcement remain required.

## 11.3 Tool integrity and list-change handling

- [ ] Monitor upstream tool-list change notifications when supported by the pinned MCP SDK, protocol version and selected transport.
- [ ] Treat notifications as triggers to fetch the current authoritative tool list.
- [ ] Reconcile on reconnect, manual refresh and periodically so missed events do not leave stale approval state.
- [ ] Canonicalize and fingerprint each complete tool definition.
- [ ] Compare the current definition with the last human-approved definition.
- [ ] Generate a before/after diff.
- [ ] Quarantine changed/new tools pending review.
- [ ] Notify downstream clients of Aegis's exposed tool-list changes where the selected protocol/transport supports the relevant notification/subscription mechanism.
- [ ] Test notification support against the actual target client; do not assume all MCP clients refresh tool lists identically.

## 11.4 Anomaly detection — post-MVP

- [ ] Define simple signals such as unusual tool frequency, unusual access sequences and unexpected server usage.
- [ ] Keep anomaly findings separate from deterministic authorization.
- [ ] Ensure false positives cannot grant broader access.
- [ ] Evaluate ML-based detection only after collecting appropriately governed, sanitized test data.

### Threat detection quality gate

- [ ] Suspicious external content can generate a finding and remains untrusted.
- [ ] A detector failure cannot authorize a sensitive operation.
- [ ] New tool metadata is reviewed before first use.
- [ ] Advertised definition changes trigger re-review/quarantine.
- [ ] Missed notifications are recovered by reconciliation.
- [ ] No claim is made that prompt injection is detected perfectly.

---

# 12. Build the Human Approval Service

The approval service is an independent human authorization boundary. The AI model cannot approve its own operation, and the original tool call must never execute before approval.

## 12.1 Approval lifecycle

```text
Tool invocation intercepted
          |
          v
Policy returns REQUIRE_APPROVAL
          |
          v
Resolve artifacts and freeze exact canonical operation
          |
          v
Encrypt payload + store payload/artifact hashes
          |
          v
Persist PENDING approval in PostgreSQL
          |
          v
Authenticated user reviews the exact operation
          |
       /     \
   REJECT    APPROVE
     |          |
     v          v
  TERMINATE  Atomic state transition / consume grant
                |
                v
       Revalidate frozen payload, principal,
       tool approval state, recipient and artifacts
                |
                v
       Execute only the stored frozen payload
                |
                v
       Record SUCCEEDED / FAILED / UNKNOWN
```

## 12.2 Approval record requirements

- [ ] Approval ID and invocation ID.
- [ ] Verified user/principal ID and authenticated client identity.
- [ ] Server ID, upstream tool name and exposed tool name.
- [ ] Encrypted frozen arguments or secure durable encrypted reference.
- [ ] Canonical payload hash.
- [ ] Destination/recipient and relevant operation metadata.
- [ ] Attachment/artifact IDs and content hashes.
- [ ] Risk level, policy ID/version and reason.
- [ ] Approval status and expiry.
- [ ] Decision maker and decision timestamp.
- [ ] `consumed_at`, execution status and `executed_at`.
- [ ] Sanitized audit references.

## 12.3 Approval service implementation

- [ ] Create a pending request before any upstream side effect.
- [ ] Freeze all arguments needed to execute the operation; encrypt payload at rest.
- [ ] Calculate a deterministic hash from canonical serialized arguments and attachment identities/content hashes.
- [ ] Bind approval to the authenticated principal and original invocation.
- [ ] Set expiry and enforce it during both decision and execution.
- [ ] Authenticate the dashboard user and enforce approval ownership.
- [ ] Implement approve and reject endpoints/UI actions.
- [ ] Use an atomic transaction/conditional update so only one consumer can claim the approval for execution.
- [ ] Revalidate the principal, payload hash, recipient, attachment IDs/hashes, tool registry approval status and current policy before execution.
- [ ] Execute only the frozen stored payload, not mutable arguments from a later AI request.
- [ ] Reject expired, altered, replayed, cross-user or already-consumed approvals.
- [ ] Keep approval UI separate from model-callable MCP tools.
- [ ] Do not provide `aegis_approve_anything` or other model-callable approval bypasses.
- [ ] Record decision and execution outcome separately.

## 12.4 Reliability and idempotency

- [ ] Use an atomic transition from `APPROVED` to `EXECUTING`/`CONSUMED` with one winner.
- [ ] Use idempotency keys where the upstream service supports them.
- [ ] Define crash behavior before upstream execution.
- [ ] Define crash/network behavior after a side effect may have occurred.
- [ ] Do not blindly retry an ambiguous send/share/delete operation.
- [ ] Record ambiguous outcomes as `UNKNOWN` or `RECONCILIATION_REQUIRED` and provide a manual reconciliation path.
- [ ] Ensure a notification or UI refresh never authorizes execution by itself.

### Approval quality gate

- [ ] A pending action has not executed upstream.
- [ ] Rejection guarantees no upstream call.
- [ ] Approval executes the exact frozen action once.
- [ ] Changed recipient, message, attachment or content hash invalidates approval.
- [ ] Expired, replayed and cross-user approvals are rejected.
- [ ] Concurrent attempts result in at most one execution claim.
- [ ] Ambiguous external outcomes are not blindly retried.
- [ ] Approval state and actual execution state are separately visible in audit history.

---

# 13. Build the Audit Service

**Audit instrumentation begins in the first gateway milestone.** A minimal event interface and request correlation ID are foundational. The full audit timeline, retention, exports and tamper-evidence can be expanded later.

## 13.1 Required event data

- [ ] Event ID and correlation/request/invocation ID.
- [ ] Verified user/principal ID and authenticated client identity.
- [ ] Server ID, upstream tool name and exposed tool name.
- [ ] Sanitized arguments metadata or arguments hash (not raw secrets/content).
- [ ] Risk level, decision, policy ID and policy version.
- [ ] Tool integrity status and threat findings.
- [ ] DLP classifications, redaction action and artifact IDs without original sensitive values.
- [ ] Approval ID/status/decision maker where relevant.
- [ ] Execution status and upstream correlation ID where available.
- [ ] Timestamp and duration.

## 13.2 Audit implementation

- [ ] Define a central `AuditWriter`/event interface before implementing the gateway.
- [ ] Emit a request-received event at gateway entry.
- [ ] Emit identity/authentication outcome events without logging bearer tokens.
- [ ] Emit tool registry, schema review and policy decision events.
- [ ] Emit DLP, artifact classification and taint events.
- [ ] Emit approval creation, decision, consumption and execution outcome events.
- [ ] Emit upstream success/failure/unknown events.
- [ ] Persist MVP events in PostgreSQL.
- [ ] Sanitize payloads before persistence.
- [ ] Add append-only permissions/behavior and tamper-evident hash chaining as a product hardening step.
- [ ] Verify event-chain consistency if hash chaining is implemented.
- [ ] Add filtering, pagination, export and retention controls.

### Audit quality gate

- [ ] Every request can be traced from authentication to final execution result.
- [ ] Blocked and pending operations have audit events.
- [ ] Approval decision and side-effect outcome are distinct.
- [ ] No raw tokens, passwords or unnecessary sensitive documents appear in logs.
- [ ] Failure paths also produce sanitized events where audit storage is available.

---

# 14. Identity, Credential Management, and Authentication Security

## 14.1 Northbound MCP authentication

- [ ] Choose the northbound transport and enforce authentication at its HTTP boundary.
- [ ] For the MVP, implement a development-only bearer token mapped to one seeded demo principal.
- [ ] Store only a hash of any static demo token if persisted; keep the secret in an environment variable and compare safely.
- [ ] Derive `user_id` from verified authentication context; never accept it from tool arguments or untrusted JSON fields.
- [ ] Validate token expiry, revocation and required scopes.
- [ ] Bind any client identity and execution workspace to the authenticated principal.
- [ ] Test missing token, invalid token, expired token, wrong audience/resource and insufficient scope.
- [ ] Keep the approval UI authenticated and enforce ownership.

## 14.2 Production OAuth/resource-server integration

- [ ] Integrate an OAuth 2.1-compatible authorization server or identity provider.
- [ ] Implement the MCP resource-server token verifier supported by the pinned SDK.
- [ ] Validate issuer, signature/introspection, expiry, scopes and audience/resource for AegisMCP.
- [ ] Obtain authenticated subject/client/scopes from trusted SDK request context.
- [ ] Enforce tenant and user ownership in all REST and MCP paths.
- [ ] Implement token revocation, key rotation and identity-provider outage behavior.
- [ ] Do not forward a northbound Aegis access token to an upstream server; obtain and use server-specific upstream credentials.

## 14.3 Upstream credential service

- [ ] Define per-user and per-server credential ownership.
- [ ] Implement OAuth connection initiation for required real integrations.
- [ ] Implement callback and state validation.
- [ ] Store upstream tokens encrypted with appropriate key management.
- [ ] Implement token refresh, revocation and minimum-scope enforcement.
- [ ] Audit credential access and refresh without logging secrets.
- [ ] Ensure the LLM never receives access tokens.
- [ ] Validate upstream token audience/resource; never forward a token intended for a different resource.
- [ ] Define key rotation, backup and recovery procedures.

## 14.4 Dashboard/API authentication

- [ ] Require authentication on all administrative APIs.
- [ ] Enforce ownership on server, tool, policy, approval, threat, artifact and audit routes.
- [ ] Protect approval actions against CSRF/request forgery appropriate to the chosen auth mechanism.
- [ ] Validate sessions/tokens and expiry.
- [ ] Implement logout and revocation behavior.
- [ ] Rate-limit sensitive endpoints.
- [ ] Avoid exposing internal stack traces or secrets in API errors.

---

# 15. Dashboard and Administration UI

## 15.1 Build order and required pages

Build a minimal authenticated approval queue and event view alongside the approval backend. Do not make the approval workflow wait for the complete administration dashboard.

| Page | Required capabilities | Delivery |
|---|---|---|
| Approvals | Review the exact operation, approve/reject, inspect state | MVP first |
| Activity / Audit | Show real persisted request, decision and execution events | MVP first |
| Overview | Security status, activity summary, recent events | Product |
| Connected Servers | Register, inspect, enable, disable, disconnect servers | Product |
| Tool Inventory | View full definitions, schemas, diffs and review status | Product |
| Policies | View and configure allow/block/approval rules | Product |
| Threats | Review injection findings, schema changes, suspicious activity | Product |
| Data Protection | View artifact lineage, classifications, DLP findings and redaction policy | Product |
| Settings | Account and security configuration | Product |

## 15.2 Frontend foundation

- [ ] Set up routes and application shell.
- [ ] Implement shared layout and navigation.
- [ ] Implement reusable cards, tables, badges, status labels, and dialogs.
- [ ] Add loading, empty, success, and error states.
- [ ] Add accessible labels and keyboard navigation.
- [ ] Add responsive layout for desktop and mobile approval use.
- [ ] Implement API client and consistent error handling.
- [ ] Ensure all displayed status is sourced from backend data.

## 15.3 Overview page

- [ ] Display connected server count/status.
- [ ] Display invocation count.
- [ ] Display blocked operation count.
- [ ] Display pending approval count.
- [ ] Display DLP finding/redaction count.
- [ ] Display recent threat events.
- [ ] Display recent audit activity.
- [ ] Do not use hardcoded statistics in the integrated application.

## 15.4 Server and tool management

- [ ] List registered servers.
- [ ] Display server health and connection state.
- [ ] Add/register an approved upstream server.
- [ ] Disconnect or disable a server.
- [ ] List discovered tools.
- [ ] Display tool schema and annotations.
- [ ] Display current and approved fingerprint state.
- [ ] Display quarantined or review-required tools.

## 15.5 Policies and approvals

- [ ] Display policy list and enabled state.
- [ ] Display each policy's effect and conditions.
- [ ] Permit only authorized users to modify policies.
- [ ] Display pending approvals.
- [ ] Display exact tool, arguments, recipient, and attachment details relevant to the decision.
- [ ] Display risk reason and expiry.
- [ ] Implement approve and reject controls.
- [ ] Display completed, rejected, expired, and failed states.
- [ ] Prevent approval actions from being duplicated accidentally.

## 15.6 Threats, DLP, and audit

- [ ] Display threat severity and type.
- [ ] Display sanitized evidence.
- [ ] Display tool schema changes.
- [ ] Display DLP entity type and classification without exposing original sensitive value.
- [ ] Display which response fields were redacted, where safe.
- [ ] Display invocation-to-execution timeline.
- [ ] Add filters by time, server, tool, decision, severity, and status.
- [ ] Add pagination.
- [ ] Add controlled export if required.

## 15.7 Live updates

- [ ] Choose Server-Sent Events or WebSockets for dashboard updates.
- [ ] Publish new invocation events.
- [ ] Publish policy decision events.
- [ ] Publish approval request events.
- [ ] Publish threat and schema-change events.
- [ ] Publish execution outcome events.
- [ ] Authenticate event subscriptions.
- [ ] Ensure event payloads are sanitized.
- [ ] Handle reconnects and stale client state.

### Dashboard quality gate

- [ ] The minimal approval page exists before the complete dashboard.
- [ ] Dashboard data comes from actual backend records.
- [ ] Approval changes update the UI.
- [ ] Policy decision, approval state and execution outcome are displayed separately.
- [ ] Security events appear without manually refreshing the page, if live updates are implemented.
- [ ] A user cannot view another user's data.
- [ ] Sensitive information is not leaked in UI payloads or browser logs.

---

# 16. Real MCP Integrations

Start with mock integrations. Add real integrations only after the complete security path is tested against mocks.

## 16.1 Gmail MCP integration

- [ ] Select an upstream Gmail MCP server/connector.
- [ ] Review its source, permissions, tool definitions, and operational behavior.
- [ ] Configure Google Cloud project and OAuth settings.
- [ ] Select the minimum Gmail scopes required.
- [ ] Implement OAuth authorization and callback.
- [ ] Encrypt and store credentials.
- [ ] Connect Aegis upstream client to Gmail MCP.
- [ ] Discover and register Gmail tools.
- [ ] Allow approved read/search operations.
- [ ] Route email sending through policy and approval controls.
- [ ] Verify no send occurs before approval.
- [ ] Test token refresh and revocation.
- [ ] Test connector outage and credential failure.

## 16.2 Google Drive MCP integration

- [ ] Select an upstream Drive MCP server/connector.
- [ ] Review its source, permissions, tool definitions, and operational behavior.
- [ ] Configure Google Cloud and OAuth scopes.
- [ ] Implement authorization and token handling.
- [ ] Encrypt and store credentials.
- [ ] Connect Aegis upstream client to Drive MCP.
- [ ] Discover and register Drive tools.
- [ ] Allow approved search/read operations.
- [ ] Inspect document contents through DLP before returning to AI.
- [ ] Route sharing/deletion or other high-impact operations through policy and approval rules.
- [ ] Test token refresh and revocation.
- [ ] Test connector outage and credential failure.

## 16.3 Google Calendar MCP integration — later

- [ ] Select and review Calendar MCP connector.
- [ ] Configure minimum OAuth scopes.
- [ ] Connect through Aegis upstream client manager.
- [ ] Register and fingerprint Calendar tools.
- [ ] Implement read-only event retrieval first.
- [ ] Add controlled event creation/modification only after policy coverage.
- [ ] Add tests for unauthorized and approval-required operations.

## 16.4 Integration rule

- [ ] All real integrations are connected to the AI host only through AegisMCP for the protected workflow.
- [ ] Tokens are isolated per service.
- [ ] The AI model never receives raw provider credentials.
- [ ] Tool results are inspected before reaching the model.
- [ ] Tool writes pass through policy and approval enforcement.

---

# 17. API and MCP Interface Checklist

## 17.1 Administrative REST APIs

| Endpoint | Method | Purpose | Implemented | Tested | Audited |
|---|---|---|---|---|---|
| `/api/servers` | GET | List servers | [ ] | [ ] | [ ] |
| `/api/servers` | POST | Register server | [ ] | [ ] | [ ] |
| `/api/servers/{id}` | DELETE | Disconnect server | [ ] | [ ] | [ ] |
| `/api/tools` | GET | List registered tools | [ ] | [ ] | [ ] |
| `/api/policies` | GET | Retrieve policies | [ ] | [ ] | [ ] |
| `/api/policies` | PUT | Update policies | [ ] | [ ] | [ ] |
| `/api/approvals` | GET | List approval requests | [ ] | [ ] | [ ] |
| `/api/approvals/{id}/approve` | POST | Approve exact operation | [ ] | [ ] | [ ] |
| `/api/approvals/{id}/reject` | POST | Reject operation | [ ] | [ ] | [ ] |
| `/api/threats` | GET | Retrieve threat events | [ ] | [ ] | [ ] |
| `/api/audit` | GET | Retrieve audit history | [ ] | [ ] | [ ] |

## 17.2 Aegis administrative MCP tools

- [ ] `aegis_list_servers`
- [ ] `aegis_security_status`
- [ ] `aegis_get_approval_status`
- [ ] `aegis_get_security_report`
- [ ] `aegis_request_tool_access`

Do not expose unrestricted model-callable tools such as `aegis_disable_security` or `aegis_approve_anything`. Human approval belongs in a separately authenticated user interface.

---

# 18. Security Engineering and Hardening Checklist

## 18.1 Authorization and least privilege

- [ ] Enforce per-user server ownership.
- [ ] Enforce per-server tool permissions.
- [ ] Apply least-privilege OAuth scopes.
- [ ] Reject unregistered or unapproved servers.
- [ ] Reject unapproved or quarantined tools.
- [ ] Prevent the model from modifying security policy without authorized user action.
- [ ] Prevent the model from approving its own high-risk operations.

## 18.2 Credential security

- [ ] Encrypt tokens and secrets at rest.
- [ ] Do not place secrets in frontend code.
- [ ] Do not expose credentials in tool results.
- [ ] Redact credentials from logs and errors.
- [ ] Isolate credentials across upstream services.
- [ ] Validate token audience/resource for the intended service.
- [ ] Implement rotation and revocation procedures.

## 18.3 MCP and network security

- [ ] Validate incoming request origin/host as required by the chosen transport and deployment.
- [ ] Use HTTPS for remote connections.
- [ ] Validate upstream endpoints.
- [ ] Restrict arbitrary URL access.
- [ ] Apply destination allowlists where applicable.
- [ ] Apply SSRF protections to any server-controlled or user-controlled URL fetching.
- [ ] Set connection and request timeouts.
- [ ] Restrict network access between containers where practical.
- [ ] Do not expose development-only endpoints in deployment.

## 18.4 Fail-safe behavior

- [ ] Missing, invalid, expired or unverifiable northbound identity rejects the request before tool execution.
- [ ] Policy evaluation unavailable: do not execute a protected operation.
- [ ] Tool registry/integrity state unavailable or ambiguous: do not execute unreviewed/changed tools.
- [ ] Mandatory response inspection/DLP unavailable: withhold the tool response content; do not forward raw results, including read results.
- [ ] Outbound attachment cannot be resolved/classified: do not silently allow an external write; block or require a defined review policy.
- [ ] Approval service/database unavailable: do not execute an approval-required operation.
- [ ] Required audit persistence unavailable: do not execute sensitive side effects if the audit record is part of the security control; define safe behavior for reads as well.
- [ ] Upstream failures do not produce false success responses.
- [ ] Ambiguous side-effect outcome is recorded as `UNKNOWN`/`RECONCILIATION_REQUIRED`; do not blindly retry.
- [ ] Quarantined or changed tools remain unavailable until re-reviewed.

## 18.5 Audit and privacy

- [ ] Do not log raw OAuth tokens, API keys, passwords, or OTPs.
- [ ] Do not log entire confidential documents unless explicitly required and safely governed.
- [ ] Sanitize arguments before audit persistence.
- [ ] Limit access to audit data.
- [ ] Define retention and deletion rules.
- [ ] Protect exported audit files.

---

# 19. Testing Strategy

Testing is a first-class workstream. Each feature should have unit tests, integration tests, and relevant security/adversarial tests.

## 19.1 Test layers

### Unit tests

- [ ] Policy rule evaluation.
- [ ] Argument/schema validation.
- [ ] Tool canonicalization and hashing.
- [ ] PII recognizers.
- [ ] Redaction behavior.
- [ ] Threat pattern detection.
- [ ] Operation fingerprint calculation.
- [ ] Approval expiry and one-time use.
- [ ] Audit event sanitization.

### Integration tests

- [ ] Aegis downstream server to upstream mock Gmail server.
- [ ] Aegis downstream server to upstream mock Drive server.
- [ ] Tool discovery and namespacing.
- [ ] Policy decision to upstream execution.
- [ ] DLP response filtering.
- [ ] Approval creation and approval execution.
- [ ] Audit persistence.
- [ ] Dashboard API ownership checks.

### Adversarial/security tests

- [ ] Malicious content in tool output.
- [ ] Poisoned tool description.
- [ ] Changed input schema.
- [ ] Malicious tool arguments.
- [ ] Approval replay.
- [ ] Approved recipient modified.
- [ ] Attachment replaced after approval.
- [ ] Cross-user approval access.
- [ ] Wrong-server credential/token.
- [ ] Malicious URL / SSRF attempt.
- [ ] DLP service unavailable.
- [ ] Policy service unavailable.
- [ ] Concurrent approval requests.

### End-to-end tests

- [ ] Normal email search from host through Aegis to mock Gmail.
- [ ] Sensitive document retrieval and sanitization.
- [ ] Prompt-injection fixture produces a threat event.
- [ ] External sensitive email is paused for approval.
- [ ] Rejection prevents upstream execution.
- [ ] Approval executes the exact frozen operation.
- [ ] Audit dashboard reflects all events.

## 19.2 Canonical security test matrix (T01–T20)

Use this same matrix in the full product roadmap and the companion MVP tracker. Do not restart numbering in other documents.

| ID | Scenario | Expected result | Implemented | Tested/pass | Audited | Evidence / notes |
|---|---|---|---|---|---|---|
| T01 | Missing, invalid or expired northbound token | Request rejected before tool handler execution | [ ] | [ ] | [ ] | |
| T02 | Normal permitted Gmail search | Allowed and routed through Aegis | [ ] | [ ] | [ ] | |
| T03 | Unpermitted tool/operation | Blocked; upstream invocation counter unchanged | [ ] | [ ] | [ ] | |
| T04 | Sensitive document returned by Drive | Required fields redacted before model-facing response | [ ] | [ ] | [ ] | |
| T05 | Response inspector/DLP unavailable during read | Raw response withheld; sanitized error returned | [ ] | [ ] | [ ] | |
| T06 | Confidential artifact read then referenced by ID in outbound email | Artifact classification/taint is resolved for the send | [ ] | [ ] | [ ] | |
| T07 | Tainted confidential artifact sent to external recipient | `REQUIRE_APPROVAL`; no initial upstream send | [ ] | [ ] | [ ] | |
| T08 | User rejects pending external send | Rejected; upstream send counter remains zero | [ ] | [ ] | [ ] | |
| T09 | User approves exact frozen send | Exactly the approved payload is executed once | [ ] | [ ] | [ ] | |
| T10 | Recipient/attachment/content hash changed, approval expired or replayed | Approval invalidated/rejected; no second execution | [ ] | [ ] | [ ] | |
| T11 | Cross-user access to server, artifact or approval | Denied by authenticated ownership checks | [ ] | [ ] | [ ] | |
| T12 | Upstream timeout after possible side effect | Outcome recorded as unknown/reconciliation; no blind retry | [ ] | [ ] | [ ] | |
| T13 | Malicious first-registration tool description | Not exposed/executable until review | [ ] | [ ] | [ ] | |
| T14 | Previously approved tool definition changes | Quarantined/review required; diff available | [ ] | [ ] | [ ] | |
| T15 | Tool-list notification is missed or unsupported | Reconciliation detects drift before use | [ ] | [ ] | [ ] | |
| T16 | Tool output contains secrets/PII | Sanitized evidence only; no raw secret in audit/model response | [ ] | [ ] | [ ] | |
| T17 | Policy engine unavailable | Protected operation fails closed | [ ] | [ ] | [ ] | |
| T18 | DLP/response inspection unavailable | Model-facing response content withheld; outbound protected write blocked | [ ] | [ ] | [ ] | |
| T19 | Malicious instructions in retrieved email | Flagged/untrusted; cannot modify policy or authorize follow-on call | [ ] | [ ] | [ ] | |
| T20 | Protected host also connects directly to upstream | Deployment/configuration audit confirms protected integrations are connected only through Aegis; any direct connection is outside the protection claim | [ ] | [ ] | [ ] | |

## 19.3 Test evidence requirements

For every security test, record:

- [ ] Test ID and date.
- [ ] Software version/commit tested.
- [ ] Test input or fixture name.
- [ ] Expected result.
- [ ] Actual result.
- [ ] Pass/fail status.
- [ ] Relevant sanitized logs or screenshot.
- [ ] Reviewer.
- [ ] Follow-up issue if the test failed.

---

# 20. Observability, Operations, and Reliability

Create the correlation ID and minimal audit event interface in the foundation/gateway phase. The tasks below expand observability beyond that initial instrumentation.

- [ ] Add structured application logs.
- [ ] Add request/correlation IDs across gateway, policy, upstream, approval, and audit components.
- [ ] Add health endpoints for backend and upstream connection status.
- [ ] Add readiness checks for database and required services.
- [ ] Add timeout and cancellation handling.
- [ ] Add safe error handling for upstream connection failures.
- [ ] Add metrics for invocation counts and outcomes if time permits.
- [ ] Add metrics for blocked, approval-required, and allowed operations.
- [ ] Add metrics for DLP detections and redactions.
- [ ] Add metrics for approval wait and execution outcomes.
- [ ] Monitor failed background jobs/notifications.
- [ ] Avoid logging raw sensitive payloads.
- [ ] Document recovery after backend, database, or upstream service restart.

---

# 21. Docker and Deployment

## 21.1 Docker Compose services

| Service | Responsibility | Required for MVP |
|---|---|---|
| `frontend` | React dashboard | Yes |
| `backend` | FastAPI and MCP gateway | Yes |
| `postgres` | Durable storage | Yes |
| `redis` | Optional transient state/background jobs | Deferred; not part of MVP |
| `notification-worker` | External/mobile approval notifications | Deferred; dashboard approval page is sufficient for MVP |
| `mock-gmail` | Mock Gmail MCP server | Yes for repeatable demo |
| `mock-drive` | Mock Drive MCP server | Yes for repeatable demo |
| `malicious-mcp` | Adversarial test server | Recommended |

## 21.2 Deployment checklist

- [ ] Write Dockerfile for backend.
- [ ] Write Dockerfile for frontend.
- [ ] Add Docker Compose configuration.
- [ ] Configure service networking.
- [ ] Configure persistent database volume.
- [ ] Configure environment variable injection.
- [ ] Keep secrets out of images and source control.
- [ ] Add health checks.
- [ ] Add startup ordering/health dependency behavior.
- [ ] Verify clean build from scratch.
- [ ] Verify restart behavior.
- [ ] Verify database persistence after container restart.
- [ ] Expose remote MCP gateway only over HTTPS in deployed environments.
- [ ] Restrict public access to dashboard and administrative APIs.
- [ ] Configure backups and recovery instructions.
- [ ] Document deployment and shutdown commands.

**Do not introduce Kubernetes or distributed microservices for the initial hackathon deployment unless a concrete requirement justifies them.**

---

# 22. Hackathon Demonstration Plan

The central demonstration should show a malicious email attempting to manipulate an AI agent into sharing a confidential document. AegisMCP should inspect the content, protect sensitive information, stop the unauthorized transmission, require human approval for a permitted high-risk action, and record the result.

## 22.1 Demo environment preparation

- [ ] Use synthetic email data.
- [ ] Use synthetic Drive documents.
- [ ] Include one normal email fixture.
- [ ] Include one sensitive financial document fixture.
- [ ] Include one malicious prompt-injection email fixture.
- [ ] Configure the Gmail mock server's send counter.
- [ ] Configure the Drive mock server's write/share counter if applicable.
- [ ] Connect the demo MCP client/AI host to AegisMCP only.
- [ ] Confirm all protected calls pass through Aegis.
- [ ] Start dashboard and live event stream.
- [ ] Reset demo database and mock-server state before the presentation.
- [ ] Prepare a repeatable scripted demo client as a fallback to unpredictable LLM behavior.
- [ ] Prepare screenshots or a recorded backup demonstration.

## 22.2 Five-stage live demonstration

### Demo 1 — Normal operation

Prompt: “Find my latest train ticket confirmation in Gmail.”

- [ ] AI host invokes Gmail search through Aegis.
- [ ] Aegis records the invocation.
- [ ] Policy returns `ALLOW`.
- [ ] Mock Gmail executes the search.
- [ ] Response inspection completes.
- [ ] Result returns to the AI host.
- [ ] Dashboard displays successful operation.

### Demo 2 — Sensitive data protection and taint registration

Prompt: “Read my financial statement and summarize my expenses.”

- [ ] Mock Drive returns a document with synthetic sensitive fields and a stable artifact ID.
- [ ] DLP detects and classifies the fields.
- [ ] Policy-required fields are redacted.
- [ ] Task-relevant values are retained where permitted.
- [ ] AI host receives sanitized content only.
- [ ] Aegis stores the artifact identity, owner, source, classification and content hash where available.
- [ ] Aegis records the artifact as tainted in the trusted principal/workspace context.
- [ ] Dashboard displays redaction and artifact-classification evidence without exposing original values.

### Demo 3 — Prompt injection inspection

- [ ] Retrieve a malicious email fixture.
- [ ] Threat detector flags suspicious instructions.
- [ ] Content is marked as untrusted.
- [ ] Threat event appears in dashboard.
- [ ] Explain that detection is not the only defense and is not guaranteed to catch every injection.

### Demo 4 — Unauthorized external transmission and rejection

Attempt: Send the previously retrieved confidential artifact to an unapproved external recipient using its stable artifact ID.

- [ ] Aegis intercepts the `gmail_send_email` invocation.
- [ ] Aegis resolves the attachment ID and its stored classification/taint.
- [ ] Policy returns `REQUIRE_APPROVAL` before upstream execution.
- [ ] Upstream send counter remains zero before the human decision.
- [ ] Approval request displays exact recipient, attachment identity, classification and risk reason.
- [ ] User rejects the operation.
- [ ] Upstream send counter remains zero after rejection.
- [ ] Audit record shows the rejection and non-execution.
- [ ] Keep a separate block-rule test for operations that must never be approved.

### Demo 5 — Legitimate approved transmission

- [ ] Start a second controlled send to a designated test recipient.
- [ ] Aegis creates an approval request.
- [ ] User reviews exact recipient, content, and attachment.
- [ ] User approves the exact operation.
- [ ] Backend validates the operation fingerprint and consumes approval once.
- [ ] Upstream mock server records exactly one execution.
- [ ] Dashboard displays successful execution and audit evidence.

## 22.3 Five properties to prove to judges

| Property | Evidence to show | Done |
|---|---|---|
| Gateway interception | Invocation visible in Aegis with request/correlation ID | [ ] |
| Effective blocking | Upstream execution counter stays at zero for blocked/rejected call | [ ] |
| DLP enforcement | Sensitive values are absent from model-facing response | [ ] |
| Approval integrity | Frozen and approved operation fingerprints match | [ ] |
| Tool integrity | Changed tool is detected and quarantined | [ ] |

## 22.4 Demo reliability checklist

- [ ] Rehearse the complete flow from a clean reset.
- [ ] Confirm every scenario produces the expected dashboard event.
- [ ] Confirm no live credentials or private accounts are needed.
- [ ] Confirm the demo works without public internet where practical.
- [ ] Prepare a local fallback if the AI host or external integration fails.
- [ ] Prepare a scripted MCP test client to guarantee the exact tool-call sequence.
- [ ] Ensure the scripted client still uses the real running Aegis gateway.
- [ ] Do not fake policy decisions or dashboard metrics.
- [ ] Label any simulated upstream service or synthetic data clearly.

---

# 23. Presentation and Judging Plan

## 23.1 Suggested presentation structure

| Slide | Topic | Key message | Done |
|---|---|---|---|
| 1 | Project title | AegisMCP — Security Infrastructure for AI Agents | [ ] |
| 2 | Problem | AI agents can access tools and perform consequential operations | [ ] |
| 3 | Security gap | Tool connectivity needs independent execution control | [ ] |
| 4 | Solution | AegisMCP sits between AI hosts and upstream MCP servers | [ ] |
| 5 | Architecture | Gateway, threat inspection, DLP, policy, approval, audit | [ ] |
| 6 | Live demo | Show attack, interception, and approval | [ ] |
| 7 | Technical implementation | MCP SDK, FastAPI, Presidio, PostgreSQL, React | [ ] |
| 8 | Feasibility and roadmap | Working MVP, limitations, and next development stages | [ ] |

## 23.2 Core opening message

> AI agents are becoming increasingly capable of interacting with external systems. They can access emails, retrieve documents, manage calendars, and execute actions on behalf of users. But what happens when an AI agent is manipulated by a malicious email into exposing confidential information? AegisMCP introduces an independent security enforcement layer between AI applications and the tools they use.

## 23.3 Core closing message

> AI agents should not automatically be trusted with the authority to execute every operation they can access. Every protected tool invocation should be inspected, evaluated, and authorized before execution. AegisMCP is designed to keep consequential actions under independent security controls and human oversight.

## 23.4 Presentation readiness

- [ ] Explain MCP in one or two sentences without overloading the audience.
- [ ] Explain why a gateway must be in the actual execution path.
- [ ] Explain the difference between detection and enforcement.
- [ ] Show an ordinary allowed operation.
- [ ] Show sensitive data being redacted.
- [ ] Show a malicious content finding.
- [ ] Show an operation stopped before upstream execution.
- [ ] Show a human rejecting an operation.
- [ ] Show a legitimate operation approved and executed.
- [ ] Show the corresponding audit records.
- [ ] Explain known limitations honestly.
- [ ] Keep the live demonstration as the central proof of the project.

---

# 24. Team Organization and Parallel Workstreams

For a four-person team, use these workstreams. For a smaller team, combine roles but preserve the same dependency order.

| Workstream | Responsibilities | Owner |
|---|---|---|
| Backend / MCP | Gateway, upstream clients, protocol handling, discovery, routing | TBD |
| Security | DLP, policies, threat inspection, integrity, approval verification | TBD |
| Frontend | Dashboard, policies, approvals, threats, audit visualization | TBD |
| Integration / QA | Mock servers, OAuth, end-to-end tests, Docker, demo | TBD |

## 24.1 Collaboration checklist

- [ ] Agree on gateway-to-policy input contract.
- [ ] Agree on policy response contract.
- [ ] Agree on approval request schema.
- [ ] Agree on audit event schema.
- [ ] Agree on API response/error formats.
- [ ] Agree on database migration ownership.
- [ ] Agree on shared development environment variables.
- [ ] Define integration checkpoints.
- [ ] Require code review for security-sensitive changes.
- [ ] Require tests with each feature pull request.
- [ ] Keep the main branch runnable.

### Example policy input contract

The `principal` is created by authentication middleware from a verified token. It is not a field supplied by the model or copied from tool arguments.

```json
{
  "principal": {
    "subject": "user_01",
    "client_id": "demo-client",
    "scopes": ["mcp:tools"]
  },
  "server_id": "gmail-mock",
  "upstream_tool_name": "send_email",
  "exposed_tool_name": "gmail_send_email",
  "arguments": {
    "to": "external@example.com",
    "subject": "Statement",
    "attachment_ids": ["artifact_001"]
  },
  "resolved_artifacts": [
    {
      "artifact_id": "artifact_001",
      "classification": "CONFIDENTIAL",
      "content_hash": "sha256:..."
    }
  ],
  "destination_type": "EXTERNAL",
  "threat_findings": ["UNTRUSTED_EMAIL_INSTRUCTIONS"]
}
```

### Example policy response contract

```json
{
  "decision": "REQUIRE_APPROVAL",
  "risk_level": "HIGH",
  "reason": "Confidential artifact shared externally",
  "policy_id": "POL-004",
  "policy_version": 1
}
```

---

# 25. Definition of Done — MVP Acceptance Criteria

Do not call the MVP complete until the relevant criteria are satisfied and evidence is recorded.

## MCP gateway and identity

- [ ] An authenticated MCP client successfully connects to AegisMCP.
- [ ] The principal is derived from verified transport authentication, not tool arguments.
- [ ] AegisMCP connects to multiple upstream mock MCP servers.
- [ ] Upstream tools are discovered and namespaced consistently.
- [ ] Protected tools are routed through the centralized execution service.

## Security enforcement and data lineage

- [ ] Every invocation receives a canonical policy decision.
- [ ] Unauthorized operations never reach upstream.
- [ ] Every model-facing response is inspected before forwarding.
- [ ] Inspection failure withholds raw response content.
- [ ] Retrieved sensitive artifacts are assigned stable identities and taint/provenance records.
- [ ] Outbound attachments are resolved and classified before policy evaluation.
- [ ] Malicious external content is treated as untrusted.
- [ ] New and changed tool definitions trigger review/quarantine.
- [ ] High-risk operations require approval before upstream execution.
- [ ] Approval is bound to exact frozen operation parameters, principal and attachment identities/hashes.
- [ ] Expired, modified, concurrent and replayed approvals are safely rejected.
- [ ] Sensitive operations fail closed when required security controls are unavailable.

## Audit and credentials

- [ ] Audit hooks capture request, decision, DLP, approval and execution outcomes from the first gateway milestone.
- [ ] Sensitive values are not exposed through audit logs.
- [ ] User ownership is enforced for integrations, artifacts and approvals.
- [ ] Upstream credentials are isolated per server and protected from the AI model.

## Product and demo

- [ ] Dashboard displays actual backend data.
- [ ] User can review and reject a pending operation.
- [ ] User can approve a legitimate operation.
- [ ] Five core demo properties are demonstrated with evidence.
- [ ] A clean setup and demo procedure is documented.

---

# 26. Risk Register and Known Limitations

Review this register throughout development. Add new risks when discovered.

| Risk | Impact | Mitigation / response | Reviewed |
|---|---|---|---|
| AI host connects directly to upstream and bypasses Aegis | Gateway protection is incomplete | Configure protected integrations only through Aegis; document that Aegis cannot enforce connections outside its execution path | [ ] |
| Prompt injection is not detected | Malicious instructions may reach the model | Treat all external content as untrusted; independently enforce every tool call | [ ] |
| PII detector misses a sensitive value | Data exposure | Add custom recognizers, validation, tests, and conservative policies | [ ] |
| False-positive DLP detections | Useful content may be removed | Use entity confidence, task-aware policy, and test fixtures | [ ] |
| Tool schema remains unchanged while implementation changes maliciously | Schema fingerprint does not detect hidden behavior | Runtime enforcement, permissions, monitoring, and connector trust review | [ ] |
| Approval is replayed or modified | Unauthorized side effect | Exact operation fingerprint, expiry, atomic one-time consumption | [ ] |
| Upstream executes but response is lost | Duplicate operation risk | Reconciliation state; do not blindly retry external side effects | [ ] |
| Security service unavailable | Unsafe operation may proceed or uninspected data may reach the model | Withhold uninspected responses; fail closed on protected writes and required checks | [ ] |
| Credential leakage | Account compromise | Encryption, least privilege, redaction, per-server isolation | [ ] |
| MCP client compatibility mismatch | Demo/integration failure | Pin SDK/protocol and test exact target client | [ ] |
| Live demo LLM behaves unpredictably | Demo flow may fail | Use a scripted MCP test client against the real Aegis gateway as fallback | [ ] |

## 26.1 Claims that must not be made

- [ ] Do not claim prompt injection can always be detected.
- [ ] Do not claim PII detection is 100% accurate.
- [ ] Do not claim schema fingerprinting detects hidden implementation changes.
- [ ] Do not claim Aegis protects direct connections that bypass the gateway.
- [ ] Do not claim exactly-once execution for third-party services unless the connector/service provides a verifiable mechanism.
- [ ] Do not describe mock integrations as real production integrations.
- [ ] Do not present simulated metrics as measured system results.

---

# 27. Recommended Full-Product Build Order and Phase Gates

This is the dependency order for the complete product. The companion `AegisMCP_Hackathon_MVP_Tracker.md` is the shorter time-boxed route for the event. Audit hooks and identity are foundational and must not be postponed until their full UI/services are complete.

| Order | Phase | Exit condition | Implemented | Tested | Audited |
|---:|---|---|---|---|---|
| 1 | Scope, threat model, ADRs and repository | Architecture decisions and local setup are recorded | [ ] | [ ] | [ ] |
| 2 | Identity boundary and audit event interface | Verified principal is available to tool handlers; early events persist | [ ] | [ ] | [ ] |
| 3 | Database and mock MCP servers | Migrations, controlled fixtures and counters work | [ ] | [ ] | [ ] |
| 4 | MCP gateway and dynamic tool registry | Client invokes approved upstream tool through Aegis | [ ] | [ ] | [ ] |
| 5 | Initial tool review and schema integrity | New/changed tools are reviewed or quarantined | [ ] | [ ] | [ ] |
| 6 | Deterministic policy enforcement | Allow/block/approval decisions prevent unauthorized calls | [ ] | [ ] | [ ] |
| 7 | DLP, artifact registry and taint tracking | Responses are sanitized and outbound operations resolve source data | [ ] | [ ] | [ ] |
| 8 | Human approval service | Exact frozen operation can be approved/rejected and executed once | [ ] | [ ] | [ ] |
| 9 | Full threat detection | Untrusted content and integrity findings are surfaced | [ ] | [ ] | [ ] |
| 10 | Audit, observability and administration UI | End-to-end events and controls are visible | [ ] | [ ] | [ ] |
| 11 | Real Gmail/Drive/Calendar integrations | Real integrations use the same gateway and security pipeline | [ ] | [ ] | [ ] |
| 12 | Credentials, OAuth and key management hardening | Production-grade token lifecycle and isolation are verified | [ ] | [ ] | [ ] |
| 13 | Security hardening and full QA | T01–T20 and extended tests pass or risks are formally accepted | [ ] | [ ] | [ ] |
| 14 | Deployment, recovery and operations | Reproducible deployment and recovery procedures work | [ ] | [ ] | [ ] |
| 15 | Demo, release and product documentation | Verified capabilities are demonstrated and documented accurately | [ ] | [ ] | [ ] |

---

# 28. Development Log and Review Records

# 28. Development Log and Review Records

Use these sections to preserve decisions and evidence as the project evolves.

## 28.1 Milestone log

| Date | Milestone | Commit / PR | Implemented by | Tested by | Audited by | Notes |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | Initial setup | | | | | |
| YYYY-MM-DD | First MCP gateway pass-through | | | | | |
| YYYY-MM-DD | Policy enforcement | | | | | |
| YYYY-MM-DD | DLP pipeline | | | | | |
| YYYY-MM-DD | Approval lifecycle | | | | | |
| YYYY-MM-DD | Dashboard integration | | | | | |

## 28.2 Security findings / issue tracker

| ID | Finding | Severity | Affected component | Owner | Status | Fix / verification evidence |
|---|---|---|---|---|---|---|
| SEC-001 | | | | | Open | |
| SEC-002 | | | | | Open | |
| SEC-003 | | | | | Open | |

## 28.3 Architecture decision record

For every significant decision, record:

```md
### ADR-XXX — Decision title

- Date:
- Status: Proposed / Accepted / Superseded
- Context:
- Decision:
- Alternatives considered:
- Security implications:
- Trade-offs:
- Owner:
```

## 28.4 Release review

- [ ] All MVP acceptance criteria are satisfied.
- [ ] All mandatory security tests pass.
- [ ] Failed tests have documented issues and risk acceptance, if any.
- [ ] Security audit findings are resolved or explicitly accepted by the project owner.
- [ ] No known secrets are committed.
- [ ] Dependencies are pinned.
- [ ] Setup documentation is current.
- [ ] Database migration and backup steps are documented.
- [ ] Demo reset procedure works.
- [ ] Presentation claims match verified implementation.
- [ ] Release tag and commit are recorded.

---

# 29. Final Project Positioning

**Product category:** MCP Security Gateway and AI Agent Governance Platform.  
**Tagline:** The Security Infrastructure for AI Agents.

**Problem:** AI agents can access external services and execute actions, creating risks around sensitive data, malicious instructions, excessive permissions, and unauthorized operations.

**Solution:** An independent security enforcement layer that inspects MCP interactions, controls permissions, protects sensitive information, and requires human approval for high-risk actions.

**Core technology:**

- MCP Gateway.
- Threat Detection.
- Data Loss Prevention.
- Policy Engine.
- Human Approval.
- Audit System.

**Primary differentiator:** AegisMCP does not simply warn users about potentially dangerous AI actions. It sits directly in the execution path and enforces whether those actions are permitted.

---

# 30. Official Development References

Keep these references available during implementation and verify version-specific guidance before making protocol or security decisions.

1. [Official Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
2. [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
3. [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)
4. [Microsoft Presidio](https://github.com/microsoft/presidio)
5. [Microsoft Presidio Documentation](https://microsoft.github.io/presidio/)
6. [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs)
7. [FastAPI Documentation](https://fastapi.tiangolo.com/)
8. [PostgreSQL Documentation](https://www.postgresql.org/docs/)
9. [Docker Compose Documentation](https://docs.docker.com/compose/)
10. [MCP Python SDK — Low-level Server](https://py.sdk.modelcontextprotocol.io/v2/advanced/low-level-server/)
11. [MCP Python SDK — Authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/)
12. [MCP Python SDK — Tool-list updates and subscriptions](https://py.sdk.modelcontextprotocol.io/handlers/context/)
13. [MCP Specification — Server Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
14. [Presidio — Supported Entities](https://github.com/microsoft/presidio/blob/main/docs/supported_entities.md)

---

## Companion hackathon tracker

Use `AegisMCP_Hackathon_MVP_Tracker.md` for the 72-hour, four-workstream vertical slice. It contains the MVP acceptance gates, required test subset, owners, evidence log and live-demo runbook. The full-product backlog above is intentionally broader and should not be treated as a hackathon completion target.

## Final implementation instruction

**The very first technical milestone is the MCP gateway and policy enforcement path — not the frontend, not the AI chatbot, and not the advanced threat dashboard.** First prove that an MCP client can connect to AegisMCP, discover a tool, invoke it through an upstream MCP server, and have AegisMCP enforce a security decision before execution. Build every other capability around that foundation.

