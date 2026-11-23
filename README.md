# AegisMCP — Architecture & Implementation Roadmap

> **Diagram compatibility:** All architecture and workflow diagrams use plain-text ASCII inside fenced `text` blocks. They render consistently in GitHub, VS Code, editors and Markdown viewers without Mermaid support.

> **Project objective:** Build an independent security gateway that sits between AI applications and their connected MCP servers, inspecting tool calls and responses, enforcing permissions, protecting sensitive information, and requiring human approval for high-risk operations.
>
> **Recommended architecture:** MCP-native security gateway  
> **Core principle:** Every protected MCP tool call must pass through an independently enforced security decision before execution, and every tool response must pass through an inspection and data-protection pipeline before reaching the AI.

---

## Contents

1. [Overall System Architecture](#1-overall-system-architecture)
2. [Detailed Component Architecture](#2-detailed-component-architecture)
3. [Complete Request Execution Workflows](#3-complete-request-execution-workflows)
4. [Technology Stack and Backend Organization](#4-technology-stack-and-backend-organization)
5. [Database Architecture](#5-database-architecture)
6. [API and MCP Interface Design](#6-api-and-mcp-interface-design)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Security Design Requirements](#8-security-design-requirements)
9. [Testing Strategy](#9-testing-strategy)
10. [Hackathon MVP](#10-what-should-the-actual-hackathon-mvp-look-like)
11. [Team Organization](#11-development-environment-and-team-organization)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Definition of Done](#13-definition-of-done)
14. [Recommended Build Sequence](#14-recommended-order-of-actual-development)
15. [Important Architectural Decisions](#15-important-architectural-decisions)
16. [Final Project Positioning](#16-final-project-positioning)
17. [Development References](#17-development-references)

---

# 1. Overall System Architecture

## 1.1 High-Level Architecture

AegisMCP is an MCP-aware broker with two distinct interfaces:

- **Northbound:** Exposes a protected MCP interface to AI applications.
- **Southbound:** Maintains individual MCP client connections to approved upstream servers.

The gateway understands tool discovery, schemas, invocation and responses. It is not merely a generic HTTP proxy inspecting JSON-RPC traffic.

```text
                         +----------------------------------+
                         |       AI APPLICATION / HOST      |
                         | Claude / MCP-compatible client   |
                         +----------------------------------+
                                      |
                         MCP over Streamable HTTP
                                      |
                                      v
+-----------------------------------------------------------------------+
|                         AEGIS SECURITY GATEWAY                        |
|                                                                       |
|  +-------------------+      +-------------------+                     |
|  | Request Inspector |----->| Threat Analyzer   |                     |
|  +-------------------+      +---------+---------+                     |
|                                       |                               |
|                                       v                               |
|                            +-------------------+                      |
|                            | Policy Engine     |                      |
|                            +---+-----------+---+                      |
|                                |           |                          |
|                    ALLOW       |           | APPROVAL REQUIRED        |
|                                v           v                          |
|                    +----------------+  +-------------------+          |
|                    | Upstream MCP   |  | Approval Manager  |          |
|                    | Connection     |  +---------+---------+          |
|                    | Manager        |            |                    |
|                    +-------+--------+            |                    |
|                            |                     |                    |
|                            v                     v                    |
|                    +----------------+    +-------------------+        |
|                    | Data Guard /   |    | Human Approval     |       |
|                    | DLP Inspection |    | Required           |       |
|                    +-------+--------+    +-------------------+        |
|                            |                                          |
|                            v                                          |
|                    +----------------+                                 |
|                    | Audit Engine   | <---- Blocked / approved events |
|                    +----------------+                                 |
+----------------------------+------------------------------------------+
                             |
                     Approved MCP calls
                             |
          +------------------+-------------------+
          |                  |                   |
          v                  v                   v
 +----------------+  +----------------+  +-------------------+
 | Gmail MCP      |  | Drive MCP      |  | Calendar MCP      |
 | Server         |  | Server         |  | Server            |
 +-------+--------+  +-------+--------+  +---------+---------+
         |                   |                     |
         v                   v                     v
 +----------------+  +----------------+  +-------------------+
 | Google Gmail   |  | Google Drive   |  | Google Calendar   |
 +----------------+  +----------------+  +-------------------+

NOTE: Every protected integration must be routed through Aegis.
A server connected directly to the AI host can bypass this gateway.
```

**Important deployment constraint:** The host must route all protected integrations through Aegis. An MCP server connected separately and directly to the AI host can bypass the gateway. Aegis cannot claim to protect connections it does not control.

## 1.2 Operating Modes

| Mode | Description | Recommendation |
|---|---|---|
| Gateway mode | External AI application connects to Aegis as its MCP server | Primary architecture |
| Managed-host mode | Aegis provides its own AI interface and manages all MCP clients | Secondary feature |

Build gateway mode first. Managed-host mode can be introduced later if more control over model context, tool discovery and host-side behavior is required.

---

# 2. Detailed Component Architecture

The backend should initially be a **modular monolith**: one FastAPI application with clear internal module boundaries. There is no need to introduce distributed microservices prematurely.

## 2.1 MCP Gateway Service

**Priority: Core component — build first.**

**Responsibility:** Receive MCP requests, identify intended operations, enforce the security workflow, and communicate with upstream servers.

### A. Downstream MCP Server

Exposes approved upstream capabilities to AI clients.

| Exposed tool | Original upstream |
|---|---|
| `gmail_search_emails` | Gmail MCP |
| `gmail_read_email` | Gmail MCP |
| `drive_search_files` | Drive MCP |
| `drive_read_file` | Drive MCP |
| `calendar_get_events` | Calendar MCP |
| `gmail_send_email` | Gmail MCP |

Tools should be namespaced to prevent collisions.

### B. Upstream MCP Client Manager

Creates and manages isolated MCP client connections.

```text
Aegis Gateway
    |
    |--- Gmail MCP Client
    |       |--- Gmail MCP Server
    |
    |--- Drive MCP Client
    |       |--- Drive MCP Server
    |
    |--- Calendar MCP Client
            |--- Calendar MCP Server
```

Do not share a single upstream credential or connection identity between different services.

### Implementation Responsibilities

- Server registration.
- MCP protocol negotiation and discovery.
- Tool enumeration.
- Tool schema validation.
- Tool name mapping.
- Invocation routing.
- Response processing.
- Connection health monitoring.
- Failure handling.

Use the official MCP Python SDK rather than manually implementing JSON-RPC. The SDK supports client and server implementations, with Streamable HTTP for remote deployment and stdio for local integrations.

## 2.2 Threat Detection Engine

**Responsibility:** Identify malicious or suspicious MCP behavior before it can affect the user.

| Submodule | Responsibility |
|---|---|
| Prompt Injection Detector | Inspect tool outputs and externally sourced content |
| Tool Integrity Monitor | Detect tool schema and description changes |
| Anomaly Detector | Identify unusual tool usage and data flows |
| Input Validator | Detect malicious parameters and unsafe requests |

### Tool Schema Fingerprinting

When a user approves an MCP server, Aegis stores a fingerprint of its reviewed tool definitions.

Example:

```json
{
  "server": "gmail",
  "tool": "send_email",
  "schema_hash": "sha256:...",
  "approved": true,
  "reviewed_at": "2026-11-23T10:00:00Z"
}
```

When the tool definitions change:

1. Recompute the fingerprint.
2. Compare it with the approved fingerprint.
3. Identify the changed fields.
4. Mark the tool as requiring review.
5. Prevent the affected operation until reviewed.

Hash the complete tool definition, including schemas and annotations, not just the description.

**Limitation:** A fingerprint detects changes to advertised definitions, not malicious behavior hidden behind an unchanged schema. Integrity monitoring and runtime enforcement are both needed.

## 2.3 DLP Engine — Data Loss Prevention

**Responsibility:** Detect and minimize sensitive information in both directions.

| Direction | What happens |
|---|---|
| Upstream response → AI | Detect and redact sensitive data before exposing it to the model |
| AI → Upstream server | Detect sensitive information being sent through arguments, messages, uploads or external requests |

### DLP Pipeline

```text
+------------------+
|    Raw Content   |
+--------+---------+
         |
         v
+--------------------------+
| Content Extraction       |
+------------+-------------+
             |
             v
+--------------------------+
| Sensitive Data Detection |
+------------+-------------+
             |
             v
+--------------------------+
| Data Classification      |
+------------+-------------+
             |
             v
+--------------------------+
| Policy Evaluation        |
+-----+---------------+----+
      |               |
   SAFE          SENSITIVE
      |               |
      v               v
+-------------+  +--------------------------+
| Continue    |  | Mask / Block / Approval  |
+------+------+  +------------+-------------+
       |                      |
       +----------+-----------+
                  |
                  v
       +----------------------+
       | Sanitized Output     |
       +----------------------+
                  |
                  v
          Return to AI Host
```

### Suggested Classification Levels

- Public.
- Internal.
- Personal.
- Confidential.
- Restricted.

### Initial Detection Coverage

- Email addresses.
- Phone numbers.
- Aadhaar and PAN patterns.
- Bank account identifiers.
- OTPs.
- Passwords and API keys.

**Recommended technology:** Microsoft Presidio, custom rules/checksum validators and a secret-scanning module.

Do not make a single regular-expression match the final security decision. Use confidence levels and policy-specific behavior.

## 2.4 Risk and Policy Engine

**Priority: Most important security module.**

The policy engine makes security decisions through deterministic backend rules.

Its three possible outcomes are:

| Decision | Meaning |
|---|---|
| `ALLOW` | Execute the operation |
| `APPROVAL` | Pause execution and request human authorization |
| `BLOCK` | Reject the operation |

The decision should evaluate:

- User identity.
- Connected MCP server.
- Tool identity.
- Tool integrity status.
- Input parameters.
- Data sensitivity.
- External recipient.
- Permission scope.
- Operation reversibility.
- Threat detection results.
- Existing approval grants.

Implement the policy engine as a deterministic rules system initially. OPA/Rego or a custom Python policy evaluator can be considered as the project grows.

### Example Policies

```yaml
policies:
  - name: allow_email_search
    tool: gmail_search_emails
    effect: allow

  - name: restrict_financial_document_sharing
    tool: drive_share_file
    data_classification:
      - confidential
      - restricted
    effect: require_approval

  - name: block_unapproved_deletion
    tool: drive_delete_file
    effect: block
```

These are illustrative policies. Production rules should also bind to the actual user, server, destination and arguments.

## 2.5 Human Approval Service

Handles actions that cannot be automatically executed.

### Responsibilities

- Approval request creation.
- Request expiration.
- Approve and reject.
- One-time authorization.
- Request status.
- Parameter integrity verification.
- Execution result tracking.

### Approval Must Be Bound to the Exact Action

For example, if a user approves:

```json
{
  "tool": "gmail_send_email",
  "to": "person@example.com",
  "attachment": "report.pdf"
}
```

The AI must not subsequently change the recipient or attachment and reuse that approval.

The backend should calculate an operation fingerprint and require the exact approved parameters at execution time.

### Recommended Approval Workflow

1. Tool invocation is intercepted.
2. Aegis creates a pending approval record containing a frozen operation payload.
3. The tool call returns an `approval_required` result.
4. The user reviews the request in the dashboard or on their phone.
5. The user approves or blocks the request.
6. On approval, the Aegis execution service validates and executes the frozen request.
7. The result is recorded and made available through the dashboard and an approval-status tool.

This avoids keeping an MCP request suspended indefinitely while waiting for a mobile notification.

## 2.6 Audit Service

Every meaningful operation should generate a structured security event.

Example:

```json
{
  "event_id": "EVT-1001",
  "user_id": "USER-01",
  "server": "gmail",
  "tool": "send_email",
  "risk_level": "high",
  "decision": "approval_required",
  "timestamp": "2026-11-23T10:30:00Z"
}
```

The audit service should store:

- Request ID.
- User and server identities.
- Tool name.
- Risk decision.
- Policy that triggered the decision.
- Approval status.
- Execution status.
- Sanitized evidence.
- Timestamp.

Use append-only event records and preferably a tamper-evident hash chain. Do not log raw secrets or entire personal documents.

## 2.7 Credential Management Service

Keep credential management independent from the gateway.

### Responsibilities

- OAuth connection management.
- Token encryption.
- Token refresh.
- Scope enforcement.
- Credential revocation.
- Server-specific credentials.
- Credential access auditing.

The LLM must never receive access tokens.

Aegis should hold credentials securely and only pass the necessary authorization to the designated upstream connector.

MCP authorization guidance requires attention to the token's intended resource and does not permit blindly forwarding tokens issued for another service.

## 2.8 Dashboard and Administration Service

The dashboard should allow users to understand and control Aegis without understanding the underlying MCP protocol.

| Page | Purpose |
|---|---|
| Overview | Security status and recent activity |
| Connected Servers | Manage MCP server connections |
| Tool Inventory | Review available tools and schemas |
| Policies | Configure permissions |
| Approvals | Approve or reject sensitive actions |
| Threats | Review detected suspicious activity |
| Data Protection | Configure classification and redaction |
| Audit Logs | Inspect previous operations |
| Settings | Account and security configuration |

---

# 3. Complete Request Execution Workflows

The following workflows define how the components interact and should guide backend implementation.

## 3.1 Workflow A — Ordinary Read-Only Request

**Example user instruction:** “Find my latest train ticket in Gmail.”

```text
USER                 AI HOST             AEGIS GATEWAY       THREAT / POLICY       GMAIL MCP
 |                     |                       |                    |                 |
 |-- Find train ------>|                       |                    |                 |
 |                     |-- Search emails ----->|                    |                 |
 |                     |                       |-- Inspect request ->|                |
 |                     |                       |<------ ALLOW -------|                |
 |                     |                       |---------------- Search tool -------->|
 |                     |                       |<--------------- Search results ------|
 |                     |                       |-- Inspect response ->|                |
 |                     |                       |<-- Sanitized result -|                |
 |                     |<-- Permitted result --|                    |                 |
 |                     |                       |-- Record audit event                 |
 |<-- Ticket details --|                       |                    |                 |
 |                     |                       |                    |                 |

All tool calls and responses pass through Aegis before reaching the AI or upstream service.
```

Steps:

1. AI requests `gmail_search_emails(query="train ticket")`.
2. Gateway identifies the upstream server, tool identity, user and request arguments.
3. Threat inspection validates the tool definition and request parameters.
4. Policy evaluation checks permissions and data-access rules. If allowed, continue.
5. The Gmail MCP client calls the connected Gmail server.
6. Response inspection scans for sensitive information and malicious instructions.
7. Sanitized results are returned to the AI.
8. An audit event records the request, decision and outcome.

The user experiences a normal AI interaction. Security checks happen without unnecessary interruptions.

## 3.2 Workflow B — Sensitive Information Exposure

**Example:** “Read my bank statement and summarize it.”

The document contains financial information.

1. AI requests Drive document retrieval.
2. Gateway verifies the tool and access policy.
3. Drive returns the original document content.
4. DLP classifies financial information.
5. Policy decides which fields are necessary for the requested task.
6. Unnecessary identifiers are redacted.
7. Sanitized content is returned to the AI.

**Important:** Redaction should be based on the requested task. If the user asks for a spending summary, the account number is generally irrelevant, but transaction amounts may be necessary. The objective is not to destroy useful context; it is to minimize exposure.

## 3.3 Workflow C — High-Risk Operation

**Example:** “Send my bank statement to this external address.”

```text
AI HOST        AEGIS GATEWAY      POLICY ENGINE      APPROVAL SERVICE      USER       GMAIL MCP
   |                 |                  |                   |                |             |
   |-- send_email ->|                  |                   |                |             |
   |                 |-- evaluate ---->|                   |                |             |
   |                 |<-- APPROVAL ----|                   |                |             |
   |                 |   REQUIRED      |                   |                |             |
   |                 |-- freeze exact operation + payload hash ----------->|             |
   |                 |<---------------- pending request ID ----------------|             |
   |<-- approval required; operation NOT executed ---------|                |             |
   |                 |                  |                   |-- notify ---->|             |
   |                 |                  |                   |<-- approve / reject --------|
   |                 |<--------------- validated decision --|                |             |
   |                 |-- revalidate operation + approval ->|                |             |
   |                 |<--------------- authorized ---------|                |             |
   |                 |---------------------------------------------------- execute ----->|
   |                 |<--------------------------------------------------- result --------|
   |<-- result / status ----------------|                   |                |             |
   |                 |                  |                   |                |             |

If rejected, expired, modified, or already used: do not call Gmail.
Approval is bound to the exact recipient, attachment, content and tool arguments.
```

Steps:

1. Tool call reaches gateway: `gmail_send_email(...)`.
2. Risk engine identifies external sharing of a financial document.
3. Execution is stopped before reaching Gmail.
4. Approval request is created with exact recipient and attachment details.
5. User receives a mobile notification.
6. User approves or rejects the exact operation.
7. Execution service validates the approval and operation fingerprint.
8. If approved, the frozen operation is executed through the upstream MCP connection.
9. Result and approval evidence are recorded.

**Never execute the original tool call first and ask for approval afterward.** Interception must happen before the side effect.

---

# 4. Technology Stack and Backend Organization

Use Python throughout the initial backend. This makes it easier to build MCP client/server components, security modules and data-processing pipelines together.

## 4.1 Recommended Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React + TypeScript | Dashboard |
| Styling | Tailwind CSS | UI |
| Backend | Python + FastAPI | Application services |
| MCP | Official MCP Python SDK | MCP client and server |
| Protocol transport | Streamable HTTP | Remote MCP connections |
| AI | LLM with tool calling | Agent interaction |
| DLP | Microsoft Presidio | PII detection |
| Secret scanning | Custom rules + secret detectors | Credential detection |
| Database | PostgreSQL | Persistent data |
| Cache | Redis | Pending approvals and transient state |
| Notifications | Web Push | Approval alerts |
| Authentication | OAuth 2.1-compatible provider | User login and connected accounts |
| Encryption | KMS/Vault-backed key management | Credential protection |
| Containers | Docker | Deployment and isolation |

The official Python SDK is the most practical starting point because it supports creating both MCP clients and servers. Its documentation includes Streamable HTTP support.

**Protocol version decision:** Build against the SDK's currently supported protocol and test compatibility with the clients intended for the demonstration. Do not assume every MCP application has adopted the same protocol version.

## 4.2 Proposed Repository Structure

```text
aegismcp/
├── frontend/
│   └── React dashboard, approvals, monitoring, server management
│
├── backend/
│   ├── gateway/
│   │   └── MCP server, MCP clients, request routing, schema registry
│   │
│   ├── security/
│   │   └── Threat detection, DLP, validation, schema integrity
│   │
│   ├── policy/
│   │   └── Risk engine, authorization rules, policy evaluation
│   │
│   ├── approvals/
│   │   └── Approval creation, verification, execution, notifications
│   │
│   ├── connectors/
│   │   └── Gmail, Drive, Calendar MCP adapters
│   │
│   ├── credentials/
│   │   └── OAuth, tokens, encrypted secrets
│   │
│   ├── audit/
│   │   └── Event recording, security history
│   │
│   ├── api/
│   │   └── REST endpoints, authentication, WebSocket notifications
│   │
│   ├── database/
│   │   └── Models, repositories, migrations
│   │
│   └── tests/
│       └── Unit, integration, security and regression tests
│
├── infrastructure/
│   └── Docker, database, Redis, deployment configuration
│
├── README.md
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

This structure deliberately separates policy decisions from MCP transport handling. The gateway should not contain dozens of hardcoded security rules.

---

# 5. Database Architecture

PostgreSQL should be the primary persistent database.

| Table | Important fields | Purpose |
|---|---|---|
| `users` | id, email, created_at | User accounts |
| `mcp_servers` | id, user_id, name, endpoint, status | Registered upstream servers |
| `server_credentials` | id, server_id, encrypted_secret, scopes | Encrypted credentials |
| `tool_registry` | id, server_id, tool_name, schema_hash, approved_version | Tool inventory |
| `security_policies` | id, user_id, rule, effect, enabled | User security settings |
| `tool_invocations` | id, server_id, tool_name, arguments_hash, status | Execution history |
| `threat_events` | id, invocation_id, threat_type, severity | Threat findings |
| `approval_requests` | id, invocation_id, payload_hash, status, expires_at | Pending approvals |
| `approval_decisions` | id, approval_id, decision, decided_by, timestamp | Approval history |
| `audit_events` | id, event_type, payload, previous_hash, event_hash | Audit history |
| `data_classifications` | id, invocation_id, data_type, severity | DLP findings |

### Database Design Rules

- Store encrypted OAuth credentials separately from normal application data.
- Never store full sensitive document contents just to generate audit logs.
- Redact credentials and PII from logged arguments.
- Use UUIDs for external identifiers.
- Add ownership constraints so one user cannot view another user's approvals or integrations.
- Keep approval decisions and audit records durable even if Redis is unavailable.

Redis should only hold transient information, such as short-lived approval notification state, not be the sole source of approval authorization.

---

# 6. API and MCP Interface Design

Distinguish between:

1. The external MCP interface exposed to AI clients.
2. The internal REST APIs used by the dashboard.
3. The upstream MCP client calls used to communicate with external servers.

## 6.1 Proposed MCP Tools

Aegis should expose protected upstream operations to AI with namespaced identities.

For its own administrative functions, expose a small number of dedicated tools:

| Tool | Responsibility |
|---|---|
| `aegis_list_servers` | List connected servers |
| `aegis_security_status` | Retrieve security status |
| `aegis_get_approval_status` | Check a pending operation |
| `aegis_get_security_report` | Retrieve sanitized threat findings |
| `aegis_request_tool_access` | Request permission for an additional tool |

The AI should not get unrestricted tools such as `aegis_disable_security` or `aegis_approve_anything`.

Approval must happen through a separately authenticated user interface, not a command generated by the model.

## 6.2 Proposed Dashboard APIs

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/servers` | GET | List servers |
| `/api/servers` | POST | Register server |
| `/api/servers/{id}` | DELETE | Disconnect server |
| `/api/tools` | GET | List registered tools |
| `/api/policies` | GET | Retrieve policies |
| `/api/policies` | PUT | Update policies |
| `/api/approvals` | GET | List approval requests |
| `/api/approvals/{id}/approve` | POST | Approve an exact operation |
| `/api/approvals/{id}/reject` | POST | Reject an operation |
| `/api/threats` | GET | Retrieve threat events |
| `/api/audit` | GET | Retrieve audit history |

All administrative routes must require authentication and enforce user ownership.

---

# 7. Implementation Roadmap

Build in a dependency-driven sequence. There is no point implementing an elaborate threat dashboard before the gateway can intercept and control an actual MCP tool call.

## 7.1 Development Milestones

### Milestone 1 — Foundation and MCP Gateway

Build:

- MCP server.
- Upstream MCP clients.
- Server registry.
- Tool routing.

**Deliverable:** Connect an AI client through Aegis to a test MCP server and successfully execute a read-only tool.

### Milestone 2 — Policy Enforcement

Build:

- Tool allowlisting.
- Argument validation.
- Risk classification.
- Allow/block decisions.

**Deliverable:** Demonstrate that the same tool can be allowed or blocked depending on its parameters and the user's permissions.

### Milestone 3 — DLP and Threat Detection

Build:

- PII identification.
- Data redaction.
- Prompt-injection detection.
- Tool-schema fingerprinting.

**Deliverable:** Retrieve a document containing test sensitive data and show that the AI receives a sanitized response.

### Milestone 4 — Human Approval

Build:

- Approval lifecycle.
- Mobile notifications.
- Secure approval verification.
- Controlled execution.

**Deliverable:** Attempt to send a sensitive document and demonstrate that nothing is transmitted before approval.

### Milestone 5 — Dashboard and Audit

Build:

- Server inventory.
- Security events.
- Approval queue.
- Policies.
- Audit timeline.

**Deliverable:** A user can inspect and control every protected integration through one dashboard.

### Milestone 6 — Security Testing and Demonstration

Build and test:

- Attack scenarios.
- Bypass attempts.
- Schema modifications.
- Credential isolation.
- Approval replay.
- Failure scenarios.

**Deliverable:** A working end-to-end demonstration with repeatable test cases.

## 7.2 Detailed Development Tasks

| Milestone | Engineering tasks | Completion condition |
|---|---|---|
| M1 | MCP client/server, routing, tool registry | End-to-end pass-through works |
| M2 | Policy evaluator, allowlists, validation | Unauthorized calls are blocked |
| M3 | PII detection, sanitization, injection checks | Sensitive output is filtered |
| M4 | Approval records, UI, authorization checks | Approved operation executes exactly once |
| M5 | Audit storage, dashboard and monitoring | Decisions are traceable |
| M6 | Adversarial testing and integration | Attack simulations pass expected controls |

### Important Implementation Dependencies

- **Tool registry before schema fingerprinting:** You need a canonical tool definition before you can reliably detect changes.
- **Policy evaluator before approval UI:** The system must know which operations require approval.
- **DLP before response forwarding:** Otherwise, sensitive content may already have reached the model.
- **Frozen operation records before approval execution:** The approval system must know exactly what is being authorized.
- **Audit hooks throughout development:** Do not postpone logging until the end.

---

# 8. Security Design Requirements

Aegis is itself a security product. Its failure modes matter just as much as its features.

| Security requirement | Implementation |
|---|---|
| Least privilege | Per-server and per-tool permissions |
| No credential exposure | Encrypted, isolated token storage |
| No approval replay | One-time authorization with expiry |
| No modified approved action | Bind approval to operation fingerprint |
| No direct bypass | All protected integrations routed through Aegis |
| No unreviewed tool changes | Schema integrity validation |
| No sensitive audit leakage | Log redaction and data minimization |
| No unsafe default execution | Sensitive writes fail closed |
| Server isolation | Separate connections and credentials per server |
| No arbitrary URL access | Destination allowlists and SSRF protections |

### Failure Behavior

What happens when the threat detector goes offline?

For sensitive write operations, the default should be to block execution. A security component failing must not accidentally disable the security controls.

### Concurrent Requests

What happens when two requests attempt to use the same approval?

Only one should succeed. Use atomic database state transitions, unique operation IDs and idempotency controls.

The security architecture should follow OWASP guidance on tool integrity, least privilege, multi-server isolation, output validation, consent and credential handling.

---

# 9. Testing Strategy

Treat security testing as a first-class development activity. Test whether Aegis behaves correctly when the AI, tool or external content is actively trying to circumvent it.

## 9.1 Test Suite

| Test | Attack or condition | Expected result |
|---|---|---|
| T01 | Normal Gmail search | Allowed |
| T02 | Read permitted Drive document | Allowed |
| T03 | Email containing prompt injection | Flagged and treated as untrusted |
| T04 | PAN/Aadhaar in returned document | Redacted according to policy |
| T05 | External transmission of sensitive file | Approval required |
| T06 | Unauthorized deletion | Blocked |
| T07 | Upstream tool schema changed | Quarantined pending review |
| T08 | Approval used twice | Second execution rejected |
| T09 | Approved recipient changed | Approval invalidated |
| T10 | Expired approval reused | Rejected |
| T11 | OAuth token for wrong server | Rejected |
| T12 | Upstream connector unavailable | Safe failure |
| T13 | User attempts to access another user's approval | Denied |
| T14 | Malicious URL in tool arguments | Destination policy enforced |
| T15 | DLP engine unavailable | Sensitive operation fails closed |

## 9.2 Test Organization

**Unit tests:** Test individual policy rules, PII detection, risk classification and operation hashing.

**Integration tests:** Connect an actual Aegis gateway to mock MCP servers and verify tool routing.

**Adversarial tests:** Send malicious instructions in tool descriptions, returned email content and tool arguments.

**Authorization tests:** Attempt to reuse approvals, change parameters, access other users' data and execute without valid permissions.

**End-to-end tests:** Run the complete workflow through the dashboard, gateway and upstream services.

For the hackathon, create a separate intentionally malicious test MCP server. It can simulate poisoned tool descriptions, changed schemas and malicious responses without involving actual user accounts or dangerous operations.

---

# 10. What Should the Actual Hackathon MVP Look Like?

Resist the temptation to demonstrate ten different security features. Three functioning security mechanisms are more convincing than ten partially implemented ones.

## 10.1 MVP Feature Set

**Must have**

- Working MCP client/server.
- Upstream server registration.
- Tool routing.
- Deterministic security policy.
- PII redaction.
- Approval and rejection.
- Audit history.

**Should have**

- Prompt-injection detection.
- Schema fingerprinting.
- Mobile-friendly approval notifications.
- Server health monitoring.

**Can wait**

- Advanced anomaly detection.
- Custom ML threat classifiers.
- Large-scale enterprise policy management.
- Multiple identity providers.
- Complex multi-user delegation.
- Full SIEM integration.

This separation is important. The MVP must prove that Aegis can actually prevent an unauthorized action, not simply identify that an action looks suspicious.

## 10.2 Initial Integrations

Start with two upstream integrations:

1. **Gmail MCP** — email search and controlled sending.
2. **Drive MCP** — document search and retrieval.

Use mock data and controlled test servers initially, then replace them with actual Google integrations once the security workflow is reliable.

## 10.3 Three Mandatory Demonstrations

| Demonstration | What judges should see |
|---|---|
| Prompt injection | Malicious email retrieved, flagged and prevented from authorizing an external action |
| DLP | Original sensitive information transformed into sanitized model context |
| Human approval | Email with sensitive attachment paused until a user approves the exact recipient and attachment |

The audit dashboard should show all three interactions in real time.

---

# 11. Development Environment and Team Organization

For a hackathon team, divide the implementation into four workstreams.

| Workstream | Responsibilities |
|---|---|
| Backend / MCP | Gateway, upstream clients, protocol handling and tool routing |
| Security | DLP, injection detection, policies, authorization and schema integrity |
| Frontend | Dashboard, approvals, notifications and event visualization |
| Integration / Testing | Mock MCP servers, OAuth, end-to-end tests and demonstration scenarios |

The workstreams should share fixed interfaces from the beginning.

### Example Gateway-to-Policy Contract

```json
{
  "user_id": "user_01",
  "server_id": "gmail",
  "tool_name": "send_email",
  "arguments": {
    "to": "external@example.com",
    "subject": "Statement",
    "attachment": "bank_statement.pdf"
  },
  "data_classification": "confidential"
}
```

### Example Policy Response

```json
{
  "decision": "require_approval",
  "risk_level": "high",
  "reason": "Sensitive document shared externally",
  "policy_id": "POL-004"
}
```

This contract lets the frontend, security engine and gateway be developed independently.

---

# 12. Deployment Architecture

For the initial deployment, use Docker Compose. Kubernetes and distributed microservices are unnecessary for this project phase.

```text
+-------------------------------------------------------------------+
|                        DOCKER COMPOSE                             |
|                                                                   |
|  +----------------------+       +-------------------------------+ |
|  | Frontend             |<----->| Backend                       | |
|  | React dashboard      |       | FastAPI                       | |
|  |                      |       | MCP gateway                   | |
|  +----------------------+       | Security modules              | |
|                                 +---------------+---------------+ |
|                                                 |                 |
|                       +-------------------------+---------+       |
|                       |                                   |       |
|                       v                                   v       |
|             +---------------------+             +----------------+|
|             | PostgreSQL          |             | Redis          ||
|             | Policies            |             | Transient      ||
|             | Approvals           |             | state          ||
|             | Audit records       |             | Background jobs||
|             +---------------------+             +-------+--------+|
|                                                         |         |
|                                                         v         |
|                                                +-----------------+|
|                                                | Notification    ||
|                                                | Worker          ||
|                                                | Approval events ||
|                                                +--------+--------+|
|                                                         |         |
|                                                         +-------> |
|                                                   Backend         |
+-------------------------------------------------------------------+

PostgreSQL stores durable records. Redis is for transient state and jobs.
The notification worker reports delivery/status; it does not authorize actions.
```

### Development Environment

- Run the frontend and backend locally.
- Use Docker containers for PostgreSQL and Redis.
- Run mock MCP servers separately.
- Use `.env` only for development credentials.
- Use an encrypted secrets manager or KMS-backed storage for deployment.
- Expose the MCP gateway over HTTPS using Streamable HTTP.
- Keep sensitive operations inaccessible when the policy service is unavailable.

For the first version, a modular monolith is the right architectural choice. The threat engine, approval manager and audit service can be split into independent services if the product grows.

---

# 13. Definition of Done — How Do We Know Aegis Works?

Use this checklist as the acceptance criteria before calling the MVP functional.

- [ ] An AI client successfully connects to Aegis through MCP.
- [ ] Aegis connects to multiple upstream MCP servers.
- [ ] All exposed tools are registered and namespaced.
- [ ] Every tool invocation passes through policy evaluation.
- [ ] Unauthorized tool operations never reach upstream servers.
- [ ] Sensitive information is redacted before reaching the model.
- [ ] Malicious content is identified and treated as untrusted.
- [ ] Changes to approved tool schemas trigger re-review.
- [ ] High-risk operations generate approval requests.
- [ ] Approval is bound to exact operation parameters.
- [ ] Expired and reused approvals are rejected.
- [ ] Audit events capture decisions and execution results.
- [ ] One user cannot access another user's integrations or approvals.
- [ ] Sensitive operations fail closed when essential security controls are unavailable.

---

# 14. Recommended Order of Actual Development

Follow this order rather than allowing everyone to implement unrelated features.

## Step 1 — Establish the MCP Gateway

Implement one downstream Aegis MCP server, one upstream test MCP server, tool discovery and forwarding.

Do not proceed until an external MCP client can successfully invoke a tool through Aegis.

## Step 2 — Intercept Tool Calls

Add the tool registry, schema validation, namespaced tools and policy engine.

Prove that a blocked request never reaches the upstream server.

## Step 3 — Add DLP

Integrate Presidio and custom sensitive-data detection. Inspect all responses before forwarding them to the AI.

## Step 4 — Add Threat Detection

Implement tool integrity checks and untrusted-content inspection. Keep heuristic threat detection separate from deterministic authorization.

## Step 5 — Implement the Approval Lifecycle

Freeze the exact operation, issue approval requests, implement one-time authorization, and execute only after successful validation.

## Step 6 — Build the Dashboard

Present policies, connected servers, approvals, threats and audit history.

## Step 7 — Perform Adversarial Testing

Use malicious test servers, prompt-injection fixtures, approval replay tests and credential-isolation tests.

---

# 15. Important Architectural Decisions

These decisions should not be compromised:

### 1. Do Not Use an LLM as the Final Authorization Mechanism

An LLM can help classify suspicious content, but the actual Allow/Block/Approval decision must be enforced through backend code.

### 2. Do Not Build a Generic Transparent Proxy First

Build an explicit MCP broker that discovers upstream tools, exposes approved and namespaced versions of those tools, and routes calls through the security pipeline. A transparent proxy can be explored later.

### 3. Do Not Allow Approval Based on an Action Description Alone

Bind it to the exact recipient, document, tool arguments and user identity.

### 4. Do Not Forward Unfiltered Tool Responses

Even a trusted MCP server can return untrusted external content.

### 5. Do Not Claim That Prompt-Injection Detection Is Foolproof

Preventing dangerous follow-on operations through authorization rules is more important than detecting every malicious sentence.

These decisions are consistent with MCP security principles and OWASP's recommended defenses for MCP deployments.

---

# 16. Final Project Positioning

## AEGISMCP

### The Security Infrastructure for AI Agents.

**Product category:** MCP Security Gateway and AI Agent Governance Platform.

**Problem:** AI agents can access external services and execute actions, introducing risks around sensitive data, malicious instructions, excessive permissions and unauthorized operations.

**Solution:** An independent security enforcement layer that inspects MCP interactions, controls permissions, protects sensitive information and requires human approval for high-risk actions.

**Core technology:**

- MCP Gateway.
- Threat Detection.
- Data Loss Prevention.
- Policy Engine.
- Human Approval.
- Audit System.

**Primary differentiator:** Aegis does not simply warn users about potentially dangerous AI actions. It sits directly in the execution path and enforces whether those actions are permitted.

### Hackathon Demonstration

A malicious email attempts to manipulate an AI agent into sharing a financial document. Aegis detects the suspicious content, prevents unauthorized sharing, sanitizes sensitive information and requires explicit human approval for any permitted external transmission.

---

# 17. Development References

1. [Official MCP Specification](https://modelcontextprotocol.io/specification)
2. [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
3. [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)
4. [Microsoft Presidio](https://github.com/microsoft/presidio)
5. [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs)

---

## Final Technical Recommendation

Build the project around one central principle:

> **Every MCP tool call must pass through an independently enforced security decision before execution, and every tool response must pass through an inspection and data-protection pipeline before reaching the AI.**

That is the foundation of AegisMCP. Everything else — the dashboard, mobile notifications, threat analytics and advanced detection — should be built around that foundation.

**The very first thing to implement is the gateway and policy enforcement path — not the frontend, not the AI chatbot, and not the threat dashboard.** Once an actual MCP tool call can be intercepted, evaluated and blocked by Aegis, the core technical contribution of the project has been established.
