
"""Views providing a django-data-wizard powered import interface."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from django import forms as django_forms
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import TemplateView

from django.forms.models import model_to_dict

from . import forms, importers, models


class SurveyWizardView(View):
    """Simple session-backed multi-step wizard."""

    template_name = "pmksy/wizard_form.html"
    success_template = "pmksy/wizard_done.html"
    session_key = "pmksy_survey_wizard"

    FORMSET_RELATED_NAMES: Dict[str, str] = {
        "land_holdings": "land_holdings",
        "assets": "assets",
        "crop_history": "crop_history",
        "cost_cultivation": "cultivation_costs",
        "water_management": "water_management",
        "pest_disease": "pest_diseases",
        "nutrient_management": "nutrient_management",
        "income_crops": "crop_income",
        "irrigated_rainfed": "irrigated_rainfed",
        "enterprises": "enterprises",
        "annual_income": "annual_income",
        "consumption": "consumption_patterns",
        "market_price": "market_prices",
        "migration": "migration_records",
        "adaptation": "adaptation_strategies",
    }

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

    # ------------------------------------------------------------------
    def get(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        step_slug = self._get_step_slug(step)
        farmer = self._get_farmer(request)
        if step_slug != self.STEP_ORDER[0] and farmer is None:
            return redirect(self._step_url(self.STEP_ORDER[0]))

        config = self.STEP_CONFIG[step_slug]
        form = self._build_form(config, farmer)
        formsets = self._build_formsets(config, farmer)
        context = self._build_context(step_slug, config, form, formsets)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, step: str | None = None) -> HttpResponse:
        step_slug = self._get_step_slug(step)
        previous_step = self._previous_step(step_slug)
        if "_prev" in request.POST and previous_step:
            return redirect(self._step_url(previous_step))

        farmer = self._get_farmer(request)
        if step_slug != self.STEP_ORDER[0] and farmer is None:
            return redirect(self._step_url(self.STEP_ORDER[0]))

        config = self.STEP_CONFIG[step_slug]
        form = self._build_form(config, farmer, data=request.POST)
        formsets = self._build_formsets(config, farmer, data=request.POST)

        valid = True
        if form is not None and not form.is_valid():
            valid = False
        for _, (_, formset) in formsets.items():
            if not formset.is_valid():
                valid = False

        if not valid:
            context = self._build_context(step_slug, config, form, formsets)
            return render(request, self.template_name, context)

        farmer = self._persist_step(request, step_slug, form, formsets, farmer)
        if farmer is None:
            return redirect(self._step_url(self.STEP_ORDER[0]))

        next_step = self._next_step(step_slug)
        if next_step:
            return redirect(self._step_url(next_step))
        return self._render_success(request, farmer)

    # ------------------------------------------------------------------
    def _get_step_slug(self, step: str | None) -> str:
        if step is None:
            return self.STEP_ORDER[0]
        if step not in self.STEP_CONFIG:
            raise Http404("Unknown wizard step")
        return step

    def _build_context(
        self,
        step_slug: str,
        config: Dict[str, Any],
        form: django_forms.Form | None,
        formsets: "OrderedDict[str, Tuple[str, django_forms.BaseFormSet]]",
    ) -> Dict[str, Any]:
        step_index = self.STEP_ORDER.index(step_slug)
        context = {
            "step": step_slug,
            "step_config": config,
            "step_index": step_index + 1,
            "step_count": len(self.STEP_ORDER),
            "form": form,
            "formsets": [
                (key, title, formset) for key, (title, formset) in formsets.items()
            ],
            "previous_step": self._previous_step(step_slug),
            "next_step": self._next_step(step_slug),
        }
        return context

    def _build_form(
        self,
        config: Dict[str, Any],
        farmer: models.Farmer | None,
        *,
        data: Dict[str, Any] | None = None,
    ) -> django_forms.Form | None:
        form_class = config.get("form")
        if not form_class:
            return None

        kwargs: Dict[str, Any] = {}
        if data is not None:
            kwargs["data"] = data

        instance = self._get_form_instance(form_class, farmer)
        if instance is not None:
            kwargs["instance"] = instance

        return form_class(**kwargs)

    def _build_formsets(
        self,
        config: Dict[str, Any],
        farmer: models.Farmer | None,
        *,
        data: Dict[str, Any] | None = None,
    ) -> "OrderedDict[str, Tuple[str, django_forms.BaseFormSet]]":
        built: "OrderedDict[str, Tuple[str, django_forms.BaseFormSet]]" = OrderedDict()
        formset_configs = config.get("formsets", {})
        for key, (formset_class, title) in formset_configs.items():
            kwargs: Dict[str, Any] = {"prefix": key}
            if data is not None:
                kwargs["data"] = data
            else:
                kwargs["initial"] = self._initial_for_formset(key, formset_class, farmer)
            built[key] = (title, formset_class(**kwargs))
        return built

    def _get_form_instance(
        self, form_class: type[django_forms.Form], farmer: models.Farmer | None
    ) -> Any:
        if farmer is None:
            return None

        model = getattr(form_class._meta, "model", None)
        if model is None:
            return None
        if model is models.Farmer:
            return farmer
        if model is models.FinancialRecord:
            return farmer.financials.first()
        return None

    def _initial_for_formset(
        self,
        key: str,
        formset_class: type[django_forms.BaseFormSet],
        farmer: models.Farmer | None,
    ) -> List[Dict[str, Any]]:
        if farmer is None:
            return []

        related_name = self.FORMSET_RELATED_NAMES.get(key, key)
        manager = getattr(farmer, related_name, None)
        if manager is None:
            return []

        try:
            queryset = manager.all()
        except AttributeError:
            return []

        fields = list(getattr(formset_class.form, "base_fields", {}).keys())
        return [model_to_dict(obj, fields=fields) for obj in queryset]

    # ------------------------------------------------------------------
    def _persist_step(
        self,
        request: HttpRequest,
        step_slug: str,
        form: django_forms.Form | None,
        formsets: "OrderedDict[str, Tuple[str, django_forms.BaseFormSet]]",
        farmer: models.Farmer | None,
    ) -> models.Farmer | None:
        if form is not None:
            farmer = self._save_form(request, step_slug, form, farmer)

        if farmer is None:
            return None

        self._save_formsets(farmer, formsets)
        return farmer

    def _save_form(
        self,
        request: HttpRequest,
        step_slug: str,
        form: django_forms.Form,
        farmer: models.Farmer | None,
    ) -> models.Farmer | None:
        model = getattr(form, "_meta", None)
        form_model = getattr(model, "model", None)

        if form_model is models.Farmer:
            farmer_obj = form.save()
            self._store_farmer(request, farmer_obj)
            return farmer_obj

        if farmer is None:
            return None

        if form_model is models.FinancialRecord:
            instance = form.save(commit=False)
            instance.farmer = farmer
            instance.save()
            models.FinancialRecord.objects.filter(farmer=farmer).exclude(pk=instance.pk).delete()
            return farmer

        saved = form.save(commit=False)
        if hasattr(saved, "farmer") and saved.farmer_id is None:
            saved.farmer = farmer
        saved.save()
        return farmer

    def _save_formsets(
        self,
        farmer: models.Farmer,
        formsets: "OrderedDict[str, Tuple[str, django_forms.BaseFormSet]]",
    ) -> None:
        for key, (_, formset) in formsets.items():
            form_class = getattr(formset, "form", None)
            model = getattr(getattr(form_class, "_meta", None), "model", None)
            if model is None:
                continue

            related_name = self.FORMSET_RELATED_NAMES.get(key, key)
            manager = getattr(farmer, related_name, None)
            if manager is None:
                continue

            try:
                manager.all().delete()
            except AttributeError:
                continue

            for subform in formset:
                cleaned = getattr(subform, "cleaned_data", None)
                if not cleaned:
                    continue
                if formset.can_delete and cleaned.get("DELETE"):
                    continue
                if not subform.has_changed():
                    continue

                obj = model(farmer=farmer)
                for field, value in cleaned.items():
                    if field == "DELETE":
                        continue
                    setattr(obj, field, value)
                obj.save()

    # ------------------------------------------------------------------
    def _previous_step(self, step_slug: str) -> str | None:
        index = self.STEP_ORDER.index(step_slug)
        if index == 0:
            return None
        return self.STEP_ORDER[index - 1]

    def _next_step(self, step_slug: str) -> str | None:
        index = self.STEP_ORDER.index(step_slug)
        if index + 1 >= len(self.STEP_ORDER):
            return None
        return self.STEP_ORDER[index + 1]

    def _step_url(self, step_slug: str) -> str:
        if step_slug == self.STEP_ORDER[0]:
            return reverse("pmksy:wizard")
        return reverse("pmksy:wizard-step", args=(step_slug,))

    def _get_farmer(self, request: HttpRequest) -> models.Farmer | None:
        storage = request.session.get(self.session_key, {})
        farmer_id = storage.get("farmer_id")
        if not farmer_id:
            return None
        try:
            return models.Farmer.objects.get(pk=farmer_id)
        except models.Farmer.DoesNotExist:
            self._clear_storage(request)
            return None

    def _store_farmer(self, request: HttpRequest, farmer: models.Farmer) -> None:
        storage = request.session.get(self.session_key, {}).copy()
        storage["farmer_id"] = str(farmer.pk)
        request.session[self.session_key] = storage

    def _clear_storage(self, request: HttpRequest) -> None:
        if self.session_key in request.session:
            del request.session[self.session_key]

    # ------------------------------------------------------------------
    def _render_success(self, request: HttpRequest, farmer: models.Farmer) -> HttpResponse:
        self._clear_storage(request)
        summary = {
            "land_holdings": farmer.land_holdings.count(),
            "assets": farmer.assets.count(),
            "crop_history": farmer.crop_history.count(),
            "water_management": farmer.water_management.count(),
            "pest_disease": farmer.pest_diseases.count(),
            "cost_cultivation": farmer.cultivation_costs.count(),
            "nutrient_management": farmer.nutrient_management.count(),
            "income_crops": farmer.crop_income.count(),
            "irrigated_rainfed": farmer.irrigated_rainfed.count(),
            "enterprises": farmer.enterprises.count(),
            "annual_income": farmer.annual_income.count(),
            "consumption": farmer.consumption_patterns.count(),
            "market_price": farmer.market_prices.count(),
            "migration": farmer.migration_records.count(),
            "adaptation": farmer.adaptation_strategies.count(),
            "financial_record": farmer.financials.count(),
        }
        family_total = (
            farmer.family_males
            + farmer.family_females
            + farmer.family_children
            + farmer.family_adult
        )
        context = {
            "farmer": farmer,
            "family_total": family_total,
            "summary": summary,
        }
        return render(request, self.success_template, context)


from data_wizard.sources.models import FileSource

from . import data_wizard_shims as wizard_importers
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


class BasePMKSYImportWizard(View):
    """Shared configuration for all PMKSY import workflows."""

    sources = (FileSource,)
    importer_classes = (
        wizard_importers.CSVImporter,
        wizard_importers.ExcelImporter,
        wizard_importers.JSONImporter,
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

