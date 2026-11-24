# Trust Gate

**An independently enforced security gateway for AI agents using the Model Context Protocol (MCP).**

Trust Gate sits between an AI application and the MCP servers it is allowed to use. It provides a central enforcement point for authenticated tool access, request and response inspection, deterministic authorization, sensitive-data protection, human approval, and security auditing.

> **Project status:** Trust Gate's architecture and implementation plan are defined. Treat capabilities as planned until they are implemented and verified by the project's tests. This README does not claim that the system is already production-ready or that prompt-injection and sensitive-data detection are infallible.

---

## Why Trust Gate?

AI agents can use connected tools to read information and perform consequential actions. A malicious instruction embedded in an email or document, excessive tool permissions, or an unintended operation can expose data or cause an external side effect.

Trust Gate places an independently enforced security layer in the execution path:

- Every protected tool invocation is authenticated and evaluated before execution.
- The calling principal is derived from verified transport authentication, never from model-supplied arguments.
- Every model-facing tool response passes through required inspection before it is returned to the AI host.
- Sensitive artifacts retain identity, provenance, and classification so later outbound operations can be evaluated.
- High-risk operations require a human decision bound to the exact operation being authorized.
- Decisions and execution outcomes are recorded as sanitized audit events.

**Core principle:** Trust Gate must enforce security independently of the AI model. An LLM may assist with analysis, but it must never make the final authorization decision.

## How it works

```text
             AI APPLICATION / MCP HOST
                        |
             Authenticated MCP request
                        |
                        v
               TRUST GATE SECURITY GATEWAY
                        |
          +-------------+--------------+
          |                            |
   Identity and tool              Artifact lookup,
   validation                     provenance and taint
          |                            |
          +-------------+--------------+
                        |
              Deterministic policy
                  /     |      \
              ALLOW  REQUIRE_  BLOCK
                     APPROVAL
                |       |
                |   Frozen operation
                |   + authenticated review
                |       |
                +-------+
                        |
                        v
              APPROVED UPSTREAM MCP
                   SERVER TOOL
                        |
                        v
             RESPONSE INSPECTION / DLP
                        |
               Sanitized response
                        |
                        v
                    AI HOST

        PostgreSQL: identity, tool registry, artifacts,
        taint, approvals, invocations and audit events
```

Trust Gate uses an MCP-native broker architecture:

- **Northbound:** exposes a protected MCP interface to an AI application or MCP-compatible host.
- **Southbound:** maintains MCP client connections to approved upstream MCP servers.

All integrations that Trust Gate is expected to protect must be routed through it. An MCP server connected directly to the AI host can bypass the gateway and is outside Trust Gate's enforcement boundary.

## Core security capabilities

| Capability | Responsibility |
|---|---|
| Authenticated gateway | Authenticates the MCP caller and derives the principal from verified request context. |
| MCP tool registry | Discovers upstream tools, stores reviewed definitions, and exposes namespaced tool names. |
| Tool integrity | Reviews tool metadata at registration and detects definition changes that require re-review. |
| Policy engine | Makes deterministic `ALLOW`, `REQUIRE_APPROVAL`, or `BLOCK` decisions. |
| Response inspection and DLP | Inspects model-facing tool output, classifies sensitive content, and redacts or withholds it according to policy. |
| Data lineage and taint | Tracks artifact identity, owner, origin, workspace, content identity, and classification across tool operations. |
| Human approval | Pauses high-risk operations and authorizes only the exact frozen operation reviewed by the user. |
| Audit trail | Records decisions, approval events, and execution outcomes without unnecessarily storing secrets or sensitive content. |

### Canonical values

Use these values consistently across backend logic, APIs, persistence, tests, and the dashboard.

| Concept | Canonical values |
|---|---|
| Policy decision | `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK` |
| Data classification | `PUBLIC`, `INTERNAL`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED` |
| Approval status | `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, `CONSUMED`, `CANCELLED` |
| Execution status | `NOT_STARTED`, `EXECUTING`, `SUCCEEDED`, `FAILED`, `UNKNOWN`, `RECONCILIATION_REQUIRED` |
| Tool review status | `PENDING_REVIEW`, `APPROVED`, `REVIEW_REQUIRED`, `QUARANTINED`, `REJECTED`, `DISABLED` |

Use `(server_id, upstream_tool_name)` as the canonical internal tool identity. Store a separate namespaced `exposed_tool_name`, such as `gmail_send_email`, for the tool presented to the AI host.

