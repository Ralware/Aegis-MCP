export type Decision = "ALLOW" | "REQUIRE_APPROVAL" | "BLOCK";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "CONSUMED";
export type ExecutionStatus = "NOT_STARTED" | "SUCCEEDED";
export type ScenarioId =
  | "normal-search"
  | "confidential-read"
  | "malicious-email"
  | "confidential-send"
  | "rejection"
  | "approved-send";

export interface AuditEvent {
  id: string;
  at: string;
  date?: string;
  principal?: string;
  server?: string;
  tool?: string;
  approval?: string;
  execution?: string;
  threat?: string;
  artifactId?: string;
  type: string;
  message: string;
  decision?: Decision;
}
export interface Artifact {
  id: string;
  name: string;
  classification: string;
  provenance: string;
  tainted: boolean;
  hash: string;
}
export interface Approval {
  id: string;
  principal?: string;
  server?: string;
  tool?: string;
  operation: string;
  arguments?: Record<string, string>;
  recipient: string;
  expiresAt?: string;
  artifactId: string;
  hash: string;
  status: ApprovalStatus;
  execution: ExecutionStatus;
  reason: string;
  created: string;
}
export interface SimulationState {
  version: 1;
  scenario: ScenarioId;
  speed: number;
  stepIndex: number;
  invocations: number;
  sends: number;
  decisions: Record<Decision, number>;
  artifacts: Artifact[];
  approvals: Approval[];
  threats: {
    id: string;
    severity: string;
    title: string;
    evidence: string;
    at: string;
  }[];
  audit: AuditEvent[];
  results: Record<string, string>;
  connected: Record<string, boolean>;
  testResults: Record<string, "NOT_RUN" | "SIMULATED_PASS">;
}

export const scenarios: {
  id: ScenarioId;
  number: string;
  title: string;
  summary: string;
  tool: string;
}[] = [
  {
    id: "normal-search",
    number: "01",
    title: "Normal Gmail search",
    summary: "Authenticated, read-only lookup with response inspection.",
    tool: "gmail_search_emails",
  },
  {
    id: "confidential-read",
    number: "02",
    title: "Confidential Drive retrieval",
    summary:
      "Synthetic identifiers are redacted and an artifact is registered.",
    tool: "drive_get_document",
  },
  {
    id: "malicious-email",
    number: "03",
    title: "Suspicious email",
    summary:
      "Untrusted instructions become a threat signal, not an authorization.",
    tool: "gmail_get_email",
  },
  {
    id: "confidential-send",
    number: "04",
    title: "External send · pending",
    summary:
      "A confidential artifact is frozen for human review; no send occurs.",
    tool: "gmail_send_email",
  },
  {
    id: "rejection",
    number: "05",
    title: "Reject operation",
    summary: "Reject the pending operation; upstream send count stays at zero.",
    tool: "gmail_send_email",
  },
  {
    id: "approved-send",
    number: "06",
    title: "Separate approved send",
    summary: "A separate synthetic operation is consumed and executes once.",
    tool: "gmail_send_email",
  },
];

const KEY = "trust-gate-simulation-v1";
const stamp = () =>
  new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
