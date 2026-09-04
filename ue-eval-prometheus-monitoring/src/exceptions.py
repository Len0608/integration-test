"""
Exceptions module template for UAC Universal Extensions.

This module provides:
- Base ExecutionError class
- Standard exception types (DataValidationError, ConnectionError, etc.)
- ErrorManager singleton for error collection
- Exit code conventions

CUSTOMIZE:
- Add custom exception types for your extension
- Modify ErrorManager methods if needed
"""
from typing import Optional

class ExecutionError(Exception):
    """
    The default error raised by an extension.

    All extension errors must inherit from it.

    Attrs:
        exit_code: The exit code of the extension (for UAC)
        message: The error message for status description
    """

    exit_code: int = 1
    message: str = "Execution Failed"

    def __init__(self, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            message: Optional message that will be appended to the default message.

        Note:
            To return result data with errors, use error_manager.set_result()
            before raising the exception.
        """
        if message:
            self.message = f"{self.message}: {message}"

        super().__init__(self.message)

class DataValidationError(ExecutionError):
    """Raised when an input field is invalid."""
    exit_code = 20
    message = "Data Validation Error"

class UnexpectedSystemError(ExecutionError):
    """Raised for unexpected system errors."""
    exit_code = 1
    message = "System Error"


class InputValidationError(ExecutionError):
    """
    Raised when a required input field is missing or empty.

    Use this when validating user-supplied fields before executing an action.
    For example, raise this when prometheus_url, credential, or promql_expression
    are absent or blank. Exit code 20 signals a user input error to UAC.
    """
    exit_code = 20
    message = "Input Validation Error"


class PrometheusConnectionError(ExecutionError):
    """
    Raised when the extension cannot reach the Prometheus server.

    Use this to wrap requests.ConnectionError (network unreachable, DNS
    resolution failure, refused connection). Indicates a transient or
    environment configuration problem rather than a bug in the extension.
    """
    exit_code = 1
    message = "Prometheus Connection Error"


class PrometheusSSLError(ExecutionError):
    """
    Raised when SSL/TLS certificate verification fails for the Prometheus server.

    Use this to wrap requests.exceptions.SSLError. Typically indicates a
    self-signed or expired certificate. Users can disable verification via
    UE_SSL_VERIFY=false in non-production environments.
    """
    exit_code = 1
    message = "Prometheus SSL Error"


class PrometheusTimeoutError(ExecutionError):
    """
    Raised when a request to the Prometheus server exceeds the configured timeout.

    Use this to wrap requests.Timeout. The timeout threshold is controlled by
    the UE_HTTP_TIMEOUT environment variable (default: 30 seconds).
    """
    exit_code = 1
    message = "Prometheus Timeout Error"


class PrometheusAuthenticationError(ExecutionError):
    """
    Raised when the Prometheus server rejects the supplied credentials.

    Use this when an HTTP 401 or HTTP 403 response is received. Indicates
    that the UAC credential record contains an incorrect username or password,
    or that the user lacks permission to access the requested endpoint.
    """
    exit_code = 1
    message = "Prometheus Authentication Error"


class PrometheusQueryError(ExecutionError):
    """
    Raised when the Prometheus server reports an invalid or failed query.

    Use this when an HTTP 400 response is received or when the Prometheus JSON
    response body contains status = "error". The error detail message from the
    Prometheus response should be included to help the user correct their PromQL
    expression.
    """
    exit_code = 1
    message = "Prometheus Query Error"


class PrometheusAPIError(ExecutionError):
    """
    Raised when the Prometheus server returns an unexpected non-2xx HTTP response.

    Use this for HTTP 5xx responses and any other non-2xx status codes that are
    not covered by PrometheusAuthenticationError or PrometheusQueryError.
    Indicates a server-side failure or an unexpected API behaviour.
    """
    exit_code = 1
    message = "Prometheus API Error"