## Hackathon MVP

The hackathon deliverable is a deliberately narrow, end-to-end vertical slice. It should prove the security properties before the project expands into a complete integration platform.

1. An MCP client authenticates to Trust Gate.
2. Trust Gate discovers and exposes approved tools from controlled mock Gmail and Drive MCP servers.
3. Every invocation passes through one centralized execution pipeline.
4. A confidential document is inspected and sanitized before its content reaches the AI host; its stable artifact identity, provenance, and classification are recorded.
5. An outbound operation resolves attachment IDs and checks their ownership, provenance, and taint before policy evaluation.
6. Trust Gate requires approval for a high-risk external send before calling the upstream send tool.
7. Rejection leaves the upstream execution counter unchanged. A separately approved frozen operation executes at most once in the controlled test environment.
8. A minimal authenticated dashboard displays approval requests and persisted audit activity.
9. A scripted MCP demo client reproduces the complete scenario without relying on unpredictable LLM behaviour.

### MVP non-goals

The initial MVP does not require real Gmail or Google Drive OAuth integrations, Web Push notifications, Redis, Kubernetes, microservices, multiple identity providers, enterprise delegation, SIEM integration, or advanced ML-based anomaly detection. These are candidates for post-MVP development and are tracked in the full product roadmap.

## Technology direction

| Area | Planned technology | Purpose |
|---|---|---|
| Backend | Python + FastAPI | Application services, authentication boundary, and dashboard APIs |
| MCP | Official MCP Python SDK | Downstream MCP server and upstream MCP clients |
| Dynamic gateway | Prototype the SDK's low-level server API | Runtime tool listing and centralized dispatch |
| Frontend | React + TypeScript | Approval interface and security dashboard |
| Database | PostgreSQL | Durable identity, registry, artifact, approval, invocation, and audit records |
| DLP | Microsoft Presidio + narrowly scoped custom rules | Sensitive-data detection and anonymization |
| Local deployment | Docker Compose | Repeatable development and demonstration environment |

Pin dependency versions and the MCP protocol/client compatibility target during project setup. Use documentation that matches the pinned SDK version; do not assume examples written for another SDK release are compatible.

## Repository layout

The repository is expected to evolve as the implementation is scaffolded. The proposed documentation and planning layout is:

