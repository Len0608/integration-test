# Prometheus Monitoring - Implementation Analysis

**Extension Name:** *Prometheus Monitoring (ue-eval-prometheus-monitoring)*
**Universal Template Name:** *Ue Eval Prometheus Monitoring*
**Target Platform:** Linux

---

## Extension Overview

This extension enables UAC automation workflows to interact with a Prometheus monitoring server. It supports two actions: **Query Metric**, which executes a user-supplied PromQL expression as an instant query to retrieve current metric values; and **Check Alerts**, which retrieves and filters active alerts by name and state. Results are surfaced as structured JSON Extension Output, human-readable ASCII tables on STDOUT, and concise summaries in output-only fields visible in the UAC task list view.

---

# Template Fields

## 1. Input Fields

**action**
- **Type**: Choice Field (Single-select)
- **Required When**: always
- **Options**:
  - Query Metric — Execute a PromQL instant query and retrieve matching metric series
  - Check Alerts — Retrieve and filter currently active alerts by name and/or state
- **Default Value**: Query Metric
- **Validation**:
  - Must be one of the options
- **Purpose**: Specifies the operation to perform against the Prometheus server

---

**prometheus_url**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: always
- **Validation**:
  - Must not be empty
  - Must include scheme (http or https), host, and port
- **Purpose**: Base URL of the Prometheus server used as the root for all API requests
- **Example**: `http://prometheus.mycompany.com:9090`

---

**credential**
- **Type**: Credential Field
- **Visible When**: always
- **Required When**: always
- **Validation**:
  - Must not be empty; `user` and `password` attributes are required
- **Purpose**: UAC Credential record providing Basic Authentication credentials for all requests to the Prometheus server. The `user` attribute maps to the HTTP Basic Auth username; the `password` attribute maps to the HTTP Basic Auth password.

---

**promql_expression**
- **Type**: Text Field (Large)
- **Visible When**: `action` value is equal to "Query Metric". It is "required" when it's visible.
- **Required When**: `action` value is equal to "Query Metric"
- **Validation**:
  - Must not be empty when action is Query Metric
- **Purpose**: PromQL expression to evaluate as an instant query at the current server time against the Prometheus `/api/v1/query` endpoint
- **Example**: `node_cpu_seconds_total{mode="idle"}`

---

**alert_name**
- **Type**: Text Field
- **Visible When**: `action` value is equal to "Check Alerts". It is "not required" when it's visible.
- **Required When**: Never
- **Validation**:
  - When provided, must be a non-empty string; it is used as an exact match filter against the `alertname` label
- **Purpose**: Optional filter to return only alerts whose `alertname` label matches this value exactly. When left empty, no name filter is applied and all alerts pass through.
- **Example**: `HighCPUAlert`

---

**alert_state_filter**
- **Type**: Choice Field (Single-select)
- **Visible When**: `action` value is equal to "Check Alerts". It is "required" when it's visible.
- **Required When**: `action` value is equal to "Check Alerts"
- **Options**:
  - All — Return both firing and pending alerts
  - Firing — Return only alerts in the firing state
  - Pending — Return only alerts in the pending (warming-up) state
- **Default Value**: All
- **Validation**:
  - Must be one of the options
- **Purpose**: Filters the returned alerts by their current state; applied after the optional alert name filter

---

## 2. Output Fields

**metric_values**
- **Type**: Text Output
- **Visible When**: `action` is "Query Metric"
- **Purpose**: Concise summary of metric query results. Configured with `defaultListView: true` to appear in the UAC task list view. Shows total series count from Prometheus and observed value range across returned results.
- **Examples**: "3 series, values: 0.12–0.85", "0 series returned"

---

**alert_state**
- **Type**: Text Output
- **Visible When**: `action` is "Check Alerts"
- **Purpose**: Concise summary of alert counts by state across all matching alerts (before truncation). Configured with `defaultListView: true` to appear in the UAC task list view.
- **Examples**: "2 firing, 0 pending", "No active alerts"

---

## 3. Field Ordering

The task form uses a **2-column grid layout**. All fields in this extension span full-width because no fields are logically paired for side-by-side display.

**Layout Rules:**
- Credential fields ALWAYS span full-width (both columns)
- Action selection spans full-width for prominence
- All other fields span full-width (no logical half-width pairs)

**Field Order (Visual Layout):**

