"""Views powering the multi-step PMKSY data collection wizard."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from django import forms as django_forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

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

    def get(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        current_step = self.normalise_step(step)
        context = self.get_step_context(request, current_step)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        current_step = self.normalise_step(step)
        config = self.STEP_CONFIG[current_step]
        wizard_data = self.get_wizard_data(request)

        form = None
        if "form" in config:
            form_class = config["form"]
            form = form_class(request.POST, prefix=current_step)

        formsets = {}
        for key, (formset_class, _title) in config.get("formsets", {}).items():
            formsets[key] = formset_class(request.POST, prefix=f"{current_step}-{key}")

        is_valid = True
        if form is not None and not form.is_valid():
            is_valid = False
        for formset in formsets.values():
            if not formset.is_valid():
                is_valid = False

        if not is_valid:
            context = self.get_step_context(request, current_step, bound_form=form, bound_formsets=formsets)
            return render(request, self.template_name, context)

        step_payload: Dict[str, Any] = {}
        if form is not None:
            step_payload["form"] = form.cleaned_data
        if formsets:
            step_payload["formsets"] = {}
            for key, formset in formsets.items():
                cleaned_items: List[Dict[str, Any]] = []
                for item in formset.cleaned_data:
                    if not item or item.get("DELETE"):
                        continue
                    meaningful = any(
                        value not in (None, "", []) or isinstance(value, bool)
                        for name, value in item.items()
                        if name not in {"DELETE"}
                    )
                    if meaningful:
                        cleaned_items.append({k: v for k, v in item.items() if k not in {"DELETE"}})
                step_payload["formsets"][key] = cleaned_items

        wizard_data[current_step] = step_payload
        request.session.modified = True

        if "_prev" in request.POST:
            previous_step = self.get_previous_step(current_step)
            if previous_step is not None:
                return redirect(self.step_url(previous_step))

        next_step = self.get_next_step(current_step)
        if next_step is None:
            farmer, summary = self.save_all(wizard_data)
            request.session.pop("pmksy_wizard", None)
            context = {
                "farmer": farmer,
                "summary": summary,
                "family_total": self.compute_family_total(farmer),
            }
            messages.success(request, "Survey responses saved successfully.")
            return render(request, self.success_template, context)

        return redirect(self.step_url(next_step))

    # ------------------------------------------------------------------
    def normalise_step(self, step: str | None) -> str:
        if step in self.STEP_ORDER:
            return step
        return self.STEP_ORDER[0]

    def get_wizard_data(self, request: HttpRequest) -> Dict[str, Any]:
        return request.session.setdefault("pmksy_wizard", {})

    def get_previous_step(self, step: str) -> str | None:
        idx = self.STEP_ORDER.index(step)
        if idx == 0:
            return None
        return self.STEP_ORDER[idx - 1]

    def get_next_step(self, step: str) -> str | None:
        idx = self.STEP_ORDER.index(step)
        if idx == len(self.STEP_ORDER) - 1:
            return None
        return self.STEP_ORDER[idx + 1]

    def step_url(self, step: str) -> str:
        return reverse("pmksy:wizard-step", kwargs={"step": step})

    def get_step_context(
        self,
        request: HttpRequest,
        step: str,
        *,
        bound_form: django_forms.Form | None = None,
        bound_formsets: Dict[str, django_forms.BaseFormSet] | None = None,
    ) -> Dict[str, Any]:
        config = self.STEP_CONFIG[step]
        wizard_data = self.get_wizard_data(request)
        step_data = wizard_data.get(step, {})

        form = bound_form
        if form is None and "form" in config:
            form_class = config["form"]
            initial = step_data.get("form")
            form = form_class(initial=initial, prefix=step)

        formsets = bound_formsets or {}
        formset_blocks = []
        if config.get("formsets"):
            stored_formsets = step_data.get("formsets", {})
            if not formsets:
                formsets = {}
            for key, (formset_class, title) in config["formsets"].items():
                if key not in formsets:
                    initial = stored_formsets.get(key, [])
                    formsets[key] = formset_class(prefix=f"{step}-{key}", initial=initial)
                formset_blocks.append((key, title, formsets[key]))

        context = {
            "step": step,
            "step_config": config,
            "form": form,
            "formsets": formset_blocks,
            "step_index": self.STEP_ORDER.index(step) + 1,
            "step_count": len(self.STEP_ORDER),
            "previous_step": self.get_previous_step(step),
            "next_step": self.get_next_step(step),
        }
        return context

    @transaction.atomic
    def save_all(self, data: Dict[str, Any]) -> tuple[models.Farmer, Dict[str, int]]:
        farmer_data = data.get("farmer", {}).get("form", {})
        farmer = models.Farmer.objects.create(**farmer_data)

        summary: Dict[str, int] = {}
        for section in ("land", "production", "livelihoods", "resilience"):
            counts = self.create_related_records(farmer, data.get(section, {}).get("formsets", {}))
            summary.update(counts)

        financial_form = data.get("resilience", {}).get("form")
        if financial_form:
            models.FinancialRecord.objects.create(farmer=farmer, **financial_form)
            summary["financial_record"] = 1
        else:
            summary["financial_record"] = 0

        summary.setdefault("land_holdings", 0)
        summary.setdefault("assets", 0)
        summary.setdefault("crop_history", 0)
        summary.setdefault("water_management", 0)
        summary.setdefault("pest_disease", 0)
        summary.setdefault("cost_cultivation", 0)
        summary.setdefault("nutrient_management", 0)
        summary.setdefault("income_crops", 0)
        summary.setdefault("irrigated_rainfed", 0)
        summary.setdefault("enterprises", 0)
        summary.setdefault("annual_income", 0)
        summary.setdefault("consumption", 0)
        summary.setdefault("market_price", 0)
        summary.setdefault("migration", 0)
        summary.setdefault("adaptation", 0)

        return farmer, summary

    def compute_family_total(self, farmer: models.Farmer) -> int:
        members = [
            farmer.family_males,
            farmer.family_females,
            farmer.family_children,
            farmer.family_adult,
        ]
        return sum(value or 0 for value in members)

    def create_related_records(
        self, farmer: models.Farmer, formset_payload: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, int]:
        mapping = {
            "land_holdings": models.LandHolding,
            "assets": models.Asset,
            "crop_history": models.CropHistory,
            "water_management": models.WaterManagement,
            "pest_disease": models.PestDiseaseRecord,
            "cost_cultivation": models.CostOfCultivation,
            "nutrient_management": models.NutrientManagement,
            "income_crops": models.IncomeFromCrops,
            "irrigated_rainfed": models.IrrigatedRainfed,
            "enterprises": models.Enterprise,
            "annual_income": models.AnnualFamilyIncome,
            "consumption": models.ConsumptionPattern,
            "market_price": models.MarketPrice,
            "migration": models.MigrationRecord,
            "adaptation": models.AdaptationStrategy,
        }
        counts: Dict[str, int] = {}
        for key, items in formset_payload.items():
            model_class = mapping.get(key)
            if model_class is None:
                continue
            created = 0
            for item in items:
                model_class.objects.create(farmer=farmer, **item)
                created += 1
            counts[key] = created
        return counts


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
