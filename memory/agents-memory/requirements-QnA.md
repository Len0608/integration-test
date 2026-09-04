# Requirements Completeness Assessment

The requirements are classified as **Low Detail**.

The core intent is clear — build a Prometheus monitoring Universal Extension with basic auth, three monitoring actions (Query Metric, Check Alerts, Get Targets), and three output fields. This gives a solid foundation to build from.

However, many design decisions are still open: the Prometheus server URL is not mentioned at all, the query type for "Query Metric" is ambiguous (instant vs. range), the valid alert state options are undefined, and the exact content of each output field needs to be shaped. The questions below are a collaborative next step to fill in those decisions together.

---

# Platform Compatibility

The build environment confirms a Linux x86_64 host, making this a **Linux-only** target platform. All identified candidate modules are pure-Python, so no binary wheel constraints apply.

**Platform Compatibility from Requirements**: Undefined (not stated in requirements)
**Platform Compatibility Agreement**: Linux-only (confirmed from `environment.md` — Build Platform: Linux x86_64)

---

# Python Modules and Versions

## Researched Modules

**requests**
- **Module Purpose**: Industry-standard HTTP client for calling Prometheus REST API endpoints (`/api/v1/query`, `/api/v1/alerts`, `/api/v1/targets`)
- **Version**: 2.34.2
- **Type**: Pure Python

**httpx**
- **Module Purpose**: Modern HTTP client with similar API to requests, adds async capability (not needed here) and finer timeout control
- **Version**: 0.28.1 (stable series) — Note: PyPI also lists a pre-release `1.0.dev1`; this should NOT be used
- **Type**: Pure Python

**prometheus-api-client**
- **Module Purpose**: Higher-level Python wrapper for the Prometheus HTTP API, primarily focused on metrics queries
- **Version**: 0.7.2
- **Type**: Pure Python

**tabulate**
- **Module Purpose**: Formats tabular data into ASCII tables for human-readable STDOUT output (recommended by UAC architect notes with `tablefmt="rounded_outline"`)
- **Version**: 0.10.0
- **Type**: Pure Python

## Agreed Python Modules and Versions

*This section is a placeholder for later update once the User provides answers.*

| Module Name | Module Purpose | Version | Type |
|---|---|---|---|
| [To be confirmed] | HTTP Client | [To be confirmed] | Pure Python |
| tabulate | STDOUT table formatting | 0.10.0 | Pure Python |

---

# Question Rationale

The requirements provide a one-sentence description covering service name, authentication type, three action names with rough parameter names, and three output field names. This is enough to understand the goal, but leaves open: how the Prometheus server URL is provided, what query type "Query Metric" performs, what the valid values for "state" are, what each output field should contain, and how no-data scenarios are handled. Answering these 11 questions will make the requirements fully concrete for implementation analysis.

---

# Clarifying Questions for Requirements Refinement

## Critical Decision Path Questions

---

**Question 1**: Which Python HTTP client module should be used to call the Prometheus HTTP API?

