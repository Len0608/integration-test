"""
Prometheus API Client utility for the Prometheus Monitoring Universal Extension.

Manages all HTTP communication with the Prometheus server, including Basic
Authentication, SSL configuration, timeout enforcement, response validation,
and exception classification.
"""
import logging
import os
from typing import Any

import requests
import requests.exceptions

from exceptions import (
    PrometheusAPIError,
    PrometheusAuthenticationError,
    PrometheusConnectionError,
    PrometheusQueryError,
    PrometheusSSLError,
    PrometheusTimeoutError,
)

logger = logging.getLogger("UNV")


def _read_ssl_verify() -> bool:
    """Return SSL verification flag from UE_SSL_VERIFY environment variable.

    Returns False only when UE_SSL_VERIFY is set to the string "false"
    (case-insensitive). All other values (including absent) return True.
    """
    raw: str = os.environ.get("UE_SSL_VERIFY", "true")
    return raw.strip().lower() != "false"


def _read_timeout() -> int:
    """Return HTTP timeout in seconds from UE_HTTP_TIMEOUT environment variable.

    Defaults to 30 seconds when the variable is absent or not parseable as int.
    """
    raw: str = os.environ.get("UE_HTTP_TIMEOUT", "")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 30


class PrometheusClient:
    """HTTP client for the Prometheus HTTP API v1.

    Reads SSL and timeout configuration from environment variables at
    construction time. Use as a context manager to guarantee that the
    underlying HTTP session is closed after use.

    Usage::

        with PrometheusClient(prometheus_url, username, password) as client:
            data = client.query(promql_expression)

    Attributes:
        base_url:   Prometheus server base URL (no trailing slash).
        ssl_verify: Whether SSL certificate verification is enabled.
        timeout:    Request timeout in seconds.
    """

    def __init__(self, base_url: str, username: str, password: str) -> None:
        """Initialise the client.

        Args:
            base_url:  Base URL of the Prometheus server, e.g.
                       ``http://prometheus.mycompany.com:9090``.
            username:  HTTP Basic Auth username (credential ``user`` attribute).
            password:  HTTP Basic Auth password (credential ``password`` attribute).
        """
        self.base_url: str = base_url.rstrip("/")
        self.ssl_verify: bool = _read_ssl_verify()
        self.timeout: int = _read_timeout()
        self._session: requests.Session = requests.Session()
        self._session.auth = (username, password)
        logger.debug(
            "PrometheusClient initialised: base_url=%s ssl_verify=%s timeout=%d",
            self.base_url,
            self.ssl_verify,
            self.timeout,
        )

    def __enter__(self) -> "PrometheusClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self._session.close()
        logger.debug("PrometheusClient session closed")

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def query(self, promql_expression: str) -> dict[str, Any]:
        """Execute a PromQL instant query against ``/api/v1/query``.

        Args:
            promql_expression: PromQL expression to evaluate.

        Returns:
            The ``data`` object from the Prometheus JSON response.

        Raises:
            PrometheusConnectionError:    Network/DNS failure.
            PrometheusSSLError:           SSL certificate verification failed.
            PrometheusTimeoutError:       Request exceeded the configured timeout.
            PrometheusAuthenticationError: HTTP 401 or 403 received.
            PrometheusQueryError:         HTTP 400 or Prometheus error status.
            PrometheusAPIError:           Other non-2xx HTTP response.
        """
        url: str = f"{self.base_url}/api/v1/query"
        params: dict[str, str] = {"query": promql_expression}
        logger.info("Executing PromQL instant query against %s", url)
        logger.debug("PromQL expression: %s", promql_expression)
        return self._get(url, params=params)

    def alerts(self) -> dict[str, Any]:
        """Retrieve all currently active alerts from ``/api/v1/alerts``.

        Returns:
            The ``data`` object from the Prometheus JSON response.

        Raises:
            PrometheusConnectionError:    Network/DNS failure.
            PrometheusSSLError:           SSL certificate verification failed.
            PrometheusTimeoutError:       Request exceeded the configured timeout.
            PrometheusAuthenticationError: HTTP 401 or 403 received.
            PrometheusAPIError:           Other non-2xx HTTP response.
        """
        url: str = f"{self.base_url}/api/v1/alerts"
        logger.info("Fetching active alerts from %s", url)
        return self._get(url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """Perform an HTTP GET request and return validated response data.

        Args:
            url:    Full request URL.
            params: Optional query parameters.

        Returns:
            The ``data`` object extracted from a successful Prometheus response.

        Raises:
            PrometheusConnectionError:    On network/DNS failure.
            PrometheusSSLError:           On SSL verification failure.
            PrometheusTimeoutError:       On request timeout.
            PrometheusAuthenticationError: On HTTP 401 or 403.
            PrometheusQueryError:         On HTTP 400 or Prometheus error status.
            PrometheusAPIError:           On other non-2xx responses.
        """
        logger.debug("HTTP GET %s params=%s", url, params)
        try:
            response: requests.Response = self._session.get(
                url,
                params=params,
                verify=self.ssl_verify,
                timeout=self.timeout,
            )
        except requests.exceptions.SSLError as exc:
            detail: str = str(exc)
            logger.error("SSL verification failed for %s: %s", url, detail)
            raise PrometheusSSLError(
                f"SSL certificate verification failed for {url}: {detail}"
            )
        except requests.ConnectionError as exc:
            detail = str(exc)
            logger.error("Connection error reaching %s: %s", url, detail)
            raise PrometheusConnectionError(
                f"Unable to connect to Prometheus server at {url}: {detail}"
            )
        except requests.Timeout:
            logger.error(
                "Request to %s timed out after %d seconds", url, self.timeout
            )
            raise PrometheusTimeoutError(
                f"Request to Prometheus timed out after {self.timeout} seconds"
            )

        logger.debug("Response status code: %d", response.status_code)
        logger.debug("Response body: %s", response.text)

        return self._validate_response(url, response)

    def _validate_response(
        self, url: str, response: requests.Response
    ) -> dict[str, Any]:
        """Classify and validate an HTTP response from the Prometheus API.

        Args:
            url:      Request URL (used in error messages).
            response: Raw HTTP response object.

        Returns:
            The ``data`` object from the parsed JSON body on success.

        Raises:
            PrometheusAuthenticationError: On HTTP 401 or 403.
            PrometheusQueryError:         On HTTP 400 or Prometheus error status.
            PrometheusAPIError:           On other non-2xx responses.
        """
        status_code: int = response.status_code

        if status_code in (401, 403):
            logger.error(
                "Authentication failed for %s (HTTP %d)", url, status_code
            )
            raise PrometheusAuthenticationError(
                f"Authentication failed for Prometheus server at {url} (HTTP {status_code})"
            )

        if status_code == 400:
            # Attempt to extract the Prometheus error message from the JSON body.
            prometheus_error: str = self._extract_error_message(response)
            logger.error("Invalid PromQL or bad request at %s: %s", url, prometheus_error)
            raise PrometheusQueryError(
                f"Invalid PromQL expression: {prometheus_error}"
            )

        if status_code >= 300:
            detail: str = response.text[:200]
            logger.error(
                "Prometheus API returned HTTP %d for %s: %s", status_code, url, detail
            )
            raise PrometheusAPIError(
                f"Prometheus API returned HTTP {status_code}: {detail}"
            )

        # 2xx — parse and validate the JSON body.
        try:
            body: dict[str, Any] = response.json()
        except Exception as exc:
            logger.error("Failed to parse JSON response from %s: %s", url, str(exc))
            raise PrometheusAPIError(
                f"Prometheus API returned HTTP {status_code}: {str(exc)}"
            )

        prom_status: str = body.get("status", "")
        if prom_status == "error":
            prometheus_error = body.get("error", "unknown error")
            logger.error(
                "Prometheus responded with status=error for %s: %s",
                url,
                prometheus_error,
            )
            raise PrometheusQueryError(
                f"Invalid PromQL expression: {prometheus_error}"
            )

        data: dict[str, Any] = body.get("data", {})
        logger.debug("Prometheus response data keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
        return data

    def _extract_error_message(self, response: requests.Response) -> str:
        """Attempt to extract the ``error`` field from a Prometheus JSON error body.

        Falls back to the raw response text if JSON parsing fails.

        Args:
            response: Raw HTTP response object.

        Returns:
            Error detail string.
        """
        try:
            body: dict[str, Any] = response.json()
            return body.get("error", response.text[:200])
        except Exception:
            return response.text[:200]
