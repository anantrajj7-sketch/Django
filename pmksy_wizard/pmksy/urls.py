"""URL routing for the PMKSY import experience."""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "pmksy"

urlpatterns = [
    path("", views.ImportLandingView.as_view(), name="home"),
    path("imports/<slug:wizard_slug>/", views.PMKSYImportWizard.as_view(), name="import-run"),
]