```text
trust-gate/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY_DESIGN.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_SPECIFICATION.md
│   ├── THREAT_MODEL.md
│   └── DEMO_GUIDE.md
├── planning/
│   ├── Trust_Gate_Full_Product_Roadmap.md
│   └── Trust_Gate_Hackathon_MVP_Tracker.md
├── backend/
├── frontend/
├── mock_servers/
├── infrastructure/
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

Keep the detailed architecture in `docs/ARCHITECTURE.md`. The full product roadmap is the long-term backlog; the hackathon tracker is the time-boxed execution plan. Avoid maintaining duplicate architecture specifications in multiple files.

## Documentation and planning

- **[Full Product Roadmap](planning/Trust_Gate_Full_Product_Roadmap.md)** — corrected long-term architecture, complete product scope, database and API design, security requirements, testing, deployment, and post-MVP backlog.
- **[Hackathon MVP Tracker](planning/Trust_Gate_Hackathon_MVP_Tracker.md)** — focused implementation work packages, timeboxes, acceptance criteria, security test matrix, and demonstration runbook.
- **[Architecture](docs/ARCHITECTURE.md)** — detailed system components, data flows, and technical decisions. Create or maintain this document as the canonical architecture reference.
- **[Security Design](docs/SECURITY_DESIGN.md)** — identity, authorization, response inspection, taint tracking, approval integrity, and fail-closed requirements.
- **[Database Schema](docs/DATABASE_SCHEMA.md)** — persistent models, relationships, constraints, and state machines.
- **[Threat Model](docs/THREAT_MODEL.md)** — assets, trust boundaries, threats, mitigations, and residual risks.

Use the **Hackathon MVP Tracker** during the event. Use the **Full Product Roadmap** to manage deferred work and the longer-term product. Track implementation, testing, and security audit separately; do not mark a task tested or audited without recorded evidence.

## Local development setup

> **Implementation status:** The repository setup commands below describe the intended workflow. Exact commands should be added and verified when the backend, frontend, dependency lockfiles, migrations, and Compose services are committed. Do not treat this planning document as evidence that a runnable implementation already exists.

### Prerequisites

- Git.
- A Python version pinned by the backend project configuration.
- A Node.js version and package manager pinned by the frontend project configuration.
- Docker Engine or Docker Desktop with Docker Compose.

### First-time setup

1. Clone the repository.
2. Create the Python environment and install backend dependencies using the committed dependency manager and lockfile.
3. Install frontend dependencies using the committed package manager and lockfile.
4. Copy `.env.example` to `.env` and configure only the local development values required by the mock-only setup.
5. Start the required services using the repository's Docker Compose configuration.
6. Apply database migrations using the project's documented migration command.
7. Start the mock MCP servers and run the scripted demo client.
8. Run the documented unit, integration, and security test commands.

Once the Compose configuration is implemented, the intended service startup command is:

```bash
docker compose up --build
```

The exact environment-variable names, migration command, application commands, and test commands must be documented alongside the actual `pyproject.toml`, frontend package configuration, `.env.example`, and Compose services. Do not invent or assume values before they are committed and verified.

## Security invariants

These are project requirements, not optional UI features:

- **Identity:** Derive the calling principal from verified transport authentication. Never trust a `user_id` supplied in model-controlled tool arguments.
- **Complete mediation:** Route every protected tool invocation through one central execution pipeline.
- **Response protection:** Inspect every model-facing tool response. If mandatory inspection or DLP is unavailable, withhold the uninspected content and return only a sanitized error.
- **Outbound data protection:** Resolve attachment/document IDs and verify ownership, provenance, and classification before evaluating external transmission. A filename alone is not proof of artifact identity or sensitivity.
- **Approval integrity:** Bind an approval to the authenticated principal, server, tool, destination, frozen arguments, artifact identities, and relevant content hashes. Consume it atomically and at most once.
- **Fail-closed execution:** If authentication, policy enforcement, required inspection, or approval verification is unavailable, do not perform the protected operation.
- **Tool integrity:** Review tool metadata on initial registration. Reconcile tool definitions after change notifications and on reconnect/refresh; quarantine unreviewed or changed definitions according to policy.
- **Audit hygiene:** Persist security decisions and execution outcomes without logging raw credentials or unnecessary sensitive document content.
- **No bypass claims:** Trust Gate only protects integrations actually routed through its gateway.

## Demonstration

The planned demonstration should show the following sequence using synthetic data:

1. A normal read-only tool operation is allowed through the gateway.
2. A mock Drive document containing synthetic sensitive values is inspected and sanitized before the result reaches the AI host.
3. A retrieved artifact is registered with a stable ID and `CONFIDENTIAL` classification.
4. A malicious email is flagged and treated as untrusted content.
5. A send operation references the confidential artifact by ID and targets an external recipient.
6. Trust Gate requires approval before upstream execution. Rejecting the request leaves the mock Gmail send counter at zero.
7. A separate exact operation is approved, verified, and executed once.
8. The dashboard shows the authenticated principal, artifact classification, policy decision, approval decision, execution outcome, and audit evidence.

Use a scripted MCP demo client so the sequence is repeatable. An LLM-powered host can be shown as an additional integration, but the security proof must not depend on unpredictable model behaviour.

## Limitations and responsible claims

Trust Gate is an enforcement gateway, not a guarantee that every malicious instruction or sensitive value can be detected. Prompt-injection inspection and automated PII recognition are imperfect. The primary protection is independent backend authorization, least privilege, artifact-aware outbound checks, response inspection, exact-operation approval, and fail-closed behaviour when mandatory controls are unavailable.

Trust Gate cannot protect a connection that bypasses its gateway. External services may also have ambiguous outcomes after network failures; record an `UNKNOWN` or `RECONCILIATION_REQUIRED` state rather than blindly retrying a potentially completed side effect. Do not claim production-grade security until the relevant controls have been implemented, tested, audited, and independently reviewed.

## Development references

- [Model Context Protocol specification](https://modelcontextprotocol.io/specification)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Python SDK — low-level server](https://py.sdk.modelcontextprotocol.io/v2/advanced/low-level-server/)
- [MCP Python SDK — authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/)
- [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)
- [Microsoft Presidio documentation](https://microsoft.github.io/presidio/)
- [Presidio supported entities](https://github.com/microsoft/presidio/blob/main/docs/supported_entities.md)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Docker Compose documentation](https://docs.docker.com/compose/)

---
