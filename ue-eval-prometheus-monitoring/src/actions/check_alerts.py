"""Check Alerts action for the Prometheus Monitoring Universal Extension.

Retrieves all currently active alerts from the Prometheus /api/v1/alerts
endpoint. Applies client-side filtering by alert name and state, then returns
matching alerts up to the UE_MAX_OUTPUT_RECORDS limit.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from actions.output import ActionOutput
from exceptions import InputValidationError
from fields.input import InputFields
from fields.output import OutputFields
from manager import ExtensionManager
from utility import (
    PrometheusClient,
    alert_summary,
    apply_record_limit,
    render_table,
    truncate_iso_timestamp,
)

logger = logging.getLogger("UNV")
extension_manager = ExtensionManager()


def _read_max_records() -> int:
    """Return UE_MAX_OUTPUT_RECORDS as int; default 100."""
    raw: str = os.environ.get("UE_MAX_OUTPUT_RECORDS", "")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 100


def check_alerts(input_data: InputFields) -> ActionOutput:
    """Retrieve and filter active Prometheus alerts.

    Args:
        input_data: Validated input fields containing prometheus_url,
                    credential, optional alert_name, and alert_state_filter.

    Returns:
        ActionOutput with structured result dict and status_description.

    Raises:
        InputValidationError:         Missing or empty required input field.
        PrometheusConnectionError:    Network/DNS failure reaching Prometheus.
        PrometheusSSLError:           SSL certificate verification failure.
        PrometheusTimeoutError:       Request exceeded configured timeout.
        PrometheusAuthenticationError: HTTP 401 or 403 from Prometheus.
        PrometheusAPIError:           Unexpected non-2xx HTTP response.
    """
    logger.info("Starting check_alerts action")

    # ------------------------------------------------------------------
    # Step 1: Input validation
    # ------------------------------------------------------------------
    if not input_data.prometheus_url or not input_data.prometheus_url.value:
        logger.error("prometheus_url is missing or empty")
        raise InputValidationError("Error: Prometheus URL is required")

    if input_data.credential is None:
        logger.error("credential is missing")
        raise InputValidationError("Error: Credential is required")

    prometheus_url: str = input_data.prometheus_url.value
    username: str = input_data.credential.user
    password: str = input_data.credential.password

    # Optional alert name filter
    alert_name_input: Optional[str] = (
        input_data.alert_name.value
        if input_data.alert_name and input_data.alert_name.value
        else None
    )

    # State filter — default "All" when not provided
    state_filter_raw: str = (
        input_data.alert_state_filter.value
        if input_data.alert_state_filter
        else "All"
    )
    # Normalise to lowercase for comparison and Extension Output
    state_filter: str = state_filter_raw.lower()

    logger.debug(
        "check_alerts inputs: prometheus_url=%s alert_name=%s alert_state_filter=%s",
        prometheus_url,
        alert_name_input,
        state_filter,
    )

    # ------------------------------------------------------------------
    # Step 2: Read environment configuration
    # ------------------------------------------------------------------
    max_records: int = _read_max_records()
    logger.debug("UE_MAX_OUTPUT_RECORDS=%d", max_records)

    # ------------------------------------------------------------------
    # Step 3: Initialise OutputFields and log start
    # ------------------------------------------------------------------
    output_fields: OutputFields = OutputFields()
    output_fields.update(alert_state="Fetching alerts...")

    print(f"Starting Check Alerts action against {prometheus_url}")
    logger.info("Fetching active alerts from Prometheus")

    # ------------------------------------------------------------------
    # Step 4 & 5: Fetch active alerts and parse response
    # ------------------------------------------------------------------
    with PrometheusClient(prometheus_url, username, password) as client:
        data: Dict[str, Any] = client.alerts()

    raw_alerts: List[Dict[str, Any]] = data.get("alerts", [])
    logger.info("Prometheus returned %d raw alerts", len(raw_alerts))

    # ------------------------------------------------------------------
    # Step 6: Apply client-side filters
    # ------------------------------------------------------------------
    filtered_alerts: List[Dict[str, Any]] = []
    for alert in raw_alerts:
        labels: Dict[str, str] = alert.get("labels", {})
        alert_state_value: str = alert.get("state", "")

        # Alert name filter (exact match, case-sensitive)
        if alert_name_input is not None:
            if labels.get("alertname", "") != alert_name_input:
                continue

        # State filter
        if state_filter == "all":
            if alert_state_value not in ("firing", "pending"):
                continue
        elif state_filter == "firing":
            if alert_state_value != "firing":
                continue
        elif state_filter == "pending":
            if alert_state_value != "pending":
                continue

        filtered_alerts.append(alert)

    logger.debug(
        "After filtering: %d alerts pass (name_filter=%s state_filter=%s)",
        len(filtered_alerts),
        alert_name_input,
        state_filter,
    )

    # ------------------------------------------------------------------
    # Step 7: Compute totals from all filtered alerts (before truncation)
    # ------------------------------------------------------------------
    firing_count: int = sum(
        1 for a in filtered_alerts if a.get("state") == "firing"
    )
    pending_count: int = sum(
        1 for a in filtered_alerts if a.get("state") == "pending"
    )

    # ------------------------------------------------------------------
    # Step 8: Apply output record limit
    # ------------------------------------------------------------------
    working_alerts, total_found, truncated = apply_record_limit(
        filtered_alerts, max_records
    )
    logger.debug(
        "apply_record_limit: total_found=%d truncated=%s", total_found, truncated
    )

    # ------------------------------------------------------------------
    # Step 9: Format and print STDOUT table
    # ------------------------------------------------------------------
    rows: List[tuple] = []
    for alert in working_alerts:
        labels = alert.get("labels", {})
        alertname: str = labels.get("alertname", "")
        state_val: str = alert.get("state", "")
        active_at_raw: str = alert.get("activeAt", "")
        active_since: str = truncate_iso_timestamp(active_at_raw) if active_at_raw else ""
        rows.append((alertname, state_val, active_since))

    table: str = render_table(rows, headers=["Alert Name", "State", "Active Since"])
    print(table)

    if truncated:
        print(
            f"Note: Output truncated to {max_records} of {total_found} available alerts."
        )
        logger.info(
            "Output truncated: showing %d of %d alerts", max_records, total_found
        )

    # ------------------------------------------------------------------
    # Step 10: Compute output field, status description, and result object
    # ------------------------------------------------------------------
    summary: str = alert_summary(firing_count, pending_count)
    output_fields.update(alert_state=summary)
    logger.debug("alert_state output field set to: %s", summary)

    if total_found > 0:
        status_description: str = (
            f"Success: {firing_count} firing, {pending_count} pending alerts matched the filter"
        )
    else:
        status_description = "Success: No active alerts matching the filter"

    # Extension Output alert_name_filter: value or null
    alert_name_filter_out: Optional[str] = alert_name_input if alert_name_input else None

    # Build alerts list for Extension Output
    alerts_list: List[Dict[str, Any]] = []
    for alert in working_alerts:
        labels = alert.get("labels", {})
        alertname = labels.get("alertname", "")
        state_val = alert.get("state", "")
        active_at_raw = alert.get("activeAt", "")
        active_since = truncate_iso_timestamp(active_at_raw) if active_at_raw else ""
        # Exclude alertname from the labels dict in output (it is surfaced separately)
        remaining_labels: Dict[str, str] = {
            k: v for k, v in labels.items() if k != "alertname"
        }
        alerts_list.append(
            {
                "alertname": alertname,
                "state": state_val,
                "active_since": active_since,
                "labels": remaining_labels,
                "annotations": alert.get("annotations", {}),
            }
        )

    result_obj: Dict[str, Any] = {
        "action": "check_alerts",
        "alert_name_filter": alert_name_filter_out,
        "state_filter": state_filter,
        "total_found": total_found,
        "firing_count": firing_count,
        "pending_count": pending_count,
        "truncated": truncated,
        "alerts": alerts_list,
    }

    # ------------------------------------------------------------------
    # Step 11: Log completion
    # ------------------------------------------------------------------
    print(
        f"Check Alerts completed. {firing_count} firing, "
        f"{pending_count} pending alerts matched the filter."
    )
    logger.info(
        "check_alerts action completed: firing=%d pending=%d total=%d",
        firing_count,
        pending_count,
        total_found,
    )

    return ActionOutput(
        result=result_obj,
        status_description=status_description,
    )
