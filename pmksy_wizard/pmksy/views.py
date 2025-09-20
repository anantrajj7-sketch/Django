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

from . import forms, models


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
