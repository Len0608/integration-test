# Integration Examples Reference

The following production-grade Stonebranch Universal Extension templates are provided as reference. Use them to guide field naming, type selection, credential design, and action structure.

## Field Type Reference

| Type       | When to use |
|------------|-------------|
| Choice     | Fixed enumeration — action modes, providers, protocols, regions |
| Credential | UAC Credential record reference — never store secrets inline |
| Text       | Free-form string — URLs, resource names, IDs, query strings |
| Script     | Multi-line editor — SQL, JSON payloads, shell snippets, prompts |
| Boolean    | Toggle flags — SSL verify, verbose logging, dry-run, wait mode |
| Integer    | Whole numbers — timeouts (s), retry counts, page sizes, ports |
| Float      | Decimal numbers — LLM temperature, top-p, penalty weights |
| Array      | Repeating key/value pairs — HTTP headers, env vars, parameters |

Design rules:
- Use one Credential field per authentication context (source vs. destination).
- Name credential fields clearly: `api_credential`, `sftp_credential`.
- Prefer Choice over Text for any field with a known fixed set of values.
- Use Integer for all numeric tuning knobs (timeout, retries, page size).
- Use Script only for multi-line content (payloads, queries, inline code).
- Output/status fields (Text) let operators capture results as UAC variables.

---

## Most Relevant Examples

### Salesforce Data Mover — `ue-sf-data-mover`
**Category:** CRM / Data Movement
**Description:** Export, insert, and upsert Salesforce records.
**Fields (29):**

| Field name | Type | Choices / Notes |
|------------|------|-----------------|
| `action` | Choice | Export, Insert, Upsert |
| `authentication_method` | Choice | OAuth 2.0 Client Credentials Flow |
| `credential` | Credential |  |
| `instance_url` | Text |  |
| `object_name` | Choice |  |
| `file_path` | Text |  |
| `file_format` | Choice | CSV |
| `delimiter` | Choice | Comma (,), Pipe (|), Tab (\t), Semicolon (;) |
| `quote_mode` | Choice | Quote Necessary, Quote All, Quote Non-Null |
| `overwrite_options` | Choice | Overwrite, Do Not Overwrite, Append Timestamp In Filename |
| `export_writable_only` | Boolean | false |
| `external_id_field` | Choice |  |
| `fields_source` | Choice | Text, Script |
| `fields` | Text |  |
| `fields_script` | Script |  |
| `soql_filter_source` | Choice | Text, Script |
| `soql_filter` | Text |  |
| `soql_filter_script` | Script |  |
| `stop_on_error` | Boolean | false |
| `error_on_failed_records` | Boolean | false |
| `results_output_dir` | Text |  |
| `chunk_size_mb` | Integer | 100 |
| `dry_run` | Boolean | false |
| `last_job_state` | Text |  |
| `job_id` | Text |  |
| `records_exported` | Integer |  |
| `records_succeeded` | Integer |  |
| `records_failed` | Integer |  |
| `records_unprocessed` | Integer |  |


### Azure Kubernetes Service Jobs — `ue-aks-jobs`
**Category:** Cloud Compute / Kubernetes
**Description:** Execute AKS jobs on a cluster
**Fields (28):**

| Field name | Type | Choices / Notes |
|------------|------|-----------------|
| `action` | Choice | Apply Job, Apply CronJob, Create Job, Create CronJob, Create Job from CronJob, Delete Resource |
| `resource_type` | Choice | Job, CronJob |
| `az_auth_method` | Choice | Service Principal (Client Credentials), Workload Identity |
| `client_credentials` | Credential |  |
| `tenant_id` | Text |  |
| `opt_client_credentials` | Credential |  |
| `opt_tenant_id` | Text |  |
| `subscription_id` | Choice |  |
| `resource_group` | Choice |  |
| `cluster` | Choice |  |
| `namespace` | Text |  |
| `cronjob` | Choice |  |
| `new_job_name` | Text |  |
| `resource_name` | Choice |  |
| `resource_definition_type` | Choice | UAC Script, Local File, HTTP Link |
| `resource_definition_script` | Script |  |
| `resource_definition_path` | Text |  |
| `resource_definition_link` | Text |  |
| `wait_for_success_or_failure` | Boolean | false |
| `monitoring_timeout` | Integer |  |
| `extension_output_options` | Choice | Include Resource Specification and Metadata, Include Container Information |
| `stdout_options` | Choice | Enable Pod Monitoring, Include Container Logs |
| `delete_job_options` | Choice | Delete Job on Successful Execution, Delete Job Regardless of Execution Status, Do not Delete Job |
| `retr_clogs_only_on_failure` | Boolean | false |
| `resource_name_output` | Text |  |
| `resource_namespace_output` | Text |  |
| `job_status_output` | Text |  |
| `last_updated_on` | Text |  |


### Oracle Analytics Publisher - Fusion Applications — `ue-oracle-analytics-publisher`
**Category:** Reporting / Analytics
**Description:** Authenticates to Oracle Analytics Publisher, submits a report job via scheduleReport, and polls getScheduledReportStatus until a terminal state is reached or the polling timeout is exceeded.
**Fields (30):**

| Field name | Type | Choices / Notes |
|------------|------|-----------------|
| `action` | Choice | Schedule and Monitor Report |
| `oracle_credential` | Credential |  |
| `schedule_service_url` | Text |  |
| `verify_tls` | Boolean | true |
| `connection_timeout_seconds` | Integer | 30 |
| `request_timeout_seconds` | Integer | 60 |
| `report_absolute_path` | Text |  |
| `report_parameters` | Text | {} |
| `output_format` | Choice | PDF format, HTML format, RTF format, Excel (legacy) format, Excel 2000 format, Excel XLSX format |
| `report_template` | Text |  |
| `report_locale` | Choice | en-US, en-GB, de-DE, fr-FR, es-ES, it-IT |
| `ui_locale` | Choice | en-US, en-GB, de-DE, fr-FR, es-ES, it-IT |
| `report_timezone` | Choice | UTC, Europe/Berlin, Europe/London, America/New_York, America/Chicago, America/Denver |
| `bypass_cache` | Boolean | false |
| `job_name` | Text |  |
| `job_description` | Text |  |
| `save_data` | Boolean | false |
| `save_output` | Boolean | false |
| `bursting` | Boolean | false |
| `public_schedule` | Boolean | false |
| `job_locale` | Choice | en-US, en-GB, de-DE, fr-FR, es-ES, it-IT |
| `job_timezone` | Choice | UTC, Europe/Berlin, Europe/London, America/New_York, America/Chicago, America/Denver |
| `poll_interval_seconds` | Integer | 10 |
| `maximum_wait_seconds` | Integer | 3600 |
| `unknown_status_retry_count` | Integer | 3 |
| `scheduled_job_id` | Text |  |
| `final_status` | Text |  |
| `status_message` | Text |  |
| `elapsed_seconds` | Text |  |
| `report_path` | Text |  |

