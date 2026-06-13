# content_generation_context.py
"""Policy and abort signals for content generation (decoupled from GUI)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ContentGenerationContext:
    """Snapshot of settings plus live abort checks via the GUI reference."""

    security_enabled: bool = False
    max_file_size: Optional[int] = None
    sanitize_urls: bool = False
    gui: Optional[Any] = field(default=None, repr=False)

    def should_abort_shutdown(self) -> bool:
        if self.gui is None:
            return False
        return bool(getattr(self.gui, "_shutdown_requested", False))

    def should_abort_cancel(self) -> bool:
        if self.gui is None:
            return False
        return bool(getattr(self.gui, "_scan_cancel_requested", False))


def build_content_context_from_gui(gui: Any) -> ContentGenerationContext:
    """Build generation policy from ``gui.settings`` and abort flags on ``gui``."""
    settings = getattr(gui, "settings", None)
    if settings is None:
        return ContentGenerationContext(gui=gui)

    security_enabled = settings.security_enabled()
    return ContentGenerationContext(
        security_enabled=security_enabled,
        max_file_size=settings.max_file_size_bytes() if security_enabled else None,
        sanitize_urls=settings.sanitize_urls_enabled(),
        gui=gui,
    )
