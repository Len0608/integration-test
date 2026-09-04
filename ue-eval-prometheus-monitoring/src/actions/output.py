"""ActionOutput dataclass for Prometheus Monitoring action return values."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionOutput:
    """Output from Prometheus Monitoring action functions.

    Carries the structured result dict for Extension Output and the
    status_description string that extension.py writes to unv_output.
    There are no user-selectable stdout_options or output_options control
    fields in this extension, so print_output() always prints everything
    and to_dict() always returns the full result.

    Fields:
        result:             Structured result object included under the
                            ``result`` key of Extension Output.
        status_description: Human-readable completion summary written to
                            ``status_description`` in Extension Output.
        stdout_options:     Unused control list — kept for API compatibility;
                            always an empty list (print everything).
        output_options:     Unused control list — kept for API compatibility;
                            always an empty list (include everything).
    """

    result: Optional[Dict[str, Any]] = None
    status_description: Optional[str] = None

    # No user-controlled choice fields exist in this template.
    # These lists remain empty; print_output() and to_dict() treat an
    # empty list as "include everything" per the ActionOutput contract.
    stdout_options: List[str] = None
    output_options: List[str] = None

    def __post_init__(self) -> None:
        """Initialise control fields with empty-list defaults."""
        if self.stdout_options is None:
            self.stdout_options = []
        if self.output_options is None:
            self.output_options = []

    def print_output(self) -> None:
        """Print the result to STDOUT.

        No stdout_options control fields exist in this extension, so the
        full result is always printed. Callers (action functions) are
        responsible for printing action-specific tables and summary lines
        directly to STDOUT during execution; this method prints the final
        structured result dict as supplementary information when present.
        """
        if self.result:
            import json
            print("\n--- Extension Output Result ---")
            print(json.dumps(self.result, indent=2, default=str))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Extension Output (unv_output).

        No output_options control fields exist in this extension, so the
        full result dict is always returned.

        Returns:
            Dict containing the ``result`` key when a result is present,
            otherwise an empty dict.
        """
        output: Dict[str, Any] = {}
        if self.result is not None:
            output["result"] = self.result
        return output
