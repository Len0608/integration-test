"""
Utility package for the Prometheus Monitoring Universal Extension.

Modules:
    prometheus_client  — HTTP communication with the Prometheus API
    formatter          — Result formatting, timestamp conversion, and summary strings
"""
from utility.prometheus_client import PrometheusClient
from utility.formatter import (
    format_metric_label,
    apply_record_limit,
    render_table,
    epoch_to_iso,
    truncate_iso_timestamp,
    metric_summary,
    alert_summary,
)

__all__ = [
    "PrometheusClient",
    "format_metric_label",
    "apply_record_limit",
    "render_table",
    "epoch_to_iso",
    "truncate_iso_timestamp",
    "metric_summary",
    "alert_summary",
]