```
┌─────────────────────────────────────────┐
│                 action                  │  ← Full-width
├─────────────────────────────────────────┤
│             prometheus_url              │  ← Full-width
├─────────────────────────────────────────┤
│              credential                 │  ← Full-width (credential)
├─────────────────────────────────────────┤
│           promql_expression             │  ← Full-width (Query Metric only)
├─────────────────────────────────────────┤
│              alert_name                 │  ← Full-width (Check Alerts only)
├─────────────────────────────────────────┤
│          alert_state_filter             │  ← Full-width (Check Alerts only)
├─────────────────────────────────────────┤
│            metric_values                │  ← Full-width output (Query Metric)
├─────────────────────────────────────────┤
│             alert_state                 │  ← Full-width output (Check Alerts)
└─────────────────────────────────────────┘
```

---

# Actions

## Action 1: Query Metric

**Description**: Executes the user-supplied PromQL expression as an instant query against the Prometheus `/api/v1/query` endpoint at the current server time. Returns all matching metric series up to the `UE_MAX_OUTPUT_RECORDS` limit. Displays results as an ASCII table on STDOUT and populates the `metric_values` output field with total series count and observed value range.

### Input Requirements

- **action** — must be "Query Metric"
- **prometheus_url** — Prometheus server base URL
- **credential** — UAC credential for Basic Auth (user attribute = username, password attribute = password)
- **promql_expression** — PromQL expression to evaluate

### Execution Flow

**Step 1: Input Validation**
- Verify `prometheus_url` is not empty. If missing or empty, raise `InputValidationError` with message "Error: Prometheus URL is required"; exit code 20.
- Verify `credential` is provided (non-null). If missing, raise `InputValidationError` with message "Error: Credential is required"; exit code 20.
- Verify `promql_expression` is not empty. If missing or empty, raise `InputValidationError` with message "Error: PromQL Expression is required"; exit code 20.

**Step 2: Read Environment Configuration**
- Read `UE_MAX_OUTPUT_RECORDS` as integer; use 100 if not set or not parseable as integer.
- Read `UE_SSL_VERIFY`: if value equals "false" (case-insensitive), set ssl_verify = False; otherwise set ssl_verify = True.
- Read `UE_HTTP_TIMEOUT` as integer (seconds); use 30 if not set or not parseable.

**Step 3: Log Start**
- Print to STDOUT: "Starting Query Metric action against {prometheus_url}"

**Step 4: Execute Instant Query**
- Send HTTP GET to `{prometheus_url}/api/v1/query` with query parameter `query` set to the value of `promql_expression`.
- Set HTTP Basic Auth header using credential `user` (username) and `password` (password).
- Apply ssl_verify and timeout from Step 2.
- Use HTTP session as context manager to guarantee connection cleanup on completion or error.

**Step 5: Parse API Response**
- On non-2xx HTTP status code, classify and raise the appropriate exception (see Exception Mapping Strategy).
- Parse JSON response body. Verify top-level `status` field equals "success". If Prometheus returns `status = "error"`, raise `PrometheusQueryError` using the `error` field from the response as the detail message (this handles invalid PromQL returned as HTTP 400 with JSON error body).
- Extract `data.result` array. Each element contains:
  - `metric`: dict of label key-value pairs, where `__name__` key holds the metric name
  - `value`: two-element array `[unix_timestamp_float, value_string]`
- Record `total_count` = length of `data.result`.

**Step 6: Apply Output Record Limit**
- If `total_count > UE_MAX_OUTPUT_RECORDS`, slice results to first `UE_MAX_OUTPUT_RECORDS` elements and set `truncated = True`.
- Otherwise set `truncated = False`. The working results set is the (possibly truncated) slice.

**Step 7: Format and Print STDOUT Table**
- For each result in the working results set, build a display row:
  - **Metric column**: Format the `metric` dict as a Prometheus selector string. Extract `__name__` as the base metric name. Format all remaining label keys/values as `{key="value",key2="value2"}` appended to the base name. If no `__name__` key is present, format all labels as `{key="value",...}`.
  - **Value column**: Convert `value[1]` string to float; use Python default float representation.
  - **Timestamp column**: Convert `value[0]` Unix epoch float to ISO 8601 UTC string truncated to whole seconds (e.g., `2026-09-04T10:00:00Z`).
