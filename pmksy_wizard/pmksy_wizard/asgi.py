"""ASGI config for pmksy_wizard project."""
from __future__ import annotations

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pmksy_wizard.settings")

application = get_asgi_application()
