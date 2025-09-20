"""URL routing for the PMKSY wizard app."""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "pmksy"

urlpatterns = [
    path("", views.wizard_view, name="wizard"),
    path("step/<str:step>/", views.wizard_view, name="wizard-step"),
]
