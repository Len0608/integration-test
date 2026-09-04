"""
Result Formatter utility for the Prometheus Monitoring Universal Extension.

Transforms raw Prometheus API response data into display-ready formats for
STDOUT (ASCII tables) and Extension Output (structured dicts), and computes
summary strings for output-only fields visible in the UAC task list view.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any

from tabulate import tabulate

logger = logging.getLogger("UNV")

# Pattern to strip sub-second precision from ISO 8601 timestamps, e.g.:
#   "2026-09-04T09:45:00.123456789Z"  →  "2026-09-04T09:45:00Z"
_SUBSECOND_PATTERN: re.Pattern[str] = re.compile(r"\.\d+Z$")


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def epoch_to_iso(epoch: float) -> str:
    """Convert a Unix epoch float to an ISO 8601 UTC string at whole-second precision.

    Args:
        epoch: Unix timestamp in seconds (float), as returned by Prometheus
               in the ``value[0]`` position of a query result.

    Returns:
        ISO 8601 UTC string truncated to whole seconds, e.g.
        ``"2026-09-04T10:00:00Z"``.
    """
    dt: datetime = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    result: str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.debug("epoch_to_iso: %s -> %s", epoch, result)
    return result


def truncate_iso_timestamp(iso_string: str) -> str:
    """Strip sub-second precision from an ISO 8601 UTC timestamp string.

    Handles nanosecond timestamps returned by Prometheus in the ``activeAt``
    field of alert objects, e.g. ``"2026-09-04T09:45:00.123456789Z"``.

    Args:
        iso_string: ISO 8601 UTC timestamp string, with or without sub-second
                    precision. Must end with ``Z``.

    Returns:
        ISO 8601 UTC string truncated to whole seconds, e.g.
        ``"2026-09-04T09:45:00Z"``.
    """
    result: str = _SUBSECOND_PATTERN.sub("Z", iso_string)
    logger.debug("truncate_iso_timestamp: %s -> %s", iso_string, result)
    return result


# ---------------------------------------------------------------------------
# Metric label formatting
# ---------------------------------------------------------------------------

def format_metric_label(metric: dict[str, str]) -> str:
    """Format a Prometheus metric label dict as a selector string.

    The ``__name__`` key is used as the base metric name. All remaining
    label pairs are formatted as ``{key="value",key2="value2"}`` and
    appended directly to the base name.  If ``__name__`` is absent, all
    labels are rendered inside braces with no prefix.  If the dict is
    empty, an empty string is returned.

    Args:
        metric: Prometheus metric dict, e.g.
                ``{"__name__": "node_cpu_seconds_total", "mode": "idle"}``.

    Returns:
        Formatted selector string, e.g.
        ``'node_cpu_seconds_total{mode="idle"}'``.
    """
    if not metric:
        return ""

    base_name: str = metric.get("__name__", "")
    labels: dict[str, str] = {k: v for k, v in metric.items() if k != "__name__"}

    if not labels:
        result: str = base_name
    else:
        label_str: str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        result = f"{base_name}{{{label_str}}}"

    logger.debug("format_metric_label: %s -> %s", metric, result)
    return result


# ---------------------------------------------------------------------------
# Output record limiting
# ---------------------------------------------------------------------------

def apply_record_limit(
    items: list[Any], limit: int
) -> tuple[list[Any], int, bool]:
    """Apply an output record limit to a list of items.

    Args:
        items: The full list of results to limit.
        limit: Maximum number of items to retain.

    Returns:
        A three-element tuple:
            - Truncated list (first ``limit`` elements, or full list if
              ``len(items) <= limit``).
            - Total count of items before truncation.
            - Boolean indicating whether truncation occurred.
    """
    total_count: int = len(items)
    if total_count > limit:
        logger.debug(
            "apply_record_limit: truncating %d items to %d", total_count, limit
        )
        return items[:limit], total_count, True
    return items, total_count, False


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

def render_table(rows: list[tuple[Any, ...]], headers: list[str]) -> str:
    """Render tabular data as an ASCII table using the ``rounded_outline`` format.

    Args:
        rows:    List of row tuples, one tuple per data row.
        headers: Column header strings, aligned by position with each tuple.

    Returns:
        Formatted ASCII table string suitable for printing to STDOUT.
    """
    logger.debug(
        "render_table: %d rows, headers=%s", len(rows), headers
    )
    return tabulate(rows, headers=headers, tablefmt="rounded_outline")


# ---------------------------------------------------------------------------
# Summary string helpers
# ---------------------------------------------------------------------------

def metric_summary(total_count: int, values: list[float]) -> str:
    """Build the ``metric_values`` output field summary string.

    Args:
        total_count: Total number of metric series returned by Prometheus
                     before any truncation.
        values:      Float values from the working (possibly truncated)
                     results set. Used to compute min/max range.

    Returns:
        Summary string, e.g. ``"3 series, values: 0.12–0.85"`` or
        ``"0 series returned"``.
    """
    if total_count == 0:
        return "0 series returned"
    min_val: float = min(values)
    max_val: float = max(values)
    result: str = f"{total_count} series, values: {min_val}–{max_val}"
    logger.debug(
        "metric_summary: total_count=%d min=%s max=%s -> %s",
        total_count,
        min_val,
        max_val,
        result,
    )
    return result


def alert_summary(firing_count: int, pending_count: int) -> str:
    """Build the ``alert_state`` output field summary string.

    Args:
        firing_count:  Number of firing alerts (from all filtered results,
                       before truncation).
        pending_count: Number of pending alerts (from all filtered results,
                       before truncation).

    Returns:
        Summary string, e.g. ``"2 firing, 0 pending"`` or
        ``"No active alerts"``.
    """
    if firing_count + pending_count == 0:
        return "No active alerts"
    result: str = f"{firing_count} firing, {pending_count} pending"
    logger.debug(
        "alert_summary: firing=%d pending=%d -> %s",
        firing_count,
        pending_count,
        result,
    )
    return result