- **Question Type**: New Discussion topic
- **Context & Resources**: The Prometheus server exposes a well-documented REST API at endpoints like `/api/v1/query`, `/api/v1/alerts`, and `/api/v1/targets`. An HTTP client module is the only Python library required for all three actions. Three options have been researched and verified as compatible:

  - **Option A — `requests==2.34.2`**: The most widely used Python HTTP library (30M+ weekly downloads). Pure-Python, synchronous, excellent documentation, and very stable API. No specialized Prometheus knowledge required — calls the API directly with simple `get()` calls. Recommended by UAC architect notes for web service integrations.

  - **Option B — `httpx==0.28.1`**: A modern alternative with a nearly identical API to requests. Adds finer-grained timeout control and encrypted client certificate support — neither of which is needed for this use case. The pre-release version `1.0.dev1` is available on PyPI but should **not** be used; pin to `0.28.1`.

  - **Option C — `prometheus-api-client==0.7.2`**: A higher-level Python wrapper for Prometheus. It simplifies metric queries but has limited or no coverage for the alerts and targets API endpoints needed by Check Alerts and Get Targets. It would add a dependency without covering all required actions.

  Regardless of HTTP client choice, `tabulate==0.10.0` will also be included for formatting tabular STDOUT output (metric results, alert lists, target tables).

  Further reading:
  - [requests documentation](https://requests.readthedocs.io/en/latest/)
  - [httpx documentation](https://www.python-httpx.org/)
  - [Prometheus HTTP API reference](https://prometheus.io/docs/prometheus/latest/querying/api/)

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — `requests==2.34.2`** plus `tabulate==0.10.0`. Requests is the simplest, most stable, and most widely understood choice for synchronous Prometheus API calls. The Prometheus HTTP API is straightforward enough that no wrapper library is needed.
- **Rationale**: Requests has a near-universal install base and familiar API. Using it directly against the Prometheus HTTP API avoids adding a specialized wrapper (prometheus-api-client) that doesn't fully cover all three required actions.
- **Trade-offs**: Choosing requests over httpx means no async capability (not needed here) and slightly less fine-grained timeout control. Choosing requests over prometheus-api-client means slightly more code per API call, but full control over all endpoints.
- **Requirement Impact**: None — no adjustments needed.
- **User's Answer**: Option A — `requests==2.34.2` + `tabulate==0.10.0`

---

**Question 2**: The UAC architect guidelines recommend implementing a maximum of 2 actions in the initial version. The requirements define 3 actions. Which 2 should be implemented first?

- **Question Type**: New Discussion topic
- **Context & Resources**: The UAC architect notes state: *"Do not propose more than two actions for the initial implementation. If multiple actions are inside the requirements then propose to implement 2 max actions as a start."* This Start Small approach reduces initial complexity and allows earlier testing and feedback. The third action can be added in a follow-up version.

  The three requested actions and their business value:
  - **Query Metric**: Executes a PromQL expression against the Prometheus query API (`/api/v1/query` or `/api/v1/query_range`). Core Prometheus functionality — most essential for automation workflows that check thresholds or retrieve metric values.
  - **Check Alerts**: Retrieves currently active alerts from the Prometheus alerts API (`/api/v1/alerts`), filtered by alert name and state. Directly useful for monitoring workflows that need to know if specific alerts are firing.
  - **Get Targets**: Retrieves scrape target health from the Prometheus targets API (`/api/v1/targets`), filtered by job label. Useful for infrastructure health checks.

  Options:
  - **Option A — Query Metric + Check Alerts**: Covers the two most common Prometheus monitoring automation use cases: threshold evaluation and active alert detection.
  - **Option B — Query Metric + Get Targets**: Covers metric querying and infrastructure target health.
  - **Option C — Check Alerts + Get Targets**: Covers alerting and target health without metric querying.
  - **Option D — All 3 actions**: Implement all three immediately, departing from the Start Small recommendation.

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — Query Metric + Check Alerts**. These two actions cover the most operationally important scenarios: "Is this metric above my threshold?" and "Is this alert currently firing?" Get Targets can be added in version 2.
- **Rationale**: Query Metric is the foundational Prometheus capability. Check Alerts provides immediate visibility into the alerting state, which is the most common monitoring automation need. Get Targets is valuable but secondary.
- **Trade-offs**: Deferring Get Targets means target health checks won't be available in v1. Adding it later is low-risk since it uses the same HTTP client and auth pattern.
- **Requirement Impact**: Get Targets action (with `job` input and `target_health` output) will be deferred to a later version. The `target_health` output-only field will not be included in v1.
- **User's Answer**: Option A — Query Metric + Check Alerts

---

**Question 3**: The requirements do not mention how the Prometheus server URL is configured. Where should users specify the Prometheus server base URL (e.g., `http://prometheus.mycompany.com:9090`)?

- **Question Type**: New Discussion topic
- **Context & Resources**: The Prometheus URL is a per-task configuration value — different tasks may target different Prometheus instances (production, staging, DR). It is not a global or environment-level setting. This URL is required for every API call.

  Options:
  - **Option A — Text Field in the task definition** *(Recommended)*: Users specify the full base URL directly in the task form. Example: `http://prometheus.monitoring.svc:9090`. This is the standard approach for connection parameters in UAC extensions.
  - **Option B — Environment variable (`UE_PROMETHEUS_URL`)**: The URL is set at the agent level and shared across all Prometheus tasks on that agent. Less flexible — assumes all tasks on a given agent target the same Prometheus instance.
  - **Option C — Both (Text Field with fallback to environment variable)**: Allows per-task override while also supporting agent-level default. Adds implementation complexity without significant benefit for most deployments.

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — Text Field**. Most UAC deployments will have tasks pointing to different Prometheus endpoints (e.g., per environment), making per-task configuration the most flexible and transparent choice.
- **Rationale**: URL configuration is a commonly tuned parameter — it varies by task. The UAC architect notes recommend environment variables only for parameters "not commonly tuned" with "sensible defaults."
- **Trade-offs**: Option A requires users to specify the URL in every task definition; Option B makes tasks simpler but inflexible. For production use cases where multiple Prometheus instances exist, Option A is significantly more useful.
- **Requirement Impact**: Add a new required input field: `Prometheus URL` (Text Field). Suggested label: "Prometheus URL". Suggested hint: "Base URL of the Prometheus server. Example: http://prometheus.mycompany.com:9090"
- **User's Answer**: Option A — Text Field in the task definition

---

## Query Metric Action Questions

---

**Question 4**: The requirements list `promql_expression` and `time_range` as inputs for the Query Metric action. Should this action perform an **instant query** (current value at a single point in time) or a **range query** (time series over a period)?

- **Question Type**: Clarification on existing requirement
- **Context & Resources**: Prometheus exposes two distinct query endpoints with different use cases:

  **Instant query** (`/api/v1/query`):
  - Parameters: `query` (PromQL expression), optional `time` (defaults to now)
  - Returns: The current value(s) of the metric at a single moment
  - Best for: Threshold checks ("Is CPU > 80% right now?"), single-value retrievals
  - Output: Simple — one value per metric series

  **Range query** (`/api/v1/query_range`):
  - Parameters: `query`, `start`, `end`, `step` (resolution interval)
  - Returns: A time series with one data point per step interval over the specified period
  - Best for: Trend analysis, detecting patterns over time
  - Output: Potentially many values — a 1-hour window at 1-minute resolution produces 60 data points per series

  The `time_range` parameter in the requirements suggests range query intent. However, for UAC automation (where the goal is often threshold evaluation or monitoring checks), instant queries are simpler and sufficient.

  Options:
  - **Option A — Instant query only**: Uses `/api/v1/query`. The `time_range` parameter would be removed or replaced with an optional `evaluation_time` offset. Simplest to implement and produce compact output.
  - **Option B — Range query only**: Uses `/api/v1/query_range`. The `time_range` input becomes a duration (e.g., "1h") applied relative to now. Returns multiple values per metric series.
  - **Option C — Both, selectable via a Choice field**: A "Query Mode" field lets users pick "Instant" or "Range" at task definition time. Most flexible, but adds UI complexity and two sets of conditional fields.

  Further reading: [Prometheus Querying API](https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries)

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — Instant query only**. For UAC automation workflows, instant queries answer the most common question: "What is the current value of this metric?" They produce compact output (one value per series), are simpler to implement, and avoid the need for a `step` parameter. The `time_range` requirement may have been intended as an optional evaluation time offset, or can be simplified away.
- **Rationale**: Range queries return time series data which is better suited for dashboards (Grafana) than automation tasks. For monitoring automation — checking if a metric exceeds a threshold, retrieving the latest value — instant queries are ideal and produce output small enough to fit in extension output fields.
- **Trade-offs**: Choosing instant query means users cannot retrieve historical trend data through this action. If trend analysis is a genuine use case, Option C (both modes) would be needed, at the cost of additional form fields and implementation complexity.
- **Requirement Impact**: If Option A is chosen, the `time_range` input can be replaced with an optional `evaluation_time` field (e.g., RFC 3339 timestamp or Unix timestamp, defaulting to "now"). If Option B or C, `time_range` becomes a duration string plus a `step` field.
- **User's Answer**: Option A — Instant query only

---

**Question 5**: For the `promql_expression` input field — should users also be able to specify an optional **evaluation timestamp** (to query the metric value at a specific past point in time), or should the query always evaluate against the current server time?

- **Question Type**: New Discussion topic
- **Context & Resources**: The Prometheus instant query endpoint (`/api/v1/query`) accepts an optional `time` parameter that specifies the evaluation timestamp. If omitted, the query evaluates at the current server time.

  Use cases for a specific evaluation time:
  - "What was this metric's value at 14:00 yesterday?" (audit, debugging)
  - "Evaluate the PromQL expression at a known reference time for comparison"

  For most automation monitoring use cases (threshold checks, current state), using the current server time is sufficient and simpler.

  Options:
  - **Option A — Always use current server time** *(Recommended)*: No timestamp field needed. Simpler task form.
  - **Option B — Optional evaluation time field**: An optional Text Field for a timestamp (e.g., RFC 3339 like `2026-09-04T10:00:00Z` or Unix epoch). If empty, defaults to current time.

- **Question Dependencies**: Compatible with Q4 Option A (Instant query). If Q4=Option B (Range query), this question is replaced by the time range definition question.
- **Recommended Answer**: **Option A — Always use current server time**. For monitoring automation, the current state is almost always what matters. Adding an optional timestamp field increases complexity without clear benefit for the core use case.
- **Rationale**: Simplicity. The vast majority of monitoring automation scenarios require "right now" metrics. Historical point-in-time queries are better served by dashboards or dedicated analytics tools.
- **Trade-offs**: Users cannot perform historical point-in-time queries. If this use case emerges, the field can be added in a later version.
- **Requirement Impact**: The `time_range` input field from the requirements can be removed. Final input for Query Metric: `promql_expression` (Text Field / Large Text Field) only.
- **User's Answer**: Option A — Always use current server time

---

## Check Alerts Action Questions

---

**Question 6**: For the Check Alerts action, how should the `alertname` and `state` inputs work as filters, and what should the valid state options be?

- **Question Type**: Clarification on existing requirement
- **Context & Resources**: The Prometheus alerts API (`/api/v1/alerts`) returns all currently active alerts. It does not support server-side filtering by alert name or state — filtering happens in the extension after fetching the full list.

  Prometheus alert states (as defined in the Prometheus API):
  - **`firing`**: The alert condition has been met for the required duration (the "for" clause in alert rules). The alert is actively firing.
  - **`pending`**: The alert condition is met but the "for" duration has not elapsed yet. The alert is warming up.
  - *(inactive alerts are not returned by the alerts endpoint — only pending and firing alerts appear)*

  **For the `alertname` input**:
  - If a value is provided: filter results to alerts whose `alertname` label matches exactly.
  - If empty: return all alerts regardless of name.
  - Field type: Text Field (optional, no default)

  **For the `state` input — options for Choice Field values**:
  - **Option A — Three choices: "All", "Firing", "Pending"** *(Recommended)*: "All" returns both firing and pending alerts. "Firing" filters to actively firing alerts only. "Pending" filters to alerts in the warming-up phase. A default of "All" works well for broad visibility.
  - **Option B — Two choices: "Firing", "Pending"** (no "All"): Forces users to always specify a state. Less convenient for dashboards or broad monitoring tasks.
  - **Option C — Free text input**: Allows any value but risks typos and lacks UX guidance.

  Further reading: [Prometheus Alerts API](https://prometheus.io/docs/prometheus/latest/querying/api/#alerts)

- **Question Dependencies**: Compatible only if Q2 includes "Check Alerts" as a selected action.
- **Recommended Answer**: **Option A — Choice field with "All", "Firing", "Pending"**. The `alertname` should be an optional Text Field (empty = no filter). The `state` should be a standard Choice Field with these three values. Default state: "All".
- **Rationale**: A choice field prevents invalid state values and guides users. Including "All" as a default makes the action useful immediately without requiring a state filter for general monitoring tasks.
- **Trade-offs**: None significant. If the user always wants just firing alerts, they set the default to "Firing" in the task definition.
- **Requirement Impact**: `alertname` maps to an optional Text Field. `state` maps to a Choice Field with values: "all" / "firing" / "pending". Labels: "Alert Name" (optional hint: "Filter by alert name. Leave empty to return all alerts") and "Alert State Filter" with default "All".
- **User's Answer**: Option A — Choice field with "All", "Firing", "Pending". alertname is optional Text Field.

---

## Output Design Questions

---

**Question 7**: The requirements define three output fields: `metric_values`, `alert_state`, and `target_health`. What should each output-only field display in the UAC task UI?

- **Question Type**: Clarification on existing requirement
- **Context & Resources**: UAC output-only fields appear in the task execution details and task list view. They are best used for short, human-readable summaries. Full detailed data (all metric values, full alert JSON) should go to STDOUT and Extension Output rather than these fields.

  UAC architect notes: *"2–3 fields are suitable for most cases. Choose the most important information to be displayed for best User Experience. Do not store large information on Output Only fields."*

  Based on Q2 (two initial actions: Query Metric and Check Alerts), `target_health` will not be in v1.

  **For `metric_values` (Query Metric action output)**:
  - **Option A — Series count + value range**: e.g., `"3 series, values: 0.42–0.85"` — gives a quick overview of how many metric series matched and their value spread.
  - **Option B — First series name + value**: e.g., `"node_cpu_seconds_total{mode='idle'}: 0.85"` — most relevant when a single metric series is expected.
  - **Option C — Total result count only**: e.g., `"5 series returned"` — minimal, leaves detail to STDOUT.

  **For `alert_state` (Check Alerts action output)**:
  - **Option A — Count summary by state**: e.g., `"3 firing, 1 pending"` or `"No active alerts"` — immediately informative about overall alerting health.
  - **Option B — State of a named alert**: e.g., `"HighCPU: firing"` — most useful when filtering to a specific alertname.
  - **Option C — Total alert count**: e.g., `"4 alerts found"` — minimal.

  Note: Since alertname is optional, the output field must handle both cases (single named alert and all-alerts queries).

- **Question Dependencies**: Compatible only if Q2 includes the respective actions. `target_health` output is deferred per Q2 recommendation.
- **Recommended Answer**:
  - `metric_values`: **Option A — Series count + value range** (e.g., `"3 series, values: 0.42–0.85"`). Full metric data goes to STDOUT and Extension Output.
  - `alert_state`: **Option A — Count summary by state** (e.g., `"2 firing, 0 pending"` or `"No active alerts"`). This is useful regardless of whether alertname filter is applied.
- **Rationale**: Summary counts and ranges are always meaningful regardless of the PromQL expression used or the alert filter applied. They allow at-a-glance assessment in the task list view without storing large datasets in the UAC database.
- **Trade-offs**: Summaries lose detail (exact metric labels, specific alert names). Full detail is available via STDOUT and Extension Output for downstream processing.
- **Requirement Impact**: `metric_values` → Text Field, output-only. `alert_state` → Text Field, output-only. Both use `defaultListView: true` so they appear in the task list. `target_health` deferred to v2.
- **User's Answer**: metric_values = Option A (series count + value range). alert_state = Option A (count summary by state).

---

**Question 8**: Should STDOUT output use **ASCII table format** or **plain text key-value format** when displaying metric results and alert details?

- **Question Type**: New Discussion topic
- **Context & Resources**: STDOUT is the human-readable output channel visible in the UAC UI. For tabular data (metrics with multiple label dimensions, multiple alerts), formatting matters for readability.

  The UAC architect notes specifically recommend: *"ASCII Table format is preferable when information can be printed nicely in rows or in columns using well known python libraries"* and *"Use `tablefmt='rounded_outline'` as it provides a really nice output."*

  `tabulate==0.10.0` has been included as a recommended dependency for exactly this purpose.

  Example ASCII table output for metric results:
  ```
  ╭──────────────────────────────────────────┬────────┬──────────────────────────╮
  │ Metric                                   │ Value  │ Timestamp                │
  ├──────────────────────────────────────────┼────────┼──────────────────────────┤
  │ node_cpu_seconds_total{mode="idle"}      │ 0.85   │ 2026-09-04T10:00:00Z     │
  │ node_cpu_seconds_total{mode="user"}      │ 0.12   │ 2026-09-04T10:00:00Z     │
  ╰──────────────────────────────────────────┴────────┴──────────────────────────╘
  ```

  Example ASCII table output for alerts:
  ```
  ╭────────────────┬─────────┬─────────────────────────────╮
  │ Alert Name     │ State   │ Active Since                │
  ├────────────────┼─────────┼─────────────────────────────┤
  │ HighCPUAlert   │ firing  │ 2026-09-04T09:45:00Z        │
  │ DiskSpaceWarn  │ pending │ 2026-09-04T09:58:00Z        │
  ╰────────────────┴─────────┴─────────────────────────────╘
  ```

  Options:
  - **Option A — ASCII table using tabulate** *(Recommended)*
  - **Option B — Plain text key-value format**: Simpler, avoids the tabulate dependency, but less readable for multiple results.

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — ASCII table using tabulate with `tablefmt="rounded_outline"`**, in alignment with UAC architect notes. `tabulate==0.10.0` is already included in the module selection.
- **Rationale**: Tabular data like metric labels+values and alert name+state+timestamp is significantly more readable as a table. The `tabulate` library is lightweight (pure-Python, no further dependencies), well-maintained, and specifically recommended by the architect notes.
- **Trade-offs**: Adds `tabulate` as a dependency (lightweight, pure-Python, no concern). The alternative (key-value text) is less readable when results contain multiple series or alerts.
- **Requirement Impact**: `tabulate==0.10.0` confirmed as a required dependency.
- **User's Answer**: Option A — ASCII table using tabulate

---

**Question 9**: Should the extension output include **verbosity control** (letting users choose what appears in STDOUT and Extension Output), or should all available data always be included?

- **Question Type**: New Discussion topic
- **Context & Resources**: The UAC Output Verbosity Selection Pattern allows users to control what data is included in STDOUT and Extension Output at task definition time. This is important because:
  1. Prometheus queries can return many metric series — output can grow large.
  2. STDOUT and Extension Output are stored in the UAC database; excessive data can strain storage.
  3. The UAC Large Output Safety Net Pattern recommends capping output via `UE_MAX_OUTPUT_RECORDS` (default 100).

  However, for a simple monitoring extension with typical single-metric queries and small alert lists, output size may not be a concern in practice.

  Options:
  - **Option A — Always include all results, with `UE_MAX_OUTPUT_RECORDS` cap** *(Recommended)*: No output choice field needed. The environment variable `UE_MAX_OUTPUT_RECORDS` (default: 100) limits the number of metric series or alerts printed. This covers the safety net without adding UI fields.
  - **Option B — Output verbosity choice field**: A multi-select Choice Field lets users choose what to include (e.g., "Show Metric Details", "Show Alert Annotations", "Show Summary Only"). Adds flexibility but also UI complexity.

  Further reading: UAC architect notes — *Large Output Safety Net Pattern*, *Output Verbosity Selection Pattern*

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — Always include all results with `UE_MAX_OUTPUT_RECORDS` cap**. For a monitoring extension with typically small result sets, a simple cap is sufficient. A verbosity control field can be added later if users request it.
- **Rationale**: Start Small. Prometheus monitoring tasks typically query specific metrics or check specific alerts — result sets are small. Adding an output verbosity choice field in v1 adds form complexity without clear benefit for most use cases.
- **Trade-offs**: No user control over output granularity in v1. If queries return many series (e.g., a PromQL expression matching 200 metric series), the cap truncates output with a note. Users needing the full dataset can use the Extension Output JSON.
- **Requirement Impact**: Add `UE_MAX_OUTPUT_RECORDS` environment variable support (default: 100). When output is truncated, include a note in STDOUT and a `truncated` flag in Extension Output metadata.
- **User's Answer**: Option A — Always include all results with `UE_MAX_OUTPUT_RECORDS` cap

---

## Functional Behavior Questions

---

**Question 10**: What should happen when an action returns **no results** (e.g., the PromQL expression matches no metric series, or no alerts match the filter)?

- **Question Type**: New Discussion topic
- **Context & Resources**: Prometheus API calls can legitimately return empty results — this is not an API error. For example:
  - `Query Metric`: A PromQL expression that matches no current metric series returns an empty result set. This happens when the metric doesn't exist or all series have expired.
  - `Check Alerts`: No active alerts matching the filter means the alerting system is healthy (desired state for a monitoring workflow).

  The behavior of the extension in these cases affects how downstream UAC workflow tasks behave.

  Options:
  - **Option A — Empty results = Success (exit code 0)** *(Recommended)*: The extension completes successfully with a message like `"Success: No active alerts found"` or `"Success: No metric series matched the expression"`. Downstream tasks can branch based on the output field values.
  - **Option B — Empty results = Failure (exit code 1)**: Useful when the metric or alert is expected to exist and absence indicates a problem. However, this assumption is not always valid — no firing alerts is often the desired state.
  - **Option C — Configurable behavior via Choice field**: A "On No Results" field lets users choose "Succeed" or "Fail" per task definition. Adds flexibility but also complexity.

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — Empty results = Success (exit code 0)**. The absence of firing alerts is typically the desired state in monitoring. Absence of metric data may indicate a scraping issue, but that is better detected via the target health check (v2 action) rather than treating empty PromQL results as failures.
- **Rationale**: For monitoring automation, "no active alerts" is the healthy state, not an error. Treating empty results as failures would cause false-positive task failures in healthy environments. Users needing "at least one result" semantics can add a validation step in the workflow.
- **Trade-offs**: Users who expect a specific metric to always exist won't get automatic failure notification — they'd need to add a workflow conditional check. This is a more explicit and maintainable pattern than a buried "fail on empty" flag.
- **Requirement Impact**: `status_description` examples: `"Success: No active alerts matching the filter"`, `"Success: 0 metric series returned for the expression"`. Return code: 0 for all no-results scenarios.
- **User's Answer**: Option A — Empty results = Success (exit code 0)

---

## Security & Configuration Questions

---

**Question 11**: How should **SSL/TLS certificate verification** be handled when connecting to the Prometheus server?

- **Question Type**: New Discussion topic
- **Context & Resources**: Prometheus is commonly deployed with self-signed or internal CA-signed TLS certificates, especially in on-premise environments. The `requests` library verifies SSL certificates by default, which is the correct behavior for security. However, this causes connection failures when the server uses a self-signed certificate and no custom CA bundle is configured on the agent.

  The `requests` library already recognizes two well-established environment variables for CA bundle configuration — no new variables are needed for the standard use case:
  - **`REQUESTS_CA_BUNDLE`**: Path to a custom CA bundle file or directory. Setting this allows `requests` to verify certificates signed by an internal CA.
  - **`CURL_CA_BUNDLE`**: Alternative, also recognized by `requests`.

  For the case where verification must be completely disabled (non-production, dev environments with no valid cert):

  Options:
  - **Option A — Verify by default; env var `UE_SSL_VERIFY=false` to disable** *(Recommended)*: SSL verification is on by default (secure). Setting `UE_SSL_VERIFY=false` at the agent level disables verification for all Prometheus tasks on that agent. This is an environment-level setting appropriate for an env var.
  - **Option B — Boolean field "Verify SSL" in the task definition**: Per-task SSL control. More visible but adds a form field to every task — appropriate if different Prometheus instances on the same agent have different cert situations.
  - **Option C — Always verify, no option to disable**: Strictest security. Users with self-signed certs must configure `REQUESTS_CA_BUNDLE` — cannot disable verification.

  Further reading: [requests SSL documentation](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification)

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — Verify by default; `UE_SSL_VERIFY=false` env var to disable**. SSL verification is on by default for production safety. The `REQUESTS_CA_BUNDLE` env var handles the common internal CA scenario. `UE_SSL_VERIFY=false` provides an escape hatch for development environments.
- **Rationale**: SSL verification is an agent-level (not task-level) setting — the same Prometheus server always has the same certificate. An environment variable is the right abstraction. A Boolean field would add form noise for the majority of users who never need to change it.
- **Trade-offs**: No per-task SSL control. If tasks on the same agent target both a verified Prometheus and an unverified one, this approach won't work — Option B (Boolean field) would be needed in that case.
- **Requirement Impact**: Add `UE_SSL_VERIFY` env var support. Document `REQUESTS_CA_BUNDLE` as the standard mechanism for custom CA bundles.
- **User's Answer**: Option A — Verify by default; `UE_SSL_VERIFY=false` env var to disable

---

**Question 12**: Should the **HTTP connection timeout** for Prometheus API calls be user-configurable, and if so, through what mechanism?

- **Question Type**: New Discussion topic
- **Context & Resources**: Prometheus API calls on a healthy local network are fast (typically <1s). However, network issues, server overload, or complex PromQL expressions on large datasets can cause slow responses. Without a timeout, the extension could hang indefinitely.

  The UAC architect notes recommend: *"Be in favor of environment variables for input parameters that are not commonly tuned and/or have sensible defaults like HTTP Client Timeouts (`UE_HTTP_TIMEOUT`)"*.

  Options:
  - **Option A — Environment variable `UE_HTTP_TIMEOUT` with default 30 seconds** *(Recommended)*: Sensible default covers most cases. Operators can tune it at the agent level without changing task definitions.
  - **Option B — Integer field in the task definition**: Per-task timeout control. Useful if queries vary greatly in expected execution time, but adds a field to the form.
  - **Option C — Hard-coded timeout (no configuration)**: Simplest, but inflexible.

- **Question Dependencies**: None
- **Recommended Answer**: **Option A — `UE_HTTP_TIMEOUT` environment variable, default 30 seconds**. This aligns exactly with the UAC architect notes recommendation and is appropriate for a parameter that rarely needs tuning.
- **Rationale**: A 30-second default is generous enough for complex PromQL queries while still protecting against hangs. Most users will never need to change it. Environment variable configuration avoids cluttering the task form with operational parameters.
- **Trade-offs**: No per-task timeout granularity. If a specific query is expected to be slow (complex PromQL over months of data), the agent-level `UE_HTTP_TIMEOUT` value must be increased for all Prometheus tasks on that agent.
- **Requirement Impact**: Add `UE_HTTP_TIMEOUT` env var support. Default: 30 seconds.
- **User's Answer**: Option A — `UE_HTTP_TIMEOUT` environment variable with default 30 seconds
