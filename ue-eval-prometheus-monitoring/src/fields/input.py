"""InputFields dataclass for input parsing and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, Dict, List, get_type_hints, Union, get_origin, get_args
from fields.output import OutputFields
from fields.types import (
    Text,
    Integer,
    Float,
    Boolean,
    SingleChoice,
    MultiChoice,
    Credential,
    Script,
    Array,
)
from exceptions import DataValidationError
from manager import ExtensionManager
from dataclasses import fields as dataclass_fields
from dataclasses import asdict

extension_manager = ExtensionManager()


@dataclass
class InputFields:
    """Input fields from UAC with validation.

    Fields correspond 1:1 with template.json fields for the Prometheus
    Monitoring extension. All user-defined fields are Optional — UAC
    Controller enforces required field validation at the UI level.

    Fields:
        action: Operation to perform (Query Metric or Check Alerts).
        prometheus_url: Base URL of the Prometheus server.
        credential: UAC Credential providing HTTP Basic Auth credentials.
        promql_expression: PromQL expression for the Query Metric action.
        alert_name: Optional exact alertname filter for Check Alerts.
        alert_state_filter: State filter choice for Check Alerts (All/Firing/Pending).
        previous_output: Auto-populated on re-runs from prior OutputFields.
        _skip_validation: Internal flag to bypass __post_init__ validation.
    """

    # User-defined fields — ALWAYS Optional, even if required in template.json
    action: Optional[SingleChoice] = None
    prometheus_url: Optional[Text] = None
    credential: Optional[Credential] = None
    promql_expression: Optional[Text] = None
    alert_name: Optional[Text] = None
    alert_state_filter: Optional[SingleChoice] = None

    # Previous run output (auto-populated for re-runs)
    previous_output: Optional[OutputFields] = None

    # Skip validation flag (internal use only)
    _skip_validation: bool = False

    @staticmethod
    def preprocess_fields(fields: dict) -> dict:
        """Preprocess raw UAC fields before creating InputFields.

        Converts raw UAC values to wrapper type instances:
        1. Filters out flattened credential fields (containing dots)
        2. Wraps values in appropriate wrapper types based on field type hints
        3. Extracts previous OutputFields if present (from re-runs)
        """

        processed = {}
        previous_output_data = {}

        # Get all OutputFields field names for detection
        output_field_names = {f.name for f in dataclass_fields(OutputFields)}

        # Get type hints to detect wrapper types
        type_hints = get_type_hints(InputFields)

        # Map field names to their wrapper types
        field_wrapper_types = {}
        for field_name, field_type in type_hints.items():
            # Get base type (unwrap Optional)
            base_type = field_type
            if get_origin(field_type) is Union:
                args = get_args(field_type)
                # Filter out NoneType to get the actual type
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    base_type = non_none_args[0]

            field_wrapper_types[field_name] = base_type

        for key, value in fields.items():
            # Skip flattened credential fields (e.g., "credential.token")
            if "." in key:
                continue

            # Check if this field belongs to OutputFields (previous run data)
            if key in output_field_names:
                previous_output_data[key] = value
                continue

            # Skip None values
            if value is None:
                processed[key] = value
                continue

            # Get the wrapper type for this field
            wrapper_type = field_wrapper_types.get(key)

            # Convert to appropriate wrapper type
            if wrapper_type == SingleChoice:
                # UAC sends as list, SingleChoice expects list
                if isinstance(value, list):
                    value = SingleChoice(_values=value)
                else:
                    value = SingleChoice(_values=[value])

            elif wrapper_type == MultiChoice:
                # UAC sends as list, MultiChoice expects list
                if isinstance(value, list):
                    value = MultiChoice(values=value)
                else:
                    value = MultiChoice(values=[value])

            elif wrapper_type == Script:
                # UAC sends as string path, Script expects Path object
                if isinstance(value, str):
                    value = Script(path=Path(value))

            elif wrapper_type == Credential:
                # UAC sends as dict, Credential expects kwargs
                if isinstance(value, dict):
                    value = Credential.from_dict(value)

            elif wrapper_type == Text:
                # Wrap string in Text
                if isinstance(value, str):
                    value = Text(value=value)

            elif wrapper_type == Integer:
                # Wrap int in Integer
                if isinstance(value, int):
                    value = Integer(value=value)

            elif wrapper_type == Float:
                # Wrap float in Float
                if isinstance(value, (int, float)):
                    value = Float(value=float(value))

            elif wrapper_type == Boolean:
                # Wrap bool in Boolean
                if isinstance(value, bool):
                    value = Boolean(value=value)

            elif wrapper_type == Array:
                # UAC sends as list of dicts, Array expects list of dicts
                if isinstance(value, list):
                    value = Array(pairs=value)

            processed[key] = value

        # If we found previous output fields, create OutputFields instance
        if previous_output_data:
            # Wrap Text fields in previous output
            for key, val in previous_output_data.items():
                if isinstance(val, str):
                    previous_output_data[key] = Text(value=val)
            processed["previous_output"] = OutputFields(**previous_output_data)

        return processed

    def to_dict(self) -> dict:
        """Convert to dict, unwrapping wrapper types and excluding internal fields.

        Returns:
            Dict with unwrapped field values, excluding _skip_validation and None previous_output
        """

        data = asdict(self)

        # Unwrap wrapper types to their raw values
        result = {}
        for key, value in data.items():
            # Skip internal fields
            if key == "_skip_validation":
                continue

            # Skip None previous_output
            if key == "previous_output" and value is None:
                continue

            # Unwrap wrapper types
            if isinstance(value, dict):
                # Check if it's a wrapper type dict representation
                if "_values" in value:  # SingleChoice
                    result[key] = value["_values"]
                elif "values" in value and len(value) == 1:  # MultiChoice
                    result[key] = value["values"]
                elif "value" in value and len(value) == 1:  # Text, Integer, Float, Boolean
                    result[key] = value["value"]
                elif "path" in value:  # Script
                    result[key] = str(value["path"])
                elif "pairs" in value:  # Array
                    result[key] = value["pairs"]
                elif "user" in value:  # Credential
                    result[key] = value
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    def __post_init__(self):
        """Validate fields after initialization."""
        if self._skip_validation:
            return

        self._validate_action()
        self._validate_prometheus_url()
        self._validate_promql_expression()
        self._validate_alert_state_filter()

        # Raise once if errors collected
        if extension_manager.has_errors():
            raise DataValidationError(
                f"Validation failed with {extension_manager.error_count()} error(s)"
            )

    def _validate_action(self):
        """Validate action field — must be one of the defined choices."""
        if self.action is not None:
            valid_actions = ["Query Metric", "Check Alerts"]
            if self.action.value not in valid_actions:
                exc = DataValidationError(
                    f"Invalid action '{self.action.value}'. Valid actions: {', '.join(valid_actions)}"
                )
                extension_manager.add_error(exc, field="action", value=self.action.value)

    def _validate_prometheus_url(self):
        """Validate prometheus_url — must not be empty when provided."""
        if self.prometheus_url is not None and self.prometheus_url.value == "":
            exc = DataValidationError("prometheus_url must not be empty")
            extension_manager.add_error(exc, field="prometheus_url")

    def _validate_promql_expression(self):
        """Validate promql_expression — required when action is Query Metric.

        UAC sends empty strings for hidden fields; check for both None and empty.
        Only validate when the Query Metric action is selected.
        """
        if self.action and self.action.value == "Query Metric":
            if not self.promql_expression or self.promql_expression.value == "":
                exc = DataValidationError(
                    "promql_expression is required when action is Query Metric"
                )
                extension_manager.add_error(exc, field="promql_expression")

    def _validate_alert_state_filter(self):
        """Validate alert_state_filter — required and must be valid when action is Check Alerts.

        Only validate when the Check Alerts action is selected.
        """
        if self.action and self.action.value == "Check Alerts":
            if self.alert_state_filter is not None:
                valid_states = ["All", "Firing", "Pending"]
                if self.alert_state_filter.value not in valid_states:
                    exc = DataValidationError(
                        f"Invalid alert_state_filter '{self.alert_state_filter.value}'. "
                        f"Valid values: {', '.join(valid_states)}"
                    )
                    extension_manager.add_error(
                        exc, field="alert_state_filter", value=self.alert_state_filter.value
                    )
