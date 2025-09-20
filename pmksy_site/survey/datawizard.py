from data_wizard.sources import ModelSource

from . import models


class FarmerSource(ModelSource):
    model = models.Farmer
    slug = 'farmers'
    name = 'Farmers'


class LandHoldingSource(ModelSource):
    model = models.LandHolding
    slug = 'land_holdings'
    name = 'Land Holdings'


class AssetSource(ModelSource):
    model = models.Asset
    slug = 'assets'
    name = 'Assets'


class CropHistorySource(ModelSource):
    model = models.CropHistory
    slug = 'crop_history'
    name = 'Crop History'


class CostOfCultivationSource(ModelSource):
    model = models.CostOfCultivation
    slug = 'cost_of_cultivation'
    name = 'Cost of Cultivation'


class WeedSource(ModelSource):
    model = models.Weed
    slug = 'weeds'
    name = 'Weed Management'


class WaterManagementSource(ModelSource):
    model = models.WaterManagement
    slug = 'water_management'
    name = 'Water Management'


class PestDiseaseSource(ModelSource):
    model = models.PestDisease
    slug = 'pest_disease'
    name = 'Pest & Disease'


class NutrientManagementSource(ModelSource):
    model = models.NutrientManagement
    slug = 'nutrient_management'
    name = 'Nutrient Management'


class IncomeFromCropsSource(ModelSource):
    model = models.IncomeFromCrops
    slug = 'income_crops'
    name = 'Income from Crops'


class EnterpriseSource(ModelSource):
    model = models.Enterprise
    slug = 'enterprises'
    name = 'Enterprises'


class AnnualFamilyIncomeSource(ModelSource):
    model = models.AnnualFamilyIncome
    slug = 'annual_family_income'
    name = 'Annual Family Income'


class MigrationSource(ModelSource):
    model = models.Migration
    slug = 'migration'
    name = 'Migration'


class AdaptationStrategySource(ModelSource):
    model = models.AdaptationStrategy
    slug = 'adaptation_strategies'
    name = 'Adaptation Strategies'


class FinancialSource(ModelSource):
    model = models.Financial
    slug = 'financials'
    name = 'Financial Profiles'


class ConsumptionPatternSource(ModelSource):
    model = models.ConsumptionPattern
    slug = 'consumption_pattern'
    name = 'Consumption Patterns'


class MarketPriceSource(ModelSource):
    model = models.MarketPrice
    slug = 'market_price'
    name = 'Market Price'


class IrrigatedRainfedSource(ModelSource):
    model = models.IrrigatedRainfed
    slug = 'irrigated_rainfed'
    name = 'Irrigated & Rainfed'
