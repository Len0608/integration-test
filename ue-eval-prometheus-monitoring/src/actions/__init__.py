"""Actions module — business logic implementations for the Prometheus Monitoring extension."""

from actions.output import ActionOutput
from actions.query_metric import query_metric
from actions.check_alerts import check_alerts
from manager import ExtensionManager

extension_manager = ExtensionManager()

# Maps the action field value (as supplied by UAC) to the action function.
ACTION_MAPPER = {
    "Query Metric": query_metric,
    "Check Alerts": check_alerts,
}
