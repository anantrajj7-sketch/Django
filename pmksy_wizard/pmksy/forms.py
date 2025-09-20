"""Forms powering the PMKSY data collection wizard."""
from __future__ import annotations

from django import forms

from . import models


class FarmerForm(forms.ModelForm):
    """Collects the base farmer profile information."""

    class Meta:
        model = models.Farmer
        exclude = ["farmer_id"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = field_name == "name"


class LandHoldingForm(forms.ModelForm):
    """Land parcel data excluding the foreign key."""

    class Meta:
        model = models.LandHolding
        exclude = ["land_id", "farmer"]
        widgets = {
            "soil_details": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class AssetForm(forms.ModelForm):
    """Asset inventory details."""

    class Meta:
        model = models.Asset
        exclude = ["asset_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class CropHistoryForm(forms.ModelForm):
    """Historical cropping pattern."""

    class Meta:
        model = models.CropHistory
        exclude = ["crop_hist_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class CostOfCultivationForm(forms.ModelForm):
    """Cost inputs for a specific crop."""

    class Meta:
        model = models.CostOfCultivation
        exclude = ["cost_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class WaterManagementForm(forms.ModelForm):
    """Water management practices."""

    class Meta:
        model = models.WaterManagement
        exclude = ["wm_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class PestDiseaseForm(forms.ModelForm):
    """Pest and disease inputs."""

    class Meta:
        model = models.PestDiseaseRecord
        exclude = ["pest_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class NutrientManagementForm(forms.ModelForm):
    """Fertiliser application details."""

    class Meta:
        model = models.NutrientManagement
        exclude = ["nutrient_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class IncomeFromCropsForm(forms.ModelForm):
    """Income estimation for crops."""

    class Meta:
        model = models.IncomeFromCrops
        exclude = ["income_crop_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class EnterpriseForm(forms.ModelForm):
    """Allied enterprise income."""

    class Meta:
        model = models.Enterprise
        exclude = ["enterprise_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class AnnualIncomeForm(forms.ModelForm):
    """Household income sources."""

    class Meta:
        model = models.AnnualFamilyIncome
        exclude = ["afi_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class MigrationForm(forms.ModelForm):
    """Migration details."""

    class Meta:
        model = models.MigrationRecord
        exclude = ["migration_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class AdaptationStrategyForm(forms.ModelForm):
    """Adaptation strategies known/adopted."""

    class Meta:
        model = models.AdaptationStrategy
        exclude = ["strategy_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class FinancialRecordForm(forms.ModelForm):
    """Single record summarising financial inclusion."""

    class Meta:
        model = models.FinancialRecord
        exclude = ["fin_id", "farmer"]
        widgets = {
            "memberships": forms.Textarea(attrs={"rows": 2}),
            "benefits": forms.Textarea(attrs={"rows": 2}),
            "training": forms.Textarea(attrs={"rows": 2}),
            "info_sources": forms.Textarea(attrs={"rows": 2}),
            "constraints": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class ConsumptionPatternForm(forms.ModelForm):
    """Monthly consumption pattern."""

    class Meta:
        model = models.ConsumptionPattern
        exclude = ["cp_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class MarketPriceForm(forms.ModelForm):
    """Market price data."""

    class Meta:
        model = models.MarketPrice
        exclude = ["price_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class IrrigatedRainfedForm(forms.ModelForm):
    """Irrigated vs rainfed crop area split."""

    class Meta:
        model = models.IrrigatedRainfed
        exclude = ["ir_id", "farmer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class ImportUploadForm(forms.Form):
    """Initial step of the bulk import wizard."""

    target = forms.ChoiceField(label="Dataset", help_text="Select the table you want to import data into.")
    data_file = forms.FileField(
        label="Data file",
        help_text="Upload a UTF-8 CSV file. Column headers should match the PMKSY schema names.",
    )

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop("choices", ())
        super().__init__(*args, **kwargs)
        self.fields["target"].choices = list(choices)

    def clean_data_file(self):
        uploaded = self.cleaned_data.get("data_file")
        if uploaded and uploaded.size == 0:
            raise forms.ValidationError("The selected file is empty.")
        return uploaded


LandHoldingFormSet = forms.formset_factory(LandHoldingForm, extra=1, can_delete=True)
AssetFormSet = forms.formset_factory(AssetForm, extra=1, can_delete=True)
CropHistoryFormSet = forms.formset_factory(CropHistoryForm, extra=1, can_delete=True)
CostOfCultivationFormSet = forms.formset_factory(CostOfCultivationForm, extra=1, can_delete=True)
WaterManagementFormSet = forms.formset_factory(WaterManagementForm, extra=1, can_delete=True)
PestDiseaseFormSet = forms.formset_factory(PestDiseaseForm, extra=1, can_delete=True)
NutrientManagementFormSet = forms.formset_factory(NutrientManagementForm, extra=1, can_delete=True)
IncomeFromCropsFormSet = forms.formset_factory(IncomeFromCropsForm, extra=1, can_delete=True)
EnterpriseFormSet = forms.formset_factory(EnterpriseForm, extra=1, can_delete=True)
AnnualIncomeFormSet = forms.formset_factory(AnnualIncomeForm, extra=1, can_delete=True)
MigrationFormSet = forms.formset_factory(MigrationForm, extra=1, can_delete=True)
AdaptationStrategyFormSet = forms.formset_factory(AdaptationStrategyForm, extra=1, can_delete=True)
ConsumptionPatternFormSet = forms.formset_factory(ConsumptionPatternForm, extra=1, can_delete=True)
MarketPriceFormSet = forms.formset_factory(MarketPriceForm, extra=1, can_delete=True)
IrrigatedRainfedFormSet = forms.formset_factory(IrrigatedRainfedForm, extra=1, can_delete=True)