- Render using `tabulate` with headers `["Metric", "Value", "Timestamp"]` and `tablefmt="rounded_outline"`. Print the rendered table to STDOUT.
- If `truncated = True`, print to STDOUT: "Note: Output truncated to {UE_MAX_OUTPUT_RECORDS} of {total_count} available series."

**Step 8: Compute Output Field, Status Description, and Extension Output**
- **metric_values field**:
  - If `total_count == 0`: set to `"0 series returned"`
  - If `total_count > 0`: extract float values from the working results set; compute min and max. Set to `"{total_count} series, values: {min}–{max}"`
- **Status description**:
  - If `total_count > 0`: `"Success: {total_count} series returned for the expression"`
  - If `total_count == 0`: `"Success: 0 metric series returned for the expression"`
- **Extension Output result object**:
```json
{
  "result": {
    "action": "query_metric",
    "promql_expression": "<value of promql_expression field>",
    "result_count": "<total_count — total series from Prometheus before truncation>",
    "truncated": "<true if total_count > UE_MAX_OUTPUT_RECORDS, false otherwise>",
    "results": [
      {
        "metric": {"__name__": "node_cpu_seconds_total", "mode": "idle"},
        "value": 0.85,
        "timestamp": "2026-09-04T10:00:00Z"
      }
    ]
  }
}
```

**Step 9: Log Completion and Exit**
- Print to STDOUT: "Query Metric completed. {total_count} series returned."
- Exit with code 0.

### Output Examples

**STDOUT**:
```
Starting Query Metric action against http://prometheus.mycompany.com:9090
╭──────────────────────────────────────────┬────────┬──────────────────────────╮
│ Metric                                   │ Value  │ Timestamp                │
├──────────────────────────────────────────┼────────┼──────────────────────────┤
│ node_cpu_seconds_total{mode="idle"}      │ 0.85   │ 2026-09-04T10:00:00Z     │
│ node_cpu_seconds_total{mode="user"}      │ 0.12   │ 2026-09-04T10:00:00Z     │
╰──────────────────────────────────────────┴────────┴──────────────────────────╯
Query Metric completed. 2 series returned.
```

**Extension Output result object (JSON)**:

The Extension Output includes `exit_code`, `status_description`, and `invocation` elements added automatically during implementation. The `result` element for this action:

```json
{
  "result": {
    "action": "query_metric",
    "promql_expression": "node_cpu_seconds_total",
    "result_count": 2,
    "truncated": false,
    "results": [
      {
        "metric": {"__name__": "node_cpu_seconds_total", "mode": "idle"},
        "value": 0.85,
        "timestamp": "2026-09-04T10:00:00Z"
      },
      {
        "metric": {"__name__": "node_cpu_seconds_total", "mode": "user"},
        "value": 0.12,
        "timestamp": "2026-09-04T10:00:00Z"
      }
    ]
  }
}
```

### Success Criteria
- Prometheus API returns HTTP 2xx with `status = "success"` in JSON body
- PromQL expression is syntactically valid (no HTTP 400 from Prometheus)
- Results (including empty result set) are successfully parsed and formatted
- `metric_values` output field is populated with the appropriate summary
- Extension Output `result` object conforms to the structure above
- Exit code is 0

---

## Action 2: Check Alerts

**Description**: Retrieves all currently active alerts from the Prometheus `/api/v1/alerts` endpoint. Filters the results client-side by optional exact `alertname` match and required state filter. Returns matching alerts up to the `UE_MAX_OUTPUT_RECORDS` limit. Displays results as an ASCII table on STDOUT and populates the `alert_state` output field with total firing and pending counts.

### Input Requirements

- **action** — must be "Check Alerts"
- **prometheus_url** — Prometheus server base URL
- **credential** — UAC credential for Basic Auth (user attribute = username, password attribute = password)
- **alert_name** — optional exact match filter for `alertname` label (empty = no filter)
- **alert_state_filter** — state filter: "All", "Firing", or "Pending"

### Execution Flow

**Step 1: Input Validation**
- Verify `prometheus_url` is not empty. If missing or empty, raise `InputValidationError` with message "Error: Prometheus URL is required"; exit code 20.
- Verify `credential` is provided (non-null). If missing, raise `InputValidationError` with message "Error: Credential is required"; exit code 20.

