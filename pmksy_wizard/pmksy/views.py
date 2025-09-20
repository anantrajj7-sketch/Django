
"""Views providing a django-data-wizard powered import interface."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from django import forms as django_forms
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import TemplateView

from . import forms, importers, models


class SurveyWizardView(View):
    """Simple session-backed multi-step wizard."""

    template_name = "pmksy/wizard_form.html"
    success_template = "pmksy/wizard_done.html"

    STEP_CONFIG: Dict[str, Dict[str, Any]] = {
        "farmer": {
            "title": "Farmer profile",
            "description": "Capture household level demographics and contact details.",
            "form": forms.FarmerForm,
        },
        "land": {
            "title": "Land & assets",
            "description": "Describe land parcels and physical assets owned by the household.",
            "formsets": {
                "land_holdings": (forms.LandHoldingFormSet, "Land holdings"),
                "assets": (forms.AssetFormSet, "Assets"),
            },
        },
        "production": {
            "title": "Crop production",
            "description": "Capture crop history, input management and realised income.",
            "formsets": {
                "crop_history": (forms.CropHistoryFormSet, "Crop history"),
                "cost_cultivation": (forms.CostOfCultivationFormSet, "Cost of cultivation"),
                "water_management": (forms.WaterManagementFormSet, "Water management"),
                "pest_disease": (forms.PestDiseaseFormSet, "Pest & disease"),
                "nutrient_management": (forms.NutrientManagementFormSet, "Nutrient management"),
                "income_crops": (forms.IncomeFromCropsFormSet, "Income from crops"),
                "irrigated_rainfed": (forms.IrrigatedRainfedFormSet, "Irrigated vs rainfed"),
            },
        },
        "livelihoods": {
            "title": "Enterprises & livelihoods",
            "description": "Collect livelihood diversification and consumption details.",
            "formsets": {
                "enterprises": (forms.EnterpriseFormSet, "Allied enterprises"),
                "annual_income": (forms.AnnualIncomeFormSet, "Annual family income"),
                "consumption": (forms.ConsumptionPatternFormSet, "Consumption pattern"),
                "market_price": (forms.MarketPriceFormSet, "Market price"),
            },
        },
        "resilience": {
            "title": "Resilience & finance",
            "description": "Document migration, adaptation strategies and access to finance.",
            "form": forms.FinancialRecordForm,
            "formsets": {
                "migration": (forms.MigrationFormSet, "Migration"),
                "adaptation": (forms.AdaptationStrategyFormSet, "Adaptation strategies"),
            },
        },
    }

    STEP_ORDER: Tuple[str, ...] = tuple(STEP_CONFIG.keys())


from data_wizard import importers
from data_wizard.sources import FileSource
from data_wizard.views import ImportWizard

from . import serializers


WizardConfig = Dict[str, Any]


def _wizard(
    label: str,
    serializer: type,
    *,
    description: str,
    help_text: str | None = None,
    title: str | None = None,
) -> WizardConfig:
    """Helper to build wizard metadata entries."""

    return {
        "slug": label,
        "serializer": serializer,
        "title": title or label.replace("_", " ").title(),
        "description": description,
        "help_text": help_text,
    }


WIZARDS: List[WizardConfig] = [
    _wizard(
        "farmers",
        serializers.FarmerSerializer,
        description="Import core farmer demographics and household composition records.",
        help_text="Each row should uniquely identify a farmer via the farmer_id column.",
        title="Farmer Profiles",
    ),
    _wizard(
        "land_holdings",
        serializers.LandHoldingSerializer,
        description="Bulk upload land parcel details including irrigation sources and coordinates.",
        title="Land Holdings",
    ),
    _wizard(
        "assets",
        serializers.AssetSerializer,
        description="Capture agricultural and household assets owned by each farmer.",
        title="Assets",
    ),
    _wizard(
        "crop_history",
        serializers.CropHistorySerializer,
        description="Historical crop production statistics such as area, yield and usage distribution.",
        title="Crop History",
    ),
    _wizard(
        "cost_of_cultivation",
        serializers.CostOfCultivationSerializer,
        description="Cost line items for each crop including quantity and expenditure.",
        title="Cost of Cultivation",
    ),
    _wizard(
        "weed_records",
        serializers.WeedRecordSerializer,
        description="Information about weed management practices, labour and chemical usage.",
        title="Weed Management",
    ),
    _wizard(
        "water_management",
        serializers.WaterManagementSerializer,
        description="Water source utilisation patterns, irrigation counts and costs.",
        title="Water Management",
    ),
    _wizard(
        "pest_disease",
        serializers.PestDiseaseRecordSerializer,
        description="Pest and disease management measures applied across seasons.",
        title="Pest & Disease",
    ),
    _wizard(
        "nutrient_management",
        serializers.NutrientManagementSerializer,
        description="Fertiliser and nutrient application for each crop and season.",
        title="Nutrient Management",
    ),
    _wizard(
        "income_from_crops",
        serializers.IncomeFromCropsSerializer,
        description="Gross and by-product income statistics for cultivated crops.",
        title="Income from Crops",
    ),
    _wizard(
        "enterprises",
        serializers.EnterpriseSerializer,
        description="Allied enterprises operated by the household and their production outputs.",
        title="Enterprises",
    ),
    _wizard(
        "annual_family_income",
        serializers.AnnualFamilyIncomeSerializer,
        description="Annual income contributions from agriculture and non-farm sources.",
        title="Annual Family Income",
    ),
    _wizard(
        "migration_records",
        serializers.MigrationRecordSerializer,
        description="Household migration patterns, reasons and remittance flows.",
        title="Migration",
    ),
    _wizard(
        "adaptation_strategies",
        serializers.AdaptationStrategySerializer,
        description="Awareness and adoption of climate adaptation practices.",
        title="Adaptation Strategies",
    ),
    _wizard(
        "financial_records",
        serializers.FinancialRecordSerializer,
        description="Financial inclusion indicators, access to credit and institutional support.",
        title="Financial Inclusion",
    ),
    _wizard(
        "consumption_patterns",
        serializers.ConsumptionPatternSerializer,
        description="Monthly consumption and procurement of agricultural produce.",
        title="Consumption Patterns",
    ),
    _wizard(
        "market_prices",
        serializers.MarketPriceSerializer,
        description="Market price realisation for crops across seasons.",
        title="Market Prices",
    ),
    _wizard(
        "irrigated_rainfed",
        serializers.IrrigatedRainfedSerializer,
        description="Breakdown of irrigated versus rainfed areas and crop calendars.",
        title="Irrigated vs Rainfed",
    ),
]


class ImportLandingView(TemplateView):
    """Landing page that lists all available import wizards."""

    template_name = "pmksy/home.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["wizards"] = [
            {
                **wizard,
                "url": reverse("pmksy:import-run", kwargs={"wizard_slug": wizard["slug"]}),
            }
            for wizard in WIZARDS
        ]
        return context


class BasePMKSYImportWizard(ImportWizard):
    """Shared configuration for all PMKSY import workflows."""

    sources = (FileSource,)
    importer_classes = (
        importers.CSVImporter,
        importers.ExcelImporter,
        importers.JSONImporter,
    )


class PMKSYImportWizard(BasePMKSYImportWizard):
    """Single entry point that delegates to the requested serializer."""

    wizard_slug: str
    success_url_name = "pmksy:home"

    @cached_property
    def _wizard_map(self) -> Dict[str, WizardConfig]:
        return {item["slug"]: item for item in WIZARDS}

    def get_serializer_class(self):  # type: ignore[override]
        slug = self.kwargs.get("wizard_slug")
        try:
            return self._wizard_map[slug]["serializer"]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise Http404("Unknown import wizard") from exc

    def get_wizard_name(self) -> str:  # pragma: no cover - thin wrapper
        wizard_slug = self.kwargs.get("wizard_slug")
        wizard = self._wizard_map.get(wizard_slug)
        if wizard is None:
            raise Http404("Unknown import wizard")
        return wizard["title"]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        wizard_slug = self.kwargs.get("wizard_slug")
        wizard = self._wizard_map.get(wizard_slug)
        if wizard is None:
            raise Http404("Unknown import wizard")
        context.update(
            {
                "wizard": wizard,
                "wizard_slug": wizard_slug,
            }
        )
        return context


wizard_view = SurveyWizardView.as_view()


class BulkImportWizardView(View):
    """Two-step workflow to import CSV data in bulk."""

    template_upload = "pmksy/import_wizard_upload.html"
    template_preview = "pmksy/import_wizard_preview.html"
    session_key = "pmksy_bulk_import"

    def get(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        if step == "preview":
            return self.render_preview(request)
        return self.render_upload(request)

    def post(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        if step == "preview":
            if "cancel" in request.POST:
                self.clear_storage(request)
                messages.info(request, "Bulk import cancelled.")
                return redirect("pmksy:import")
            if "confirm" in request.POST:
                return self.perform_import(request)
            return self.render_preview(request)
        return self.handle_upload(request)

    # ------------------------------------------------------------------
    def render_upload(self, request: HttpRequest, form: django_forms.Form | None = None) -> HttpResponse:
        form = form or forms.ImportUploadForm(choices=importers.target_choices())
        context = {
            "form": form,
            "targets": importers.TARGET_LIST,
        }
        return render(request, self.template_upload, context)

    def handle_upload(self, request: HttpRequest) -> HttpResponse:
        form = forms.ImportUploadForm(request.POST or None, request.FILES or None, choices=importers.target_choices())
        if not form.is_valid():
            return self.render_upload(request, form)

        target_key = form.cleaned_data["target"]
        try:
            target = importers.get_target(target_key)
        except KeyError:
            form.add_error("target", "Unknown dataset selected.")
            return self.render_upload(request, form)

        uploaded_file = form.cleaned_data["data_file"]
        try:
            parsed = importers.parse_uploaded_file(uploaded_file)
        except ValueError as exc:
            form.add_error("data_file", str(exc))
            return self.render_upload(request, form)

        storage_payload = {
            "target": target.key,
            "columns": parsed.columns,
            "column_labels": parsed.original_headers,
            "rows": [{"line": row.line_number, "values": dict(row.values)} for row in parsed.rows],
        }
        self.set_storage(request, storage_payload)
        messages.info(request, "File parsed successfully. Review the preview before importing.")
        return redirect("pmksy:import-preview")

    def render_preview(self, request: HttpRequest) -> HttpResponse:
        storage = self.get_storage(request)
        if not storage:
            messages.info(request, "Upload a CSV file to begin a bulk import.")
            return redirect("pmksy:import")

        target = importers.get_target(storage["target"])
        context = self.build_preview_context(target, storage)
        return render(request, self.template_preview, context)

    def perform_import(self, request: HttpRequest) -> HttpResponse:
        storage = self.get_storage(request)
        if not storage:
            messages.info(request, "Upload a CSV file to begin a bulk import.")
            return redirect("pmksy:import")

        target = importers.get_target(storage["target"])
        context = self.build_preview_context(target, storage)
        if not context["can_import"]:
            messages.error(request, "Required columns are missing. Update the file and try again.")
            return render(request, self.template_preview, context)

        parsed_rows = [
            importers.ParsedRow(line_number=row["line"], values=row["values"])
            for row in storage["rows"]
        ]
        summary = importers.perform_import(target, parsed_rows)

        if summary.created and not summary.error_count:
            messages.success(request, f"Imported {summary.created} rows into {target.label}.")
        elif summary.created:
            messages.warning(
                request,
                f"Imported {summary.created} rows into {target.label} with {summary.error_count} errors.",
            )
        else:
            messages.error(request, "No rows were imported. See the error details below.")

        error_rows = [
            {
                "row_number": error.row_number,
                "message": error.message,
                "values": [
                    (
                        context["column_labels"].get(key, key),
                        "—" if value in (None, "") else str(value),
                    )
                    for key, value in error.values.items()
                ],
            }
            for error in summary.errors
        ]

        context.update(
            {
                "import_complete": True,
                "summary": summary,
                "error_rows": error_rows,
            }
        )
        self.clear_storage(request)
        return render(request, self.template_preview, context)

    # ------------------------------------------------------------------
    def build_preview_context(self, target: importers.ImportTarget, storage: Dict[str, object]) -> Dict[str, Any]:
        columns: List[str] = list(storage.get("columns", []))
        column_labels: Dict[str, str] = dict(storage.get("column_labels", {}))
        rows: List[Dict[str, Any]] = list(storage.get("rows", []))

        available_columns = set(columns)
        target_columns = set(target.field_map.keys())
        missing = sorted(target.required - available_columns)
        recognized = [col for col in columns if col in target_columns]
        unused = [col for col in columns if col not in target_columns]

        preview_rows = rows[:10]
        preview_headers = [
            {
                "key": col,
                "label": column_labels.get(col, col),
            }
            for col in columns
        ]
        preview_table = [
            [row["values"].get(col, "") for col in columns]
            for row in preview_rows
        ]

        context: Dict[str, Any] = {
            "target": target,
            "row_count": len(rows),
            "column_order": columns,
            "column_labels": column_labels,
            "preview_headers": preview_headers,
            "preview_table": preview_table,
            "recognized_columns": [
                {
                    "source": column_labels.get(col, col),
                    "normalised": col,
                    "model_field": target.field_map[col],
                    "model_label": target.humanised_column(col),
                }
                for col in recognized
            ],
            "unused_columns": [column_labels.get(col, col) for col in unused],
            "missing_columns": [target.humanised_column(col) for col in missing],
            "required_columns": [target.humanised_column(col) for col in target.required],
            "expected_columns": [
                {
                    "column": col,
                    "label": target.humanised_column(col),
                }
                for col in target.expected_columns
            ],
            "can_import": len(rows) > 0 and not missing,
            "error_rows": [],
        }
        return context

    def get_storage(self, request: HttpRequest) -> Dict[str, Any] | None:
        return request.session.get(self.session_key)

    def set_storage(self, request: HttpRequest, payload: Dict[str, Any]) -> None:
        request.session[self.session_key] = payload
        request.session.modified = True

    def clear_storage(self, request: HttpRequest) -> None:
        request.session.pop(self.session_key, None)


wizard_view = SurveyWizardView.as_view()


class BulkImportWizardView(View):
    """Two-step workflow to import CSV data in bulk."""

    template_upload = "pmksy/import_wizard_upload.html"
    template_preview = "pmksy/import_wizard_preview.html"
    session_key = "pmksy_bulk_import"

    def get(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        if step == "preview":
            return self.render_preview(request)
        return self.render_upload(request)

    def post(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        if step == "preview":
            if "cancel" in request.POST:
                self.clear_storage(request)
                messages.info(request, "Bulk import cancelled.")
                return redirect("pmksy:import")
            if "confirm" in request.POST:
                return self.perform_import(request)
            return self.render_preview(request)
        return self.handle_upload(request)

    # ------------------------------------------------------------------
    def render_upload(self, request: HttpRequest, form: django_forms.Form | None = None) -> HttpResponse:
        form = form or forms.ImportUploadForm(choices=importers.target_choices())
        context = {
            "form": form,
            "targets": importers.TARGET_LIST,
        }
        return render(request, self.template_upload, context)

    def handle_upload(self, request: HttpRequest) -> HttpResponse:
        form = forms.ImportUploadForm(request.POST or None, request.FILES or None, choices=importers.target_choices())
        if not form.is_valid():
            return self.render_upload(request, form)

        target_key = form.cleaned_data["target"]
        try:
            target = importers.get_target(target_key)
        except KeyError:
            form.add_error("target", "Unknown dataset selected.")
            return self.render_upload(request, form)

        uploaded_file = form.cleaned_data["data_file"]
        try:
            parsed = importers.parse_uploaded_file(uploaded_file)
        except ValueError as exc:
            form.add_error("data_file", str(exc))
            return self.render_upload(request, form)

        storage_payload = {
            "target": target.key,
            "columns": parsed.columns,
            "column_labels": parsed.original_headers,
            "rows": [{"line": row.line_number, "values": dict(row.values)} for row in parsed.rows],
        }
        self.set_storage(request, storage_payload)
        messages.info(request, "File parsed successfully. Review the preview before importing.")
        return redirect("pmksy:import-preview")

    def render_preview(self, request: HttpRequest) -> HttpResponse:
        storage = self.get_storage(request)
        if not storage:
            messages.info(request, "Upload a CSV file to begin a bulk import.")
            return redirect("pmksy:import")

        target = importers.get_target(storage["target"])
        context = self.build_preview_context(target, storage)
        return render(request, self.template_preview, context)

    def perform_import(self, request: HttpRequest) -> HttpResponse:
        storage = self.get_storage(request)
        if not storage:
            messages.info(request, "Upload a CSV file to begin a bulk import.")
            return redirect("pmksy:import")

        target = importers.get_target(storage["target"])
        context = self.build_preview_context(target, storage)
        if not context["can_import"]:
            messages.error(request, "Required columns are missing. Update the file and try again.")
            return render(request, self.template_preview, context)

        parsed_rows = [
            importers.ParsedRow(line_number=row["line"], values=row["values"])
            for row in storage["rows"]
        ]
        summary = importers.perform_import(target, parsed_rows)

        if summary.created and not summary.error_count:
            messages.success(request, f"Imported {summary.created} rows into {target.label}.")
        elif summary.created:
            messages.warning(
                request,
                f"Imported {summary.created} rows into {target.label} with {summary.error_count} errors.",
            )
        else:
            messages.error(request, "No rows were imported. See the error details below.")

        error_rows = [
            {
                "row_number": error.row_number,
                "message": error.message,
                "values": [
                    (
                        context["column_labels"].get(key, key),
                        "—" if value in (None, "") else str(value),
                    )
                    for key, value in error.values.items()
                ],
            }
            for error in summary.errors
        ]

        context.update(
            {
                "import_complete": True,
                "summary": summary,
                "error_rows": error_rows,
            }
        )
        self.clear_storage(request)
        return render(request, self.template_preview, context)

    # ------------------------------------------------------------------
    def build_preview_context(self, target: importers.Dataset, storage: Dict[str, object]) -> Dict[str, Any]:
        columns: List[str] = list(storage.get("columns", []))
        column_labels: Dict[str, str] = dict(storage.get("column_labels", {}))
        rows: List[Dict[str, Any]] = list(storage.get("rows", []))

        available_columns = set(columns)
        target_columns = set(target.field_map.keys())
        missing = sorted(target.required - available_columns)
        recognized = [col for col in columns if col in target_columns]
        unused = [col for col in columns if col not in target_columns]

        preview_rows = rows[:10]
        preview_headers = [
            {
                "key": col,
                "label": column_labels.get(col, col),
            }
            for col in columns
        ]
        preview_table = [
            [row["values"].get(col, "") for col in columns]
            for row in preview_rows
        ]

        context: Dict[str, Any] = {
            "target": target,
            "row_count": len(rows),
            "column_order": columns,
            "column_labels": column_labels,
            "preview_headers": preview_headers,
            "preview_table": preview_table,
            "recognized_columns": [
                {
                    "source": column_labels.get(col, col),
                    "normalised": col,
                    "model_field": target.field_map[col],
                    "model_label": target.humanised_column(col),
                }
                for col in recognized
            ],
            "unused_columns": [column_labels.get(col, col) for col in unused],
            "missing_columns": [target.humanised_column(col) for col in missing],
            "required_columns": [target.humanised_column(col) for col in target.required],
            "expected_columns": [
                {
                    "column": col,
                    "label": target.humanised_column(col),
                }
                for col in target.expected_columns
            ],
            "can_import": len(rows) > 0 and not missing,
            "error_rows": [],
        }
        return context

    def get_storage(self, request: HttpRequest) -> Dict[str, Any] | None:
        return request.session.get(self.session_key)

    def set_storage(self, request: HttpRequest, payload: Dict[str, Any]) -> None:
        request.session[self.session_key] = payload
        request.session.modified = True

    def clear_storage(self, request: HttpRequest) -> None:
        request.session.pop(self.session_key, None)


bulk_import_wizard_view = BulkImportWizardView.as_view()

wizard_view = SurveyWizardView.as_view()


class BulkImportWizardView(View):
    """Two-step workflow to import CSV data in bulk."""

    template_upload = "pmksy/import_wizard_upload.html"
    template_preview = "pmksy/import_wizard_preview.html"
    session_key = "pmksy_bulk_import"

    def get(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        if step == "preview":
            return self.render_preview(request)
        return self.render_upload(request)

    def post(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        if step == "preview":
            if "cancel" in request.POST:
                self.clear_storage(request)
                messages.info(request, "Bulk import cancelled.")
                return redirect("pmksy:import")
            if "confirm" in request.POST:
                return self.perform_import(request)
            return self.render_preview(request)
        return self.handle_upload(request)

    # ------------------------------------------------------------------
    def render_upload(self, request: HttpRequest, form: django_forms.Form | None = None) -> HttpResponse:
        form = form or forms.ImportUploadForm(choices=importers.target_choices())
        context = {
            "form": form,
            "targets": importers.TARGET_LIST,
        }
        return render(request, self.template_upload, context)

    def handle_upload(self, request: HttpRequest) -> HttpResponse:
        form = forms.ImportUploadForm(request.POST or None, request.FILES or None, choices=importers.target_choices())
        if not form.is_valid():
            return self.render_upload(request, form)

        target_key = form.cleaned_data["target"]
        try:
            target = importers.get_target(target_key)
        except KeyError:
            form.add_error("target", "Unknown dataset selected.")
            return self.render_upload(request, form)

        uploaded_file = form.cleaned_data["data_file"]
        try:
            parsed = importers.parse_uploaded_file(uploaded_file)
        except ValueError as exc:
            form.add_error("data_file", str(exc))
            return self.render_upload(request, form)

        storage_payload = {
            "target": target.key,
            "columns": parsed.columns,
            "column_labels": parsed.original_headers,
            "rows": [{"line": row.line_number, "values": dict(row.values)} for row in parsed.rows],
        }
        self.set_storage(request, storage_payload)
        messages.info(request, "File parsed successfully. Review the preview before importing.")
        return redirect("pmksy:import-preview")

    def render_preview(self, request: HttpRequest) -> HttpResponse:
        storage = self.get_storage(request)
        if not storage:
            messages.info(request, "Upload a CSV file to begin a bulk import.")
            return redirect("pmksy:import")

        target = importers.get_target(storage["target"])
        context = self.build_preview_context(target, storage)
        return render(request, self.template_preview, context)

    def perform_import(self, request: HttpRequest) -> HttpResponse:
        storage = self.get_storage(request)
        if not storage:
            messages.info(request, "Upload a CSV file to begin a bulk import.")
            return redirect("pmksy:import")

        target = importers.get_target(storage["target"])
        context = self.build_preview_context(target, storage)
        if not context["can_import"]:
            messages.error(request, "Required columns are missing. Update the file and try again.")
            return render(request, self.template_preview, context)

        parsed_rows = [
            importers.ParsedRow(line_number=row["line"], values=row["values"])
            for row in storage["rows"]
        ]
        summary = importers.perform_import(target, parsed_rows)

        if summary.created and not summary.error_count:
            messages.success(request, f"Imported {summary.created} rows into {target.label}.")
        elif summary.created:
            messages.warning(
                request,
                f"Imported {summary.created} rows into {target.label} with {summary.error_count} errors.",
            )
        else:
            messages.error(request, "No rows were imported. See the error details below.")

        error_rows = [
            {
                "row_number": error.row_number,
                "message": error.message,
                "values": [
                    (
                        context["column_labels"].get(key, key),
                        "—" if value in (None, "") else str(value),
                    )
                    for key, value in error.values.items()
                ],
            }
            for error in summary.errors
        ]

        context.update(
            {
                "import_complete": True,
                "summary": summary,
                "error_rows": error_rows,
            }
        )
        self.clear_storage(request)
        return render(request, self.template_preview, context)

    # ------------------------------------------------------------------
    def build_preview_context(self, target: importers.Dataset, storage: Dict[str, object]) -> Dict[str, Any]:
        columns: List[str] = list(storage.get("columns", []))
        column_labels: Dict[str, str] = dict(storage.get("column_labels", {}))
        rows: List[Dict[str, Any]] = list(storage.get("rows", []))

        available_columns = set(columns)
        target_columns = set(target.field_map.keys())
        missing = sorted(target.required - available_columns)
        recognized = [col for col in columns if col in target_columns]
        unused = [col for col in columns if col not in target_columns]

        preview_rows = rows[:10]
        preview_headers = [
            {
                "key": col,
                "label": column_labels.get(col, col),
            }
            for col in columns
        ]
        preview_table = [
            [row["values"].get(col, "") for col in columns]
            for row in preview_rows
        ]

        context: Dict[str, Any] = {
            "target": target,
            "row_count": len(rows),
            "column_order": columns,
            "column_labels": column_labels,
            "preview_headers": preview_headers,
            "preview_table": preview_table,
            "recognized_columns": [
                {
                    "source": column_labels.get(col, col),
                    "normalised": col,
                    "model_field": target.field_map[col],
                    "model_label": target.humanised_column(col),
                }
                for col in recognized
            ],
            "unused_columns": [column_labels.get(col, col) for col in unused],
            "missing_columns": [target.humanised_column(col) for col in missing],
            "required_columns": [target.humanised_column(col) for col in target.required],
            "expected_columns": [
                {
                    "column": col,
                    "label": target.humanised_column(col),
                }
                for col in target.expected_columns
            ],
            "can_import": len(rows) > 0 and not missing,
            "error_rows": [],
        }
        return context

    def get_storage(self, request: HttpRequest) -> Dict[str, Any] | None:
        return request.session.get(self.session_key)

    def set_storage(self, request: HttpRequest, payload: Dict[str, Any]) -> None:
        request.session[self.session_key] = payload
        request.session.modified = True

    def clear_storage(self, request: HttpRequest) -> None:
        request.session.pop(self.session_key, None)


bulk_import_wizard_view = BulkImportWizardView.as_view()

