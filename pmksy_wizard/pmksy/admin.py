"""Django admin configuration for PMKSY models."""
from __future__ import annotations

from django.contrib import admin

from . import models


@admin.register(models.Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ("name", "village", "district", "contact_no")
    search_fields = ("name", "village", "district")


admin.site.register(models.LandHolding)
admin.site.register(models.Asset)
admin.site.register(models.CropHistory)
admin.site.register(models.CostOfCultivation)
admin.site.register(models.WeedRecord)
admin.site.register(models.WaterManagement)
admin.site.register(models.PestDiseaseRecord)
admin.site.register(models.NutrientManagement)
admin.site.register(models.IncomeFromCrops)
admin.site.register(models.Enterprise)
admin.site.register(models.AnnualFamilyIncome)
admin.site.register(models.MigrationRecord)
admin.site.register(models.AdaptationStrategy)
admin.site.register(models.FinancialRecord)
admin.site.register(models.ConsumptionPattern)
admin.site.register(models.MarketPrice)
admin.site.register(models.IrrigatedRainfed)