const id = (prefix: string) =>
  `${prefix}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
const initial = (): SimulationState => ({
  version: 1,
  scenario: "normal-search",
  speed: 1,
  stepIndex: 0,
  invocations: 0,
  sends: 0,
  decisions: { ALLOW: 0, REQUIRE_APPROVAL: 0, BLOCK: 0 },
  artifacts: [],
  approvals: [],
  threats: [],
  audit: [],
  results: {},
  connected: { Gmail: true, Drive: true, Calendar: false },
  testResults: {},
});
export function loadState(): SimulationState {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as SimulationState;
      if (parsed.version === 1) return { ...initial(), ...parsed };
    }
  } catch {
    /* Invalid local fixtures are safely discarded. */
  }
  return initial();
}
export function saveState(state: SimulationState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* Simulation remains usable for this tab. */
  }
}
export function resetState() {
  localStorage.removeItem(KEY);
  return initial();
}
function event(
  state: SimulationState,
  type: string,
  message: string,
  decision?: Decision,
) {
  const context = `${type} ${message}`.toLowerCase();
  const server = context.includes("drive") || context.includes("artifact") ? "drive-mock" : context.includes("gmail") || context.includes("email") || context.includes("send") ? "gmail-mock" : "—";
  const tool = context.includes("drive") ? "drive_get_document" : context.includes("send") ? "gmail_send_email" : context.includes("search") ? "gmail_search_emails" : context.includes("email") ? "gmail_get_email" : "—";
  const artifactId = message.match(/artifact-[a-z0-9-]+/i)?.[0] ?? "";
  state.audit.unshift({ id: id("EVT"), at: stamp(), date: new Date().toISOString().slice(0,10), principal: "demo-user", server, tool, approval: type.includes("APPROVAL") ? type.replace("APPROVAL_", "") : "—", execution: context.includes("not_started") ? "NOT_STARTED" : context.includes("succeeded") || context.includes("executed") ? "SUCCEEDED" : "—", threat: type.includes("THREAT") ? "Finding" : "—", artifactId, type, message, decision });
}
function decision(state: SimulationState, value: Decision) {
  state.decisions[value] += 1;
}
function pendingApproval(state: SimulationState, variant = "review") {
  const approved = variant === "approved";
  const artifactId =
    state.artifacts[state.artifacts.length - 1]?.id ??
    "artifact-confidential-001";
  const approval: Approval = {
    id: id("APR"),
    principal: "demo-user", server: "gmail-mock", tool: "gmail_send_email",
    operation: approved
      ? "Send reviewed expense extract"
      : "Send confidential attachment externally",
    arguments: { to: approved ? "reviewer@trustgate.example" : "external@example.net", subject: approved ? "Expense extract for review" : "Confidential statement", attachment_ids: artifactId },
    recipient: approved ? "reviewer@trustgate.example" : "external@example.net",
    expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
    artifactId,
    hash: approved ? "sha256:91c0…8bd4" : "sha256:4c31…a207",
    status: "PENDING",
    execution: "NOT_STARTED",
    reason:
      "External destination with a CONFIDENTIAL artifact; exact operation requires authenticated review.",
    created: stamp(),
  };
  state.approvals.unshift(approval);
  return approval;
}
export function runScenario(
  state: SimulationState,
  scenario: ScenarioId,
): SimulationState {
  const next = structuredClone(state);
  next.scenario = scenario;
  next.stepIndex = 9;
  next.invocations += 1;
  const title = scenarios.find((x) => x.id === scenario)?.title ?? scenario;
  event(
    next,
    "REQUEST_RECEIVED",
    `${title} submitted by verified demo principal.`,
  );
  event(
    next,
    "AUTHENTICATED",
    "Synthetic verified principal established; no model-supplied user_id is used.",
  );
  const requiredServer = scenario === "confidential-read" ? "Drive" : "Gmail";
  if (!next.connected[requiredServer]) {
    decision(next, "BLOCK");
    event(
      next,
      "SERVER_UNAVAILABLE",
      `${requiredServer} mock server is disabled; execution failed closed.`,
      "BLOCK",
    );
    next.results[scenario] =
      `BLOCK · ${requiredServer} mock server unavailable · no upstream execution.`;
    return next;
  }
  switch (scenario) {
    case "normal-search":
      decision(next, "ALLOW");
      event(
        next,
        "POLICY_DECISION",
        "Read-only search matched the synthetic allow rule.",
        "ALLOW",
      );
      event(
        next,
        "RESPONSE_INSPECTED",
        "Synthetic result inspected before returning to the model-facing caller.",
      );
      next.results[scenario] =
        "ALLOW · 3 synthetic messages returned after response inspection.";
      break;
    case "confidential-read": {
      decision(next, "ALLOW");
      const artifact: Artifact = {
        id: "artifact-drive-2048",
        name: "Q4 expense statement",
        classification: "CONFIDENTIAL",
        provenance: "Drive · drive_get_document · demo workspace",
        tainted: true,
        hash: "sha256:7f2e…44bc",
      };
      next.artifacts = [
        artifact,
        ...next.artifacts.filter((a) => a.id !== artifact.id),
      ];
      event(
        next,
        "DLP_REDACTION",
        "Synthetic PAN, phone, and account-like values redacted; artifact registered CONFIDENTIAL.",
      );
      event(
        next,
        "ARTIFACT_REGISTERED",
        `${artifact.id} · provenance and taint recorded.`,
      );
      next.results[scenario] =
        "ALLOW · 3 synthetic entities redacted · artifact-drive-2048 registered CONFIDENTIAL.";
      break;
    }
    case "malicious-email": {
      const threat = {
        id: id("THR"),
        severity: "HIGH",
        title: "Untrusted instruction in retrieved email",
        evidence:
          "Synthetic message asks the agent to reveal and externally send a confidential document.",
        at: stamp(),
      };
      next.threats.unshift(threat);
      event(
        next,
        "THREAT_SIGNAL",
        `${threat.id} flagged; content marked untrusted.`,
      );
      next.results[scenario] =
        "SIMULATED FINDING · Suspicious instruction flagged and marked untrusted. Detection is imperfect; policy remains the authorization boundary.";
      break;
    }
    case "confidential-send": {
      decision(next, "REQUIRE_APPROVAL");
      const approval = pendingApproval(next);
      event(
        next,
        "ARTIFACT_RESOLVED",
        `${approval.artifactId} · CONFIDENTIAL · external destination.`,
      );
      event(
        next,
        "APPROVAL_CREATED",
        `${approval.id} frozen; upstream execution NOT_STARTED.`,
        "REQUIRE_APPROVAL",
      );
      next.results[scenario] =
        `REQUIRE_APPROVAL · ${approval.id} frozen · Gmail send count unchanged (${next.sends}).`;
      break;
    }
    case "rejection": {
      let approval = next.approvals.find(
        (a) => a.status === "PENDING" && a.recipient === "external@example.net",
      );
      if (!approval) approval = pendingApproval(next);
      approval.status = "REJECTED";
      approval.execution = "NOT_STARTED";
      event(
        next,
        "APPROVAL_REJECTED",
        `${approval.id} rejected; Gmail send counter remains ${next.sends}.`,
      );
      next.results[scenario] =
        `REJECTED · execution NOT_STARTED · simulated upstream send count ${next.sends}.`;
      break;
    }
    case "approved-send": {
      decision(next, "REQUIRE_APPROVAL");
      const approval = pendingApproval(next, "approved");
      event(
        next,
        "APPROVAL_CREATED",
        `${approval.id} · separate exact operation frozen.`,
        "REQUIRE_APPROVAL",
      );
      approval.status = "APPROVED";
      event(
        next,
        "APPROVAL_APPROVED",
        `${approval.id} · authenticated synthetic reviewer approved the frozen operation.`,
      );
      approval.status = "CONSUMED";
      approval.execution = "SUCCEEDED";
      next.sends += 1;
      event(
        next,
        "APPROVAL_CONSUMED",
        `${approval.id} consumed once; frozen synthetic operation executed.`,
      );
      event(
        next,
        "EXECUTION_SUCCEEDED",
        `Simulated send count is ${next.sends}; no external service was contacted.`,
      );
      next.results[scenario] =
        `CONSUMED · SUCCEEDED · separate operation executed once · simulated send count ${next.sends}.`;
      break;
    }
  }
  return next;
}
const pipelineSteps = [
  "Verify authentication",
  "Resolve reviewed tool",
  "Inspect request arguments",
  "Resolve artifact identity",
  "Evaluate deterministic policy",
  "Freeze or review operation",
  "Control upstream execution",
  "Inspect model-facing response",
  "Persist sanitized audit",
];
export function stepScenario(
  state: SimulationState,
  scenario: ScenarioId,
): SimulationState {
  let next = structuredClone(state);
  if (next.scenario !== scenario) {
    next.scenario = scenario;
    next.stepIndex = 0;
  }
  if (next.stepIndex >= pipelineSteps.length) return next;
  const label = pipelineSteps[next.stepIndex];
  next.stepIndex += 1;
  if (next.stepIndex < pipelineSteps.length) {
    event(
      next,
      "PIPELINE_STEP",
      `Step ${String(next.stepIndex).padStart(2, "0")} · ${label}.`,
    );
    return next;
  }
  return runScenario(next, scenario);
}
export function runTest(
  state: SimulationState,
  testId: string,
): SimulationState {
  const next = structuredClone(state);
  next.testResults[testId] = "SIMULATED_PASS";
  event(
    next,
    "SIMULATED_TEST",
    `${testId} demonstration passed in local synthetic simulation. This is not a real Trust Gate verification.`,
  );
  return next;
}
export const testCases = [
  ["T01", "Missing/invalid/expired token", "Rejected before tool handler"],
  ["T02", "Normal permitted Gmail search", "Allowed through Trust Gate"],
  ["T03", "Unpermitted tool/operation", "Blocked; upstream counter unchanged"],
  [
    "T04",
    "Sensitive Drive document",
    "Required fields redacted before response",
  ],
  ["T05", "Inspector/DLP unavailable", "Raw result withheld; sanitized error"],
  [
    "T06",
    "Confidential artifact referenced by ID",
    "Classification/taint resolved",
  ],
  [
    "T07",
    "Tainted artifact sent externally",
    "REQUIRE_APPROVAL; no initial send",
  ],
  [
    "T08",
    "Reject pending external send",
    "Rejected; send counter remains zero",
  ],
  ["T09", "Approve exact frozen send", "Exact operation executes once"],
  [
    "T10",
    "Changed/expired/replayed approval",
    "Invalidated; no second execution",
  ],
  ["T11", "Cross-user access", "Denied by ownership checks"],
  [
    "T12",
    "Upstream timeout after possible side effect",
    "Unknown/reconciliation; no blind retry",
  ],
  ["T13", "Malicious initial tool description", "Not exposed before review"],
  ["T14", "Approved definition changes", "Quarantined; review required"],
  ["T15", "Missed tool-list notification", "Reconciliation detects drift"],
  ["T16", "Tool output contains secrets/PII", "Sanitized evidence only"],
  ["T17", "Policy engine unavailable", "Protected operation fails closed"],
  ["T18", "DLP unavailable", "Response withheld; protected write blocked"],
  [
    "T19",
    "Malicious email instruction",
    "Untrusted; cannot authorize follow-on call",
  ],
  ["T20", "Direct upstream bypass", "Outside Trust Gate protection boundary"],
] as const;