**Step 2: Read Environment Configuration**
- Read `UE_MAX_OUTPUT_RECORDS` as integer; use 100 if not set or not parseable.
- Read `UE_SSL_VERIFY`: if value equals "false" (case-insensitive), set ssl_verify = False; otherwise set ssl_verify = True.
- Read `UE_HTTP_TIMEOUT` as integer (seconds); use 30 if not set or not parseable.

**Step 3: Log Start**
- Print to STDOUT: "Starting Check Alerts action against {prometheus_url}"

**Step 4: Fetch Active Alerts**
- Send HTTP GET to `{prometheus_url}/api/v1/alerts`.
- Set HTTP Basic Auth header using credential `user` (username) and `password` (password).
- Apply ssl_verify and timeout from Step 2.
- Use HTTP session as context manager to guarantee connection cleanup on completion or error.

**Step 5: Parse API Response**
- On non-2xx HTTP status code, classify and raise the appropriate exception (see Exception Mapping Strategy).
- Parse JSON response body. Verify top-level `status` field equals "success".
- Extract `data.alerts` array. Each element contains:
  - `labels`: dict of label key-value pairs; `alertname` is extracted from `labels["alertname"]`
  - `state`: string — "firing" or "pending"
  - `activeAt`: ISO 8601 UTC timestamp string (e.g., "2026-09-04T09:45:00.123456789Z")
  - `annotations`: dict of annotation key-value pairs

**Step 6: Apply Client-Side Filters**
- **Alert name filter**: If `alert_name` input is provided and non-empty, retain only alerts where `labels["alertname"]` equals `alert_name` exactly (case-sensitive string comparison). If `alert_name` is empty or not provided, all alerts pass this filter.
- **State filter**: Apply based on the selected `alert_state_filter` option:
  - "All" (choice value "all"): retain alerts where `state` is "firing" or "pending"
  - "Firing" (choice value "firing"): retain alerts where `state` is "firing" only
  - "Pending" (choice value "pending"): retain alerts where `state` is "pending" only

**Step 7: Compute Totals from All Filtered Alerts**
- `total_found` = count of all alerts passing both filters (before truncation)
- `firing_count` = count of filtered alerts where `state` is "firing"
- `pending_count` = count of filtered alerts where `state` is "pending"

**Step 8: Apply Output Record Limit**
- If `total_found > UE_MAX_OUTPUT_RECORDS`, slice the filtered alerts to first `UE_MAX_OUTPUT_RECORDS` elements and set `truncated = True`.
- Otherwise set `truncated = False`. The working alerts set is the (possibly truncated) slice.

**Step 9: Format and Print STDOUT Table**
- For each alert in the working alerts set, build a display row:
  - **Alert Name column**: `labels["alertname"]`
  - **State column**: `state` value as-is (e.g., "firing", "pending")
  - **Active Since column**: the `activeAt` string truncated to whole seconds by stripping sub-second precision and trailing nanoseconds (e.g., `"2026-09-04T09:45:00Z"`)
- Render using `tabulate` with headers `["Alert Name", "State", "Active Since"]` and `tablefmt="rounded_outline"`. Print the rendered table to STDOUT.
- If `truncated = True`, print to STDOUT: "Note: Output truncated to {UE_MAX_OUTPUT_RECORDS} of {total_found} available alerts."

**Step 10: Compute Output Field, Status Description, and Extension Output**
- **alert_state field**:
  - If `total_found == 0`: set to `"No active alerts"`
  - If `total_found > 0`: set to `"{firing_count} firing, {pending_count} pending"`
- **Status description**:
  - If `total_found > 0`: `"Success: {firing_count} firing, {pending_count} pending alerts matched the filter"`
  - If `total_found == 0`: `"Success: No active alerts matching the filter"`
- **alert_name_filter value in Extension Output**: the value of the `alert_name` input field if provided and non-empty; otherwise `null`.
- **state_filter value in Extension Output**: lowercase value of the selected `alert_state_filter` choice ("all", "firing", or "pending").
- **Extension Output result object**:
```json
{
  "result": {
    "action": "check_alerts",
    "alert_name_filter": "<alert_name value or null>",
    "state_filter": "<all | firing | pending>",
    "total_found": "<total_found — count of all matching alerts before truncation>",
    "firing_count": "<firing_count>",
    "pending_count": "<pending_count>",
    "truncated": "<true if total_found > UE_MAX_OUTPUT_RECORDS, false otherwise>",
    "alerts": [
      {
        "alertname": "HighCPUAlert",
        "state": "firing",
        "active_since": "2026-09-04T09:45:00Z",
        "labels": {"severity": "critical", "instance": "node1"},
        "annotations": {"summary": "CPU usage exceeded threshold"}
      }
    ]
  }
}
```

