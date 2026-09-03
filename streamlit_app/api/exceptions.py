from __future__ import annotations


class BackendError(Exception):
    """A user-safe error raised for any failed backend call.

    ``message`` is always safe to show directly in the UI -- no raw
    tracebacks or provider error bodies are ever surfaced to the caller.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        is_timeout: bool = False,
        is_connection: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after
        self._is_timeout = is_timeout
        self._is_connection = is_connection

    @property
    def is_quota_error(self) -> bool:
        return self.status_code == 429

    @property
    def is_timeout_error(self) -> bool:
        return self._is_timeout

    @property
    def is_connection_error(self) -> bool:
        if self._is_timeout:
            return False
        return self._is_connection or (self.status_code is None)
