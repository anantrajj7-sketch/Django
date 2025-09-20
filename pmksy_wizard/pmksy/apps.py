from __future__ import annotations

from django.apps import AppConfig


class PmksyConfig(AppConfig):
    """Application configuration for the PMKSY survey wizard."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "pmksy"
