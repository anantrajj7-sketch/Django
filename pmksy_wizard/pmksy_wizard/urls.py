"""URL configuration for pmksy_wizard project."""
from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("datawizard/", include("data_wizard.urls")),
    path("", include("pmksy.urls", namespace="pmksy")),
]