**Step 11: Log Completion and Exit**
- Print to STDOUT: "Check Alerts completed. {firing_count} firing, {pending_count} pending alerts matched the filter."
- Exit with code 0.

### Output Examples

**STDOUT**:
```
Starting Check Alerts action against http://prometheus.mycompany.com:9090
╭────────────────┬─────────┬─────────────────────────────╮
│ Alert Name     │ State   │ Active Since                │
├────────────────┼─────────┼─────────────────────────────┤
│ HighCPUAlert   │ firing  │ 2026-09-04T09:45:00Z        │
│ DiskSpaceWarn  │ pending │ 2026-09-04T09:58:00Z        │
╰────────────────┴─────────┴─────────────────────────────╯
Check Alerts completed. 1 firing, 1 pending alerts matched the filter.
```

**Extension Output result object (JSON)**:

The Extension Output includes `exit_code`, `status_description`, and `invocation` elements added automatically during implementation. The `result` element for this action:

```json
{
  "result": {
    "action": "check_alerts",
    "alert_name_filter": null,
    "state_filter": "all",
    "total_found": 2,
    "firing_count": 1,
    "pending_count": 1,
    "truncated": false,
    "alerts": [
      {
        "alertname": "HighCPUAlert",
        "state": "firing",
        "active_since": "2026-09-04T09:45:00Z",
        "labels": {"severity": "critical"},
        "annotations": {"summary": "CPU usage exceeded threshold"}
      },
      {
        "alertname": "DiskSpaceWarn",
        "state": "pending",
        "active_since": "2026-09-04T09:58:00Z",
        "labels": {"severity": "warning"},
        "annotations": {"summary": "Disk usage above 80%"}
      }
    ]
  }
}
```

### Success Criteria
- Prometheus API returns HTTP 2xx with `status = "success"` in JSON body
- Filters are applied correctly client-side (exact name match, state match)
- Results (including empty result set) are successfully parsed and formatted
- `alert_state` output field is populated with the appropriate count summary
- Extension Output `result` object conforms to the structure above
- Exit code is 0

---

# Progress Reporting

Progress Reporting (percentage of completion report) is not required. STDOUT logging provides execution visibility: each action logs the action name and target URL at the start of execution, and a completion message before exit.

---

# Dynamic Choice Field Population

No Dynamic choice fields should be implemented.

---

# Cancellation Behavior

Default UAC cancellation behavior applies. The extension performs stateless, short-lived HTTP API calls with no background threads or long-running external jobs. No custom cancellation logic is required. Upon receipt of the TERM signal, the process terminates immediately; HTTP connections are closed by the OS.

---

# Re-Run Behavior

Re-runs are treated as initial executions. The extension is stateless and idempotent: each execution queries the Prometheus API at the current time and may return different results reflecting the current system state. No output-only fields from previous runs are used to alter execution behavior.

---

# Dynamic Commands

No Dynamic commands should be implemented.

---

# Utility Modules

## Required Utility Modules

### 1. Prometheus API Client

**Purpose:** Manages all HTTP communication with the Prometheus server, including authentication, SSL configuration, timeout enforcement, response validation, and exception classification.

**Required Capabilities:**

**Prometheus HTTP API:**
- Execute HTTP GET to `/api/v1/query` with `query` parameter set to the PromQL expression string
- Execute HTTP GET to `/api/v1/alerts` with no query parameters
- Configure HTTP Basic Authentication on every request using credential `user` attribute as username and `password` attribute as password
- Configure SSL certificate verification per `UE_SSL_VERIFY` environment variable (True by default; False when set to "false" case-insensitively)
- Configure request timeout per `UE_HTTP_TIMEOUT` environment variable (default 30 seconds)
- Use HTTP session as context manager to guarantee connection cleanup on both normal exit and exception

**Response Validation:**
- Parse JSON response body
- Verify top-level `status` field equals "success"; if `status` equals "error", extract `error` field as the detail message
- Return the parsed `data` object to the caller on success

