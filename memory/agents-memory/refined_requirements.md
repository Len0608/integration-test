# Universal Extension Requirements (Refined)

**Extension Name:** Prometheus Monitoring
**Original Generated:** Not recorded in source documents
**Refined:** 2026-09-04
**Agent_id:** Not specified
**Requirements Completeness:** High Detail
**Target Platform:** Linux

---

# Table of Contents

1. [Overview](#1-overview)
2. [Actions](#2-actions)
   - 2.1 [Query Metric](#21-query-metric)
   - 2.2 [Check Alerts](#22-check-alerts)
3. [Input Requirements](#3-input-requirements)
   - 3.1 [Connection Parameters](#31-connection-parameters)
   - 3.2 [Query Metric Fields](#32-query-metric-fields)
   - 3.3 [Check Alerts Fields](#33-check-alerts-fields)
4. [Output Requirements](#4-output-requirements)
   - 4.1 [On Success](#41-on-success)
   - 4.2 [On Error](#42-on-error)
5. [Authentication Requirements](#5-authentication-requirements)
6. [Environment Variables](#6-environment-variables)
7. [Operational Behavior](#7-operational-behavior)
8. [Implementation Notes](#8-implementation-notes)
   - 8.1 [Python Compatibility](#81-python-compatibility)
   - 8.2 [Target Platform](#82-target-platform)
   - 8.3 [Third-Party Services and Tools](#83-third-party-services-and-tools)
   - 8.4 [Error Handling](#84-error-handling)
   - 8.5 [Resource Cleanup](#85-resource-cleanup)
9. [Requirements Summary](#9-requirements-summary)
10. [Document Change History](#10-document-change-history)
11. [References](#11-references)

---

# 1. Overview

This document specifies the requirements for the Prometheus Monitoring Universal Extension.

**Integration Purpose:** The extension enables UAC automation workflows to interact with a Prometheus monitoring server by executing PromQL instant queries to retrieve current metric values, and by querying active alerts filtered by name and state. It provides structured output for downstream workflow branching and human-readable STDOUT for task execution review.

---

# 2. Actions

## 2.1 Query Metric

**Functional Requirements:**

1. The action must execute a user-supplied PromQL expression as an instant query against the Prometheus HTTP API endpoint `/api/v1/query`.
2. The query must be evaluated at the current server time; no user-configurable evaluation timestamp is required.
3. The action must return all matching metric series up to the limit defined by `UE_MAX_OUTPUT_RECORDS`.
4. When no metric series match the PromQL expression, the action must complete successfully with exit code 0.
5. The `metric_values` output-only field must display a summary in the format `"<N> series, values: <min>–<max>"` where N is the count of returned series and min/max are the observed value range. When no series are returned, the field must display `"0 series returned"`.
6. STDOUT must display metric results as an ASCII table with columns: Metric, Value, Timestamp.
7. When results are truncated by `UE_MAX_OUTPUT_RECORDS`, STDOUT must include a note indicating truncation and the total number of available series.
8. The Extension Output must be a JSON object containing the action name, PromQL expression, result count, a truncation flag, and the array of metric result objects.

## 2.2 Check Alerts

**Functional Requirements:**

1. The action must retrieve all currently active alerts from the Prometheus HTTP API endpoint `/api/v1/alerts`.
2. Filtering by alert name and alert state must be performed by the extension after fetching the full alerts list from Prometheus (Prometheus does not support server-side filtering on this endpoint).
3. When an alert name filter is provided, the action must return only alerts whose `alertname` label matches the provided value exactly.
4. When no alert name filter is provided, the action must return all alerts regardless of name.
5. The action must filter alerts by state according to the selected state filter option: "All" returns both firing and pending alerts; "Firing" returns only firing alerts; "Pending" returns only pending alerts.
6. The action must return all matching alerts up to the limit defined by `UE_MAX_OUTPUT_RECORDS`.
7. When no alerts match the applied filters, the action must complete successfully with exit code 0.
8. The `alert_state` output-only field must display a count summary in the format `"<N> firing, <M> pending"`. When no alerts match, it must display `"No active alerts"`.
9. STDOUT must display alert results as an ASCII table with columns: Alert Name, State, Active Since.
10. When results are truncated by `UE_MAX_OUTPUT_RECORDS`, STDOUT must include a note indicating truncation and the total number of available alerts.
11. The Extension Output must be a JSON object containing the action name, the applied filters, total found count, firing count, pending count, a truncation flag, and the array of alert objects.

> **Note:** The Get Targets action (originally requested with `job` input and `target_health` output) is deferred to a future version (v2). It will not be implemented in this version.

---

# 3. Input Requirements

## 3.1 Connection Parameters

These fields apply to all actions.

- **Prometheus URL** (Text Field, required): The base URL of the Prometheus server, including scheme, host, and port.
  - Example: `http://prometheus.mycompany.com:9090`
  - Applicability: Query Metric, Check Alerts
  - Default Value: None

- **Credential** (Credential Field, required): A UAC Basic Authentication credential containing username and password for authenticating to the Prometheus server.
  - Applicability: Query Metric, Check Alerts
  - Default Value: None

## 3.2 Query Metric Fields

- **PromQL Expression** (Large Text Field, required): A valid PromQL expression to evaluate against the Prometheus server.
  - Example: `node_cpu_seconds_total{mode="idle"}`
  - Applicability: Query Metric only
  - Default Value: None

## 3.3 Check Alerts Fields

- **Alert Name** (Text Field, optional): Filter results to alerts whose `alertname` label matches this value exactly. When left empty, all alerts are returned regardless of name.
  - Example: `HighCPUAlert`
  - Applicability: Check Alerts only
  - Default Value: None (empty — no filter applied)

- **Alert State Filter** (Choice Field, required): Filters returned alerts by their current state.
  - Available options:
    - `All` — returns both firing and pending alerts
    - `Firing` — returns only actively firing alerts
    - `Pending` — returns only alerts in the pending (warming-up) phase
  - Default presented option: `All`
  - Applicability: Check Alerts only

---

# 4. Output Requirements

## 4.1 On Success

**Return code:** 0

**Output-only fields:**

| Field Name | Type | Description | Applies To |
|---|---|---|---|
| `metric_values` | Text Field (output-only) | Summary of metric query results | Query Metric |
| `alert_state` | Text Field (output-only) | Summary of alert counts by state | Check Alerts |

Both output-only fields must be configured with `defaultListView: true` so they are visible in the UAC task list view.

**Status description examples:**

- Query Metric (results found): `"Success: 3 series returned for the expression"`
- Query Metric (no results): `"Success: 0 metric series returned for the expression"`
- Check Alerts (alerts found): `"Success: 2 firing, 0 pending alerts matched the filter"`
- Check Alerts (no results): `"Success: No active alerts matching the filter"`

**STDOUT output:**

Query Metric — ASCII table format using `tabulate` with `tablefmt="rounded_outline"`:

```
╭──────────────────────────────────────────┬────────┬──────────────────────────╮
│ Metric                                   │ Value  │ Timestamp                │
├──────────────────────────────────────────┼────────┼──────────────────────────┤
│ node_cpu_seconds_total{mode="idle"}      │ 0.85   │ 2026-09-04T10:00:00Z     │
│ node_cpu_seconds_total{mode="user"}      │ 0.12   │ 2026-09-04T10:00:00Z     │
╰──────────────────────────────────────────┴────────┴──────────────────────────╯
```

Check Alerts — ASCII table format using `tabulate` with `tablefmt="rounded_outline"`:

```
╭────────────────┬─────────┬─────────────────────────────╮
│ Alert Name     │ State   │ Active Since                │
├────────────────┼─────────┼─────────────────────────────┤
│ HighCPUAlert   │ firing  │ 2026-09-04T09:45:00Z        │
│ DiskSpaceWarn  │ pending │ 2026-09-04T09:58:00Z        │
╰────────────────┴─────────┴─────────────────────────────╯
```

When results are truncated, a note must appear below the table indicating how many records were omitted.

**Extension Output (JSON):**

Query Metric:
```json
{
  "action": "query_metric",
  "promql_expression": "<expression>",
  "result_count": 3,
  "truncated": false,
  "results": [
    {
      "metric": {"__name__": "node_cpu_seconds_total", "mode": "idle"},
      "value": 0.85,
      "timestamp": "2026-09-04T10:00:00Z"
    }
  ]
}
```

Check Alerts:
```json
{
  "action": "check_alerts",
  "alert_name_filter": "HighCPUAlert",
  "state_filter": "all",
  "total_found": 2,
  "firing_count": 2,
  "pending_count": 0,
  "truncated": false,
  "alerts": [
    {
      "alertname": "HighCPUAlert",
      "state": "firing",
      "active_since": "2026-09-04T09:45:00Z",
      "labels": {},
      "annotations": {}
    }
  ]
}
```

When output is truncated, the `truncated` field must be `true`.

**Success Criteria:**

1. The Prometheus API returns an HTTP 2xx response.
2. The PromQL expression is syntactically valid (no 400 error from Prometheus).
3. Results (including empty result sets) are successfully parsed and formatted.
4. Output-only fields are populated with the appropriate summary.
5. Extension Output contains valid JSON conforming to the structure above.

## 4.2 On Error

**Return code:** 1 for all failure scenarios.

**Failure Scenarios:**

| Scenario | Description | Root Causes | Status Description Pattern |
|---|---|---|---|
| Connection Error | Unable to reach the Prometheus server | Server unreachable, DNS failure, incorrect URL | `"Error: Unable to connect to Prometheus server at <url>: <detail>"` |
| Authentication Error | Prometheus server rejects the credentials | Invalid username or password (HTTP 401/403) | `"Error: Authentication failed for Prometheus server at <url> (HTTP <code>)"` |
| SSL/TLS Error | Certificate verification failed | Self-signed cert, expired cert, CA not trusted | `"Error: SSL certificate verification failed for <url>: <detail>"` |
| Timeout Error | The API request exceeded the timeout limit | Slow server, complex PromQL on large dataset, network latency | `"Error: Request to Prometheus timed out after <N> seconds"` |
| Invalid PromQL | The PromQL expression is syntactically invalid | Malformed expression (Prometheus returns HTTP 400) | `"Error: Invalid PromQL expression: <prometheus_error_message>"` |
| API Error | Prometheus returned an unexpected server-side error | Internal server error (HTTP 5xx) | `"Error: Prometheus API returned HTTP <code>: <detail>"` |

**Input Validation:**

- `Prometheus URL` must be provided. If missing, the extension must fail with: `"Error: Prometheus URL is required"`.
- `PromQL Expression` must be provided for the Query Metric action. If missing, the extension must fail with: `"Error: PromQL Expression is required"`.
- `Credential` must be provided. If missing, the extension must fail with: `"Error: Credential is required"`.

---

# 5. Authentication Requirements

The extension must support **HTTP Basic Authentication** exclusively. The username and password are sourced from a UAC Credential field configured on the task. These credentials must be passed as a Basic Auth header on every HTTP request to the Prometheus API. No other authentication methods are required in this version.

---

# 6. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `UE_MAX_OUTPUT_RECORDS` | `100` | Maximum number of metric series or alerts to include in STDOUT and Extension Output. When results exceed this limit, output is truncated and a truncation note is added to STDOUT and the `truncated` flag is set to `true` in Extension Output. |
| `UE_SSL_VERIFY` | `true` (verification enabled) | Controls SSL/TLS certificate verification. Set to `false` to disable verification (intended for development or non-production environments with self-signed certificates). In production, configure custom CA bundles via the standard `REQUESTS_CA_BUNDLE` environment variable instead. |
| `UE_HTTP_TIMEOUT` | `30` (seconds) | Maximum number of seconds to wait for a response from the Prometheus API before raising a timeout error. |

---

# 7. Operational Behavior

**Dynamic Choice Fields:**
Not applicable. No dynamic choice population is required.

**Cancel Action:**
Standard UAC cancel behavior applies. No specific cancel handling beyond the default is required.

**Re-run Capability:**
The extension is stateless and idempotent. Re-running a task with the same inputs will re-query Prometheus at the current time, which may return different results reflecting the current state of the system.

**Progress Reporting:**
No progress bar is required. STDOUT logging must provide sufficient visibility: the action name and target URL must be logged at the start of execution, and a completion message must be logged before exit.

**Dynamic Commands:**
Not applicable. No dynamic commands are required.

---

# 8. Implementation Notes

## 8.1 Python Compatibility

Targeting compatibility for Python 3.11.

## 8.2 Target Platform

Linux only (confirmed from build environment: Linux x86_64). C extension modules with a confirmed `manylinux_2_17_x86_64` wheel are viable in addition to pure-Python modules. All identified candidate modules are pure-Python, so no binary wheel constraints apply.

## 8.3 Third-Party Services and Tools

**Prometheus HTTP API**
- Short Description: The REST API exposed by Prometheus for querying metrics and alert state. Used for all three supported endpoints: `/api/v1/query` (instant queries), `/api/v1/alerts` (active alerts).
- Version Constraints: No specific Prometheus server version constraint. The extension targets the stable Prometheus HTTP API v1.
- Integration Approach: The extension calls the Prometheus REST API directly using an HTTP client. No Prometheus-specific SDK or wrapper is used.

**requests (Python library)**
- Short Description: Industry-standard synchronous HTTP client used to call the Prometheus REST API endpoints.
- Version: `2.34.2`
- Type: Pure Python
- Integration Approach: Used for all HTTP GET requests to the Prometheus API, including Basic Auth header injection and SSL configuration.

**tabulate (Python library)**
- Short Description: Pure-Python library for formatting tabular data into ASCII tables for human-readable STDOUT output.
- Version: `0.10.0`
- Type: Pure Python
- Integration Approach: Used to render metric results and alert lists as ASCII tables with `tablefmt="rounded_outline"`.

## 8.4 Error Handling

**Error Categories:**
- Connection errors (network unreachable, DNS failure, wrong URL)
- Authentication errors (HTTP 401, HTTP 403)
- SSL/TLS errors (certificate verification failure)
- Timeout errors (request exceeds `UE_HTTP_TIMEOUT`)
- API errors (HTTP 400 for invalid PromQL, HTTP 5xx for server-side failures)
- Input validation errors (missing required fields)

**Error Handling Strategy:**
All errors must result in exit code 1. Error messages must be descriptive, including the error category, the target URL, and the underlying error detail where available. Errors must be written to STDERR.

**Recovery Mechanisms:**
No automatic retry or fallback behavior is required. Each task execution is a single attempt.

## 8.5 Resource Cleanup

**Cleanup Scenarios:**
HTTP connections opened during API calls must be properly closed upon completion or error, regardless of outcome.

**Strategy:**
Standard connection lifecycle management using context managers or equivalent patterns must be applied to ensure no connections are left open.

---

# 9. Requirements Summary

| Aspect | Decision |
|---|---|
| Actions in v1 | Query Metric, Check Alerts |
| Deferred to v2 | Get Targets |
| Authentication | Basic Auth via UAC Credential field |
| Prometheus URL | Required Text Field per task |
| Query type | Instant query only (`/api/v1/query`) |
| Evaluation time | Always current server time |
| Alert state options | All, Firing, Pending (default: All) |
| Alert name filter | Optional Text Field |
| metric_values field | Series count + value range summary |
| alert_state field | Count summary by state |
| STDOUT format | ASCII table with `tabulate`, `tablefmt="rounded_outline"` |
| Empty results behavior | Success (exit code 0) |
| Output record limit | `UE_MAX_OUTPUT_RECORDS` env var, default 100 |
| SSL verification | Enabled by default; `UE_SSL_VERIFY=false` to disable |
| HTTP timeout | `UE_HTTP_TIMEOUT` env var, default 30 seconds |
| HTTP client | `requests==2.34.2` |
| Table formatting | `tabulate==0.10.0` |
| Target platform | Linux only |
| Python version | 3.11 |

---

# 10. Document Change History

- **2026-09-04**: Initial requirements captured (completeness level: Low Detail) — one-sentence source covering service name, auth type, three action names, and three output fields.
- **2026-09-04**: Comprehensive refinement based on 11 clarification questions and user feedback — all design decisions resolved including action scope, query type, input fields, output format, SSL handling, timeout configuration, and output verbosity.

---

# 11. References

- Original Requirements Document: `memory/requirements.md`
- Original Requirements Q&A Document: `memory/agents-memory/requirements-QnA.md`
