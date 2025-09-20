
"""URL routing for the PMKSY import experience."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "pmksy"

urlpatterns = [

    path("", views.wizard_view, name="wizard"),
    path("step/<str:step>/", views.wizard_view, name="wizard-step"),
    path("import/", views.bulk_import_wizard_view, name="import"),
    path(
        "import/preview/",
        views.bulk_import_wizard_view,
        {"step": "preview"},
        name="import-preview",
    ),
]
