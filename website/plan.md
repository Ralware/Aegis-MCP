# Trust Gate Companion Website — Plan

## Scope and constraints

Build a standalone, responsive product showcase and deterministic security simulation in `website/`, preserving the existing Trust Gate repository and backend plans. Use plain local development only: do not initialize or attach Manus-managed website services, add a Manus project declaration, sync code to Manus, connect a database, or call real Gmail, Drive, OAuth, PostgreSQL, or external MCP servers. The website is an honest showcase and simulation, not the Trust Gate backend.

The source repository has the README, Hackathon MVP Tracker (`Project Checklist.md`), full roadmap (`Roadmap.md`), and `Template.webp`; it has no existing frontend. The README and unchecked tracker/roadmap make clear that real product capabilities are planned rather than verified. Use the roadmap's exact 15 build phases and T01–T20 security test definitions. Distinguish `Implemented`, `Planned`, and `Simulated`; keep implementation, test, and audit status separate and never mark product work complete on the basis of simulated UI activity.

## Implementation approach

Create an independent React + TypeScript + Vite app with a small set of dependencies, reusable page components, direct-linkable routes, a shared shell, and local-only state. Serve all required routes: `/`, `/architecture`, `/security`, `/demo`, `/technology`, `/documentation`, `/roadmap`, `/console`. Public pages use the editorial product shell; `/console` uses a separate compact application shell with sidebar navigation and denser information layout. Unknown routes receive a usable not-found page.

Keep the deterministic simulation engine and types separate from view components. Define shared local entities for mock servers/tools, principals, policies, invocations, artifacts, findings, approval requests, executions, audit events, and test results. Persist scenario and console state in `localStorage`, initialize reproducible synthetic fixtures, and provide a complete reset. Derive console metrics and histories from that shared state. Include scenario controls for normal search, sensitive Drive retrieval/redaction, malicious email, confidential external-send approval, rejection, and a separate approved operation that consumes once. Every action must be local and synthetic; visibly disclaim that no live integrations are connected.

Build reusable interaction primitives (tabs, expandable rows, filters, dialogs, selectors, step controls, status labels, copy/view panels) so links and controls do useful work. Implement policy outcomes only as `ALLOW`, `REQUIRE_APPROVAL`, and `BLOCK`; approval and execution statuses remain separate. Approval must freeze the simulated operation, rejection must not increment the upstream-send count, and a distinct approved operation can execute at most once. Show response inspection, redaction, artifact identity/provenance/taint, threat signals, fail-closed outcomes, and sanitized audit events as simulation results rather than claims about the real product.

The `/console` application includes Overview, Connected Servers, Tool Inventory, Policy Engine, Approvals, Data Protection, Threat Centre, Audit Explorer, Security Testing (T01–T20), and Settings. Make navigation state persistent and keep simulated status distinct from real project verification. Show Gmail and Drive as mock/simulated; Calendar as planned.

The Architecture page provides selectable components, highlighted connections, responsibility/input/output details, and normal, blocked, approval-required, and inspection-failure flows. Its execution pipeline separates request-side authorization from response-side inspection. Artifact lineage is interactive. The Security page details each documented capability, including purpose, workflow, example, limitations, location, and honest planned/simulated status. The technology page lists only the documented stack and differentiates verified choices from plans. The documentation hub links only to material actually present in the repository (README, Project Checklist, Roadmap) or provides clearly labeled on-page summaries; do not imply absent docs/API files exist. The roadmap contains the 15 phases in `Roadmap.md`, with separate Implemented/Tested/Audited evidence fields and no invented completion evidence.

## Design

- **Design Movement:** Reference-driven cinematic monochrome product editorial, adapted from the supplied framed crypto-site screenshot into sober AI-agent security infrastructure.
- **Core Principles:** Preserve generous negative space; keep the hero as the primary focal point; make security states legible without alarmist neon; prioritize truthful product status and functional interactions.
- **Color Philosophy:** Black and charcoal establish a quiet technical stage; diffuse silver and pale sage-gray suggest protected pathways and precision; amber/red appear only for review/block states.
- **Layout Paradigm:** A centered, rounded black website canvas floats within a charcoal surround. A separate inset, atmospheric hero carries the homepage composition; later sections unfold as editorial bands. The console deliberately changes to a compact sidebar-and-workspace layout.
- **Signature Elements:** Fine curved SVG connection paths with restrained moving data points; sparse identity/policy/audit nodes; capsule navigation, controls, and status labels.
- **Interaction Philosophy:** Every selector or control reveals actual local simulation state or navigates; no ornamental dead buttons. Pipeline selections surface component detail. Respect reduced-motion preferences.
- **Animation:** Slow ambient light drift and subtle line-flow only; transition states gently; disable movement under `prefers-reduced-motion`; avoid blinking, spinning, or heavy glow.
- **Typography System:** Space Grotesk for display, Inter/system sans for body and controls, JetBrains Mono for technical metadata; large regular-weight hero headline and muted secondary copy.
- **Brand Essence:** Independent policy and inspection boundary between AI agents and MCP tools; precise, restrained, trustworthy.
- **Brand Voice:** Direct and security-specific. Examples: “Security, before execution.” “AI agents can request actions. Trust Gate controls whether those actions are allowed to happen.”
- **Wordmark & Logo:** Original compact geometric gateway/shield glyph made from simple inline SVG, not a lock or copied logo.
- **Signature Brand Color:** Pale sage-gray `#A7C8BC`, used sparingly against black.

## Project structure

- `website/` — independent companion app; does not alter or replace root backend/project documentation.
- `website/src/app/` — router, route metadata, public and console shells.
- `website/src/components/` — shared navigation, typography/status primitives, cards, dialogs, SVG diagrams, and controls.
- `website/src/pages/` — home, architecture, security, demo, technology, documentation, roadmap, and console page views.
- `website/src/simulation/` — typed shared state, deterministic rules, scenario transitions, fixtures, persistence, reset, and derived selectors.
- `website/src/styles/` — design tokens, responsive styling, reduced-motion rules, and public/console layout styles.
- `website/public/` — route manifest and static favicon/brand assets.

## Dependencies and delivery boundaries

Use the smallest practical dependency set compatible with React + TypeScript: Vite, React, React DOM, and a client-side router if needed. Prefer hand-authored CSS, SVG, and browser APIs over a large UI/charting package. Do not add live service SDKs. Local state is synthetic and non-authoritative. Keep real security-test results unclaimed; the website's own simulation is not project verification. The site's source and any runtime remain plain local and under the user's existing repository workflow.