**Error Classification:**
- `requests.ConnectionError` (network unreachable, DNS failure) → raise `PrometheusConnectionError` with message "Unable to connect to Prometheus server at {url}: {detail}"
- `requests.exceptions.SSLError` (certificate verification failed) → raise `PrometheusSSLError` with message "SSL certificate verification failed for {url}: {detail}"
- `requests.Timeout` (request exceeded timeout) → raise `PrometheusTimeoutError` with message "Request to Prometheus timed out after {timeout} seconds"
- HTTP 401 or HTTP 403 response → raise `PrometheusAuthenticationError` with message "Authentication failed for Prometheus server at {url} (HTTP {code})"
- HTTP 400 response or Prometheus JSON `status = "error"` → raise `PrometheusQueryError` with message "Invalid PromQL expression: {prometheus_error_message}"
- HTTP 5xx response or any other non-2xx response → raise `PrometheusAPIError` with message "Prometheus API returned HTTP {code}: {detail}"

**Used By:** Query Metric action, Check Alerts action

---

### 2. Result Formatter

**Purpose:** Transforms raw Prometheus API response data into display-ready formats for STDOUT and Extension Output, and computes summary strings for output-only fields.

**Required Capabilities:**

**Timestamp Conversion:**
- Convert Unix epoch float (from Query Metric `value[0]`) to ISO 8601 UTC string truncated to whole seconds (e.g., `2026-09-04T10:00:00Z`)
- Truncate ISO 8601 nanosecond timestamps from Check Alerts `activeAt` field to whole-second precision (e.g., strip sub-second suffix, ensure trailing `Z`)

**Metric Label Formatting:**
- Accept a `metric` dict (label key-value pairs) and return a Prometheus-format selector string
- Extract `__name__` key as the base metric name; format remaining keys as `{key="value",key2="value2"}` appended directly
- If no `__name__` key present, format all keys as `{key="value",...}` with no base name prefix
- If no labels at all, return empty string

**Output Record Limiting:**
- Accept a list and a limit integer; return a tuple of (truncated_list, total_count, was_truncated_bool)
- Truncation slices to the first `limit` elements

**Tabulate Table Rendering:**
- Accept a list of row tuples and a list of column header strings
- Render and return an ASCII table string using `tabulate` with `tablefmt="rounded_outline"`

**Metric Summary String:**
- Accept total_count (int) and a list of float values from the working results set
- If total_count == 0: return `"0 series returned"`
- If total_count > 0: compute min and max of the float value list; return `"{total_count} series, values: {min}–{max}"`

**Alert Summary String:**
- Accept firing_count (int) and pending_count (int) representing totals from all filtered alerts
- If firing_count + pending_count == 0: return `"No active alerts"`
- Otherwise: return `"{firing_count} firing, {pending_count} pending"`

**Used By:** Query Metric action, Check Alerts action

---

## Exception Mapping Strategy

**Input Validation Errors:**
- Missing or empty `prometheus_url` → `InputValidationError` (exit code 20, user input error)
- Missing `credential` → `InputValidationError` (exit code 20, user input error)
- Missing or empty `promql_expression` when action is Query Metric → `InputValidationError` (exit code 20, user input error)

**HTTP Communication Errors:**
- Network/DNS failure → `PrometheusConnectionError` (exit code 1, potentially transient)
- SSL certificate verification failure → `PrometheusSSLError` (exit code 1, user/environment configuration)
- Request timeout exceeded → `PrometheusTimeoutError` (exit code 1, potentially transient)

**API Response Errors:**
- HTTP 401 or 403 → `PrometheusAuthenticationError` (exit code 1, user credential configuration)
- HTTP 400 or Prometheus `status = "error"` → `PrometheusQueryError` (exit code 1, user input — invalid PromQL)
- HTTP 5xx or other non-2xx → `PrometheusAPIError` (exit code 1, server-side or unexpected)

**Exit Code Guide:**
- Exit code 0: Successful execution (including empty result sets)
- Exit code 1: Runtime failure (connection, authentication, SSL, timeout, API, or query errors)
- Exit code 20: Input validation error — missing or invalid required field value

---

# Dependencies

## 1. External API Dependencies

