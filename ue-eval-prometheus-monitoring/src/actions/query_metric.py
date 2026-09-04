"""Query Metric action for the Prometheus Monitoring Universal Extension.

Executes a PromQL instant query against the Prometheus /api/v1/query endpoint
and returns matching metric series up to the UE_MAX_OUTPUT_RECORDS limit.
"""

import logging
import os
from typing import Any, Dict, List

from actions.output import ActionOutput
from exceptions import InputValidationError
from fields.input import InputFields
from fields.output import OutputFields
from manager import ExtensionManager
from utility import (
    PrometheusClient,
    apply_record_limit,
    epoch_to_iso,
    format_metric_label,
    metric_summary,
    render_table,
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


def query_metric(input_data: InputFields) -> ActionOutput:
    """Execute a PromQL instant query and return matching metric series.

    Args:
        input_data: Validated input fields containing prometheus_url,
                    credential, and promql_expression.

    Returns:
        ActionOutput with structured result dict and status_description.

    Raises:
        InputValidationError:         Missing or empty required input field.
        PrometheusConnectionError:    Network/DNS failure reaching Prometheus.
        PrometheusSSLError:           SSL certificate verification failure.
        PrometheusTimeoutError:       Request exceeded configured timeout.
        PrometheusAuthenticationError: HTTP 401 or 403 from Prometheus.
        PrometheusQueryError:         Invalid PromQL (HTTP 400 or status=error).
        PrometheusAPIError:           Unexpected non-2xx HTTP response.
    """
    logger.info("Starting query_metric action")

    # ------------------------------------------------------------------
    # Step 1: Input validation
    # ------------------------------------------------------------------
    if not input_data.prometheus_url or not input_data.prometheus_url.value:
        logger.error("prometheus_url is missing or empty")
        raise InputValidationError("Error: Prometheus URL is required")

    if input_data.credential is None:
        logger.error("credential is missing")
        raise InputValidationError("Error: Credential is required")

    if not input_data.promql_expression or not input_data.promql_expression.value:
        logger.error("promql_expression is missing or empty")
        raise InputValidationError("Error: PromQL Expression is required")

    prometheus_url: str = input_data.prometheus_url.value
    username: str = input_data.credential.user
    password: str = input_data.credential.password
    promql_expression: str = input_data.promql_expression.value

    logger.debug(
        "query_metric inputs: prometheus_url=%s promql_expression=%s",
        prometheus_url,
        promql_expression,
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
    output_fields.update(metric_values="Querying...")

    print(f"Starting Query Metric action against {prometheus_url}")
    logger.info("Executing PromQL query: %s", promql_expression)

    # ------------------------------------------------------------------
    # Step 4 & 5: Execute instant query and parse response
    # ------------------------------------------------------------------
    with PrometheusClient(prometheus_url, username, password) as client:
        data: Dict[str, Any] = client.query(promql_expression)

    raw_results: List[Dict[str, Any]] = data.get("result", [])
    logger.info("Prometheus returned %d series", len(raw_results))

    # ------------------------------------------------------------------
    # Step 6: Apply output record limit
    # ------------------------------------------------------------------
    working_results, total_count, truncated = apply_record_limit(raw_results, max_records)
    logger.debug(
        "apply_record_limit: total_count=%d truncated=%s", total_count, truncated
    )

    # ------------------------------------------------------------------
    # Step 7: Format and print STDOUT table
    # ------------------------------------------------------------------
    rows: List[tuple] = []
    float_values: List[float] = []

    for item in working_results:
        metric_dict: Dict[str, str] = item.get("metric", {})
        value_pair = item.get("value", [0, "0"])
        epoch: float = float(value_pair[0])
        value_str: str = str(value_pair[1])
        value_float: float = float(value_str)
        timestamp: str = epoch_to_iso(epoch)
        metric_label: str = format_metric_label(metric_dict)

        float_values.append(value_float)
        rows.append((metric_label, value_float, timestamp))

    table: str = render_table(rows, headers=["Metric", "Value", "Timestamp"])
    print(table)

    if truncated:
        print(f"Note: Output truncated to {max_records} of {total_count} available series.")
        logger.info(
            "Output truncated: showing %d of %d series", max_records, total_count
        )

    # ------------------------------------------------------------------
    # Step 8: Compute output field, status description, and result object
    # ------------------------------------------------------------------
    summary: str = metric_summary(total_count, float_values)
    output_fields.update(metric_values=summary)
    logger.debug("metric_values output field set to: %s", summary)

    if total_count > 0:
        status_description: str = (
            f"Success: {total_count} series returned for the expression"
        )
    else:
        status_description = "Success: 0 metric series returned for the expression"

    # Build results list for Extension Output
    results_list: List[Dict[str, Any]] = []
    for item in working_results:
        metric_dict = item.get("metric", {})
        value_pair = item.get("value", [0, "0"])
        results_list.append(
            {
                "metric": metric_dict,
                "value": float(str(value_pair[1])),
                "timestamp": epoch_to_iso(float(value_pair[0])),
            }
        )

    result_obj: Dict[str, Any] = {
        "action": "query_metric",
        "promql_expression": promql_expression,
        "result_count": total_count,
        "truncated": truncated,
        "results": results_list,
    }

    # ------------------------------------------------------------------
    # Step 9: Log completion
    # ------------------------------------------------------------------
    print(f"Query Metric completed. {total_count} series returned.")
    logger.info("query_metric action completed: %d series returned", total_count)

    return ActionOutput(
        result=result_obj,
        status_description=status_description,
    )
