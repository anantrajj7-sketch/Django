from django.contrib import admin
from . import models


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.model_name}.csv'
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response

    export_as_csv.short_description = 'Export Selected as CSV'


@admin.register(models.Farmer)
class FarmerAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('name', 'village', 'taluka_block', 'district', 'contact_no')
    search_fields = ('name', 'village', 'district', 'contact_no')
    list_filter = ('district',)
    actions = ['export_as_csv']


@admin.register(models.LandHolding)
class LandHoldingAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'category', 'total_area_ha', 'irrigated_area_ha')
    list_filter = ('category', 'farmer__district')
    search_fields = ('farmer__name', 'category')
    actions = ['export_as_csv']


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'item_name', 'quantity', 'current_value')
    search_fields = ('farmer__name', 'item_name')
    actions = ['export_as_csv']


@admin.register(models.CropHistory)
class CropHistoryAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'crop_name', 'season', 'area_ha', 'production_kg')
    list_filter = ('season', 'crop_name')
    search_fields = ('farmer__name', 'crop_name')
    actions = ['export_as_csv']


@admin.register(models.CostOfCultivation)
class CostOfCultivationAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'crop_name', 'particular', 'cost_rs')
    list_filter = ('crop_name',)
    search_fields = ('farmer__name', 'crop_name', 'particular')
    actions = ['export_as_csv']


@admin.register(models.Weed)
class WeedAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'season', 'weed_type', 'herbicide')
    list_filter = ('season', 'weed_type')
    search_fields = ('farmer__name', 'weed_type')
    actions = ['export_as_csv']


@admin.register(models.WaterManagement)
class WaterManagementAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'season', 'irrigation_source', 'irrigation_count')
    list_filter = ('season', 'irrigation_source')
    search_fields = ('farmer__name', 'irrigation_source')
    actions = ['export_as_csv']


@admin.register(models.PestDisease)
class PestDiseaseAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'season', 'pest_disease', 'chemical_used')
    list_filter = ('season', 'pest_disease')
    search_fields = ('farmer__name', 'pest_disease', 'chemical_used')
    actions = ['export_as_csv']


@admin.register(models.NutrientManagement)
class NutrientManagementAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'season', 'crop_name', 'nitrogen_kg')
    list_filter = ('season', 'crop_name')
    search_fields = ('farmer__name', 'crop_name')
    actions = ['export_as_csv']


@admin.register(models.IncomeFromCrops)
class IncomeFromCropsAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'season', 'crop_name', 'gross_income_rs')
    list_filter = ('season', 'crop_name')
    search_fields = ('farmer__name', 'crop_name')
    actions = ['export_as_csv']


@admin.register(models.Enterprise)
class EnterpriseAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'enterprise_type', 'number', 'market_price')
    list_filter = ('enterprise_type',)
    search_fields = ('farmer__name', 'enterprise_type')
    actions = ['export_as_csv']


@admin.register(models.AnnualFamilyIncome)
class AnnualFamilyIncomeAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'source', 'income_rs', 'employment_days')
    search_fields = ('farmer__name', 'source')
    actions = ['export_as_csv']


@admin.register(models.Migration)
class MigrationAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'age_gender', 'migration_type', 'remittance')
    list_filter = ('migration_type',)
    search_fields = ('farmer__name', 'migration_type')
    actions = ['export_as_csv']


@admin.register(models.AdaptationStrategy)
class AdaptationStrategyAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'strategy', 'aware', 'adopted')
    list_filter = ('aware', 'adopted')
    search_fields = ('farmer__name', 'strategy')
    actions = ['export_as_csv']


@admin.register(models.Financial)
class FinancialAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'loan', 'kcc', 'soil_testing')
    list_filter = ('loan', 'kcc', 'soil_testing')
    search_fields = ('farmer__name',)
    actions = ['export_as_csv']


@admin.register(models.ConsumptionPattern)
class ConsumptionPatternAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'crop', 'crop_product', 'purchased', 'pds')
    list_filter = ('purchased', 'pds')
    search_fields = ('farmer__name', 'crop')
    actions = ['export_as_csv']


@admin.register(models.MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'crop', 'season', 'price_rs_qntl')
    list_filter = ('season', 'crop')
    search_fields = ('farmer__name', 'crop')
    actions = ['export_as_csv']


@admin.register(models.IrrigatedRainfed)
class IrrigatedRainfedAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('farmer', 'crop', 'sowing_date', 'harvesting_date')
    list_filter = ('crop',)
    search_fields = ('farmer__name', 'crop')
    actions = ['export_as_csv']