**1. Prometheus HTTP API**
- **Endpoint**: `{prometheus_url}/api/v1/query` and `{prometheus_url}/api/v1/alerts`
- **Purpose**: Instant metric queries (Query Metric action) and active alert retrieval (Check Alerts action)
- **Protocol**: HTTP or HTTPS (determined by scheme in `prometheus_url`)
- **Method**: HTTP GET
- **Authentication**: HTTP Basic Authentication — username from credential `user` attribute, password from credential `password` attribute
- **Response Format**: JSON with top-level `status` ("success" or "error") and `data` fields
- **Data Retrieved**:
  - `/api/v1/query`: `data.result` array with `metric` (label dict) and `value` ([timestamp, value_string]) per series
  - `/api/v1/alerts`: `data.alerts` array with `labels`, `state`, `activeAt`, and `annotations` per alert

**General API Requirements:**
- No Prometheus SDK is used; the extension calls the REST API directly via `requests`
- No specific Prometheus server version constraint; targets the stable Prometheus HTTP API v1
- SSL/TLS certificate verification is enabled by default; disable via `UE_SSL_VERIFY=false` for self-signed certificates in non-production environments

---

## 2. Python version dependency

Python >= 3.11

---

## 3. Target Platform

Linux only (build environment: Linux x86_64). C extension modules with a confirmed `manylinux_2_17_x86_64` wheel are viable in addition to pure-Python modules. All identified runtime dependencies (`requests`, `tabulate`) are pure-Python, so no binary wheel constraints apply.

---

## 4. Python Library Dependencies

**1. requests**
- **Purpose**: Synchronous HTTP client for all Prometheus API calls, including Basic Auth header injection and SSL configuration
- **Version**: `2.34.2`
- **Installation**: `pip install requests==2.34.2`
- **Usage**: HTTP GET requests in Prometheus API Client utility module
- **Features Used**: `requests.Session`, Basic Auth via `auth` parameter, `verify` parameter for SSL, `timeout` parameter, `requests.ConnectionError`, `requests.Timeout`, `requests.exceptions.SSLError`

**2. tabulate**
- **Purpose**: Pure-Python library for rendering tabular data as ASCII tables for STDOUT output
- **Version**: `0.10.0`
- **Installation**: `pip install tabulate==0.10.0`
- **Usage**: Result Formatter utility module for rendering metric and alert tables
- **Features Used**: `tabulate()` function with `tablefmt="rounded_outline"` and custom column headers

---

## 5. Python Standard Library Dependencies

**1. os**
- **Purpose**: Read environment variables
- **Usage**: Read `UE_MAX_OUTPUT_RECORDS`, `UE_SSL_VERIFY`, `UE_HTTP_TIMEOUT` in both action execution flows

**2. datetime**
- **Purpose**: Unix epoch to ISO 8601 UTC timestamp conversion
- **Usage**: Result Formatter utility — convert Prometheus `value[0]` Unix epoch float to ISO string

**3. json**
- **Purpose**: JSON parsing and serialization
- **Usage**: Parse Prometheus API JSON response bodies; construct Extension Output JSON

---

## 6. CLI Tool Dependencies

No Dependencies.

---

## 7. Environment Variables

**UE_MAX_OUTPUT_RECORDS** (integer, optional):
- **Purpose**: Caps the number of metric series or alerts included in STDOUT table and Extension Output results array. When results exceed this limit, output is truncated, a note is added to STDOUT, and `truncated: true` is set in Extension Output.
- **Default**: 100
- **Usage**: Applied in both Query Metric and Check Alerts actions after fetching data from Prometheus
- **Examples**: `50`, `200`, `500`

**UE_SSL_VERIFY** (string boolean, optional):
- **Purpose**: Controls SSL/TLS certificate verification for all Prometheus API requests. Set to "false" to disable verification for development or non-production environments using self-signed certificates. In production, configure custom CA bundles via `REQUESTS_CA_BUNDLE` instead.
- **Default**: `"true"` (verification enabled)
- **Usage**: Parsed in both actions; passed as `verify` parameter to the HTTP session
- **Examples**: `"true"`, `"false"`

**UE_HTTP_TIMEOUT** (integer, optional):
- **Purpose**: Maximum number of seconds to wait for a Prometheus API response before raising a timeout error
- **Default**: `30`
- **Usage**: Passed as `timeout` parameter to every HTTP request in both actions
- **Examples**: `10`, `60`, `120`
