"""OutputFields dataclass for real-time UI updates."""

from dataclasses import dataclass, asdict
from typing import Optional
from universal_extension import ui
from fields.types import Text


@dataclass
class OutputFields:
    """Real-time output fields for UAC UI updates.

    These fields correspond to the Output Only fields defined in template.json
    for the Prometheus Monitoring extension. They sync with the UAC UI in
    real-time during execution and are visible in the UAC task list view.

    Fields:
        metric_values: Summary of metric query results (Query Metric action).
            Example: "3 series, values: 0.12-0.85" or "0 series returned".
        alert_state: Summary of alert counts by state (Check Alerts action).
            Example: "2 firing, 0 pending" or "No active alerts".
    """

    # Output fields matching template.json Output Only fields
    metric_values: Optional[Text] = None
    alert_state: Optional[Text] = None

    def update(self, **fields):
        """Update fields and sync with UAC UI in real-time.

        Args:
            **fields: Field names and values to update (strings will be wrapped in Text)
        """
        for field_name, field_value in fields.items():
            if hasattr(self, field_name):
                # Wrap string values in Text type
                if isinstance(field_value, str):
                    field_value = Text(field_value)
                setattr(self, field_name, field_value)
        ui.update_output_fields(fields)

    def to_dict(self) -> dict:
        """Get current fields as dictionary.

        Returns:
            Dict with non-None field values (Text wrappers unwrapped to strings)
        """
        result = {}
        for k, v in asdict(self).items():
            if v is not None:
                # Extract value from Text wrapper
                result[k] = v.value if isinstance(v, Text) else v
        return result

    def clear(self):
        """Reset all fields to None."""
        self.metric_values = None
        self.alert_state = None
