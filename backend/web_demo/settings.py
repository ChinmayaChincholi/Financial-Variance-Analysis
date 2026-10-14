"""
Configuration for the hosted web demo, read from environment variables.

Every value has a safe default, so the demo works with no configuration at
all. Invalid values fail fast at startup with a clear message instead of
silently falling back to something unexpected.
"""

import os
from dataclasses import dataclass

MODE_ENV = "VARIANCE_STUDIO_MODE"

MAX_UPLOAD_MB_ENV = "VARIANCE_STUDIO_MAX_UPLOAD_MB"
RETENTION_HOURS_ENV = "VARIANCE_STUDIO_RETENTION_HOURS"
MAX_WORKSPACES_ENV = "VARIANCE_STUDIO_MAX_WORKSPACES"
MAX_CONCURRENT_JOBS_ENV = "VARIANCE_STUDIO_MAX_CONCURRENT_JOBS"

_MB = 1024 * 1024


def _read_number(name: str, default: float, minimum: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}.") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum:g}, got {raw!r}.")
    return value


@dataclass(frozen=True)
class WebSettings:
    # Largest Excel file a visitor may upload.
    max_upload_bytes: int = 50 * _MB
    # Largest request body for every other endpoint (for example, the Excel
    # export posts the rows of an already-computed table).
    max_api_body_bytes: int = 50 * _MB
    # Visitor data is deleted after this many hours without activity.
    retention_hours: float = 24.0
    # Saved analyses kept per visitor; the least recently opened are dropped.
    max_workspaces: int = 10
    # Upload/processing requests allowed to run at the same time.
    max_concurrent_jobs: int = 2
    # How often the background sweep looks for expired visitor data.
    cleanup_interval_seconds: int = 900
    # Lifetime of the anonymous visitor cookie.
    cookie_max_age_seconds: int = 30 * 24 * 3600

    @property
    def max_upload_mb(self) -> float:
        return self.max_upload_bytes / _MB

    @classmethod
    def from_env(cls) -> "WebSettings":
        return cls(
            max_upload_bytes=int(
                _read_number(MAX_UPLOAD_MB_ENV, 50, 0.1) * _MB
            ),
            retention_hours=_read_number(RETENTION_HOURS_ENV, 24, 0.1),
            max_workspaces=int(_read_number(MAX_WORKSPACES_ENV, 10, 1)),
            max_concurrent_jobs=int(
                _read_number(MAX_CONCURRENT_JOBS_ENV, 2, 1)
            ),
        )


def is_web_mode() -> bool:
    """True when VARIANCE_STUDIO_MODE=web; the default is the desktop mode."""
    value = os.environ.get(MODE_ENV, "desktop").strip().lower()
    if value in ("", "desktop"):
        return False
    if value == "web":
        return True
    raise ValueError(f"{MODE_ENV} must be 'desktop' or 'web', got {value!r}.")