# Trust Gate V1

Trust Gate is a backend-first security gateway for Gemini agents that use Google Gmail and Drive. The existing React showcase is unchanged; this repository now includes the V1 backend in `backend/`.

## Implementation assessment

The original repository supplied a Vite/React showcase and extensive architecture/roadmap documents, but no backend, persistence layer, authentication, MCP server, provider adapters, or environment configuration. V1 adds those missing server components without changing the website. The old planning references to mock integrations describe the hackathon plan, not this V1 implementation.

## Security design

Every protected call—HTTP, Gemini function call, or MCP tool—uses `ExecutionService`:

`identity → registered tool/schema → artifact resolution → deterministic policy → approval (if needed) → provider → DLP/response inspection → provenance/audit`

Read operations are allowed only for the Google account owned by the verified OAuth principal. Sends always require an expiring, one-use, frozen approval. MCP is served at `/mcp` using the official MCP SDK's Streamable HTTP ASGI application and requires the same signed, HttpOnly Trust Gate session. Provider tokens never leave the backend, are encrypted with Fernet at rest, and are never sent to Gemini. Gemini also has a separately prompted structured security analyzer for untrusted retrieved mail; its output is recorded as a signal and cannot override deterministic policy.

## Setup

1. Use Python 3.11+ (the pinned Google GenAI SDK requires it) and PostgreSQL 16+.
2. `Copy-Item .env.example .env`, then set a unique `TOKEN_ENCRYPTION_KEY`, `SESSION_SECRET`, Gemini key/model, and Google OAuth client credentials. Do not commit `.env`.
3. In Google Cloud, create a **Web application** OAuth client, add the exact redirect URI from `GOOGLE_OAUTH_REDIRECT_URI`, configure the consent screen/test users, and enable **Gmail API** and **Google Drive API**. The requested scopes are read-only Drive, Gmail read/send, and OpenID identity.
4. Start PostgreSQL: `docker compose up -d postgres`.
5. Create a virtual environment, install: `pip install -e .`.
6. Run migrations: `alembic -c backend/alembic.ini upgrade head`.
7. Start: `uvicorn backend.app.asgi:app --reload --port 8000`.
8. Open `http://localhost:8000/api/integrations/google/connect`, complete the Google flow, then verify `GET /api/integrations/google/status`.

The backend API is available at `/docs`. Browser authentication is established only after Google verifies an ID token. The OAuth callback checks state, expiry, single-use consumption, and the exact configured redirect URI.

## APIs

| Endpoint | Purpose |
|---|---|
| `GET /api/integrations/google/connect` | starts real authorization-code OAuth with offline access |
| `GET /api/integrations/google/callback` | validates state, exchanges code, verifies Google identity |
| `GET /api/integrations/google/status` | reports connected account without tokens |
| `POST /api/integrations/google/disconnect` | revokes and removes usable credentials |
| `POST /api/tools/{tool}` | executes an approved tool through the security pipeline |
| `GET/POST /api/approvals...` | lists, approves, or rejects frozen sends |
| `POST /api/chat` | Gemini function-calling bridge (protected tools only) |
| `/mcp` | authenticated Streamable HTTP MCP endpoint |

MCP tools: `gmail_search_emails`, `gmail_get_message`, `gmail_get_thread`, `gmail_send_email`, `drive_search_files`, `drive_get_file_metadata`, and `drive_read_file`.

## Operational limits and live verification

`drive_read_file` enforces the configured byte ceiling via the Google API download stream and redacts before model-facing output. Unsupported/binary formats should be rejected rather than forwarded until a format-specific extractor is configured; do not treat unknown content as public. The current V1 Drive reader exports native Google Workspace files to text and accepts downloadable UTF-8 text. MIME-specific extraction for PDF, DOCX, XLSX, and CSV is the next hardening increment before claiming broad document-format support.

No Google or Gemini credentials were supplied to this workspace, so live OAuth/API calls and real-account E2E tests have not run. The deterministic security tests can run with `pytest`; live tests must use a dedicated Google test account and must only send when `LIVE_TEST_ENABLED=true` plus a recipient allowlist is configured. A send timeout is recorded as `UNKNOWN`; it is never automatically retried.

## Evidence status

- Implemented: backend configuration, PostgreSQL schema/migration, OAuth, encrypted refresh storage, Gmail/Drive adapters, pipeline, DLP, approvals/audit, MCP and Gemini bridge.
- Locally verified: syntax and deterministic policy/DLP tests (record actual command output when run).
- Requires credentials: OAuth connect/refresh/revoke, Gmail/Drive operations, Gemini function calls, and live send approval execution.
