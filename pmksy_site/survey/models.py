import uuid
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Farmer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    village = models.CharField(max_length=255, blank=True)
    taluka_block = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=255, blank=True)
    contact_no = models.CharField(max_length=50, blank=True)
    education = models.CharField(max_length=255, blank=True)
    caste_religion = models.CharField(max_length=255, blank=True)
    farming_experience_years = models.PositiveIntegerField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    altitude = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    family_males = models.PositiveIntegerField(blank=True, null=True)
    family_females = models.PositiveIntegerField(blank=True, null=True)
    family_children = models.PositiveIntegerField(blank=True, null=True)
    family_adult = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name or str(self.id)


class LandHolding(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='land_holdings')
    category = models.CharField(max_length=255, blank=True)
    total_area_ha = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    irrigated_area_ha = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    irrigation_source = models.CharField(max_length=255, blank=True)
    irrigation_no = models.CharField(max_length=100, blank=True)
    irrigation_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    irrigation_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    soil_details = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Land Holding'
        verbose_name_plural = 'Land Holdings'

    def __str__(self):
        return f"{self.farmer} - {self.category or 'Land'}"


class Asset(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='assets')
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    years_owned = models.PositiveIntegerField(blank=True, null=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.item_name} ({self.farmer})"


class CropHistory(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='crop_history')
    crop_name = models.CharField(max_length=255)
    variety = models.CharField(max_length=255, blank=True)
    season = models.CharField(max_length=100, blank=True)
    area_ha = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    production_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    sold_market_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    retained_seed_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    home_consumption_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Crop History'

    def __str__(self):
        return f"{self.crop_name} - {self.farmer}"


class CostOfCultivation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='cultivation_costs')
    crop_name = models.CharField(max_length=255)
    particular = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    cost_rs = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Cost of Cultivation'
        verbose_name_plural = 'Cost of Cultivation'

    def __str__(self):
        return f"{self.crop_name} - {self.particular}"


class Weed(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='weeds')
    season = models.CharField(max_length=100, blank=True)
    weed_type = models.CharField(max_length=255, blank=True)
    weeding_time = models.CharField(max_length=255, blank=True)
    herbicide = models.CharField(max_length=255, blank=True)
    chemical_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    labour_days = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    labour_charge = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Weed Management'
        verbose_name_plural = 'Weed Management'

    def __str__(self):
        return f"{self.weed_type} - {self.farmer}"


class WaterManagement(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='water_management')
    season = models.CharField(max_length=100, blank=True)
    irrigation_source = models.CharField(max_length=255, blank=True)
    irrigation_count = models.PositiveIntegerField(blank=True, null=True)
    depth = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    energy_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    labour_charge = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Water Management'
        verbose_name_plural = 'Water Management'

    def __str__(self):
        return f"Water Mgmt {self.farmer}"


class PestDisease(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='pest_diseases')
    season = models.CharField(max_length=100, blank=True)
    pest_disease = models.CharField(max_length=255, blank=True)
    chemical_used = models.CharField(max_length=255, blank=True)
    chemical_qty = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    chemical_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    labour_days = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    labour_charge = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Pest & Disease'
        verbose_name_plural = 'Pest & Disease'

    def __str__(self):
        return f"{self.pest_disease} - {self.farmer}"


class NutrientManagement(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='nutrient_management')
    season = models.CharField(max_length=100, blank=True)
    crop_name = models.CharField(max_length=255, blank=True)
    fym_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    nitrogen_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    phosphate_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    gromer_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    other_fertilizer = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Nutrient Management'
        verbose_name_plural = 'Nutrient Management'

    def __str__(self):
        return f"{self.crop_name} - {self.farmer}"


class IncomeFromCrops(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='income_crops')
    season = models.CharField(max_length=100, blank=True)
    crop_name = models.CharField(max_length=255, blank=True)
    production_qntl = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    yield_qntl_ha = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    price_rs_qntl = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    gross_income_rs = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    byproduct_income_rs = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Income from Crops'
        verbose_name_plural = 'Income from Crops'

    def __str__(self):
        return f"Income {self.crop_name} - {self.farmer}"


class Enterprise(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='enterprises')
    enterprise_type = models.CharField(max_length=255)
    number = models.PositiveIntegerField(blank=True, null=True)
    production = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    home_consumption = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    sold_market = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    market_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Enterprise'
        verbose_name_plural = 'Enterprises'

    def __str__(self):
        return f"{self.enterprise_type} - {self.farmer}"


class AnnualFamilyIncome(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='annual_income')
    source = models.CharField(max_length=255)
    income_rs = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    employment_days = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        verbose_name = 'Annual Family Income'
        verbose_name_plural = 'Annual Family Income'

    def __str__(self):
        return f"{self.source} - {self.farmer}"


class Migration(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='migration_records')
    age_gender = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    migration_type = models.CharField(max_length=255, blank=True)
    remittance = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Migration'
        verbose_name_plural = 'Migration'

    def __str__(self):
        return f"Migration {self.farmer}"


class AdaptationStrategy(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='adaptation_strategies')
    strategy = models.CharField(max_length=255)
    aware = models.BooleanField(default=False)
    adopted = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Adaptation Strategy'
        verbose_name_plural = 'Adaptation Strategies'

    def __str__(self):
        return f"{self.strategy} - {self.farmer}"


class Financial(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='financial_records')
    loan = models.BooleanField(default=False)
    loan_purpose = models.TextField(blank=True)
    credit_returned = models.BooleanField(default=False)
    kcc = models.BooleanField(default=False)
    kcc_used = models.BooleanField(default=False)
    memberships = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    soil_testing = models.BooleanField(default=False)
    training = models.TextField(blank=True)
    info_sources = models.TextField(blank=True)
    constraints = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Financial Profile'
        verbose_name_plural = 'Financial Profiles'

    def __str__(self):
        return f"Financials - {self.farmer}"


class ConsumptionPattern(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='consumption_patterns')
    crop = models.CharField(max_length=255, blank=True)
    crop_product = models.CharField(max_length=255, blank=True)
    consumption_kg_month = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    purchased = models.BooleanField(default=False)
    pds = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Consumption Pattern'
        verbose_name_plural = 'Consumption Patterns'

    def __str__(self):
        return f"Consumption {self.crop} - {self.farmer}"


class MarketPrice(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='market_prices')
    crop = models.CharField(max_length=255, blank=True)
    season = models.CharField(max_length=100, blank=True)
    area_ha = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    production_tons = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    price_rs_qntl = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Market Price'
        verbose_name_plural = 'Market Prices'

    def __str__(self):
        return f"Price {self.crop} - {self.farmer}"


class IrrigatedRainfed(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='irrigated_rainfed')
    crop = models.CharField(max_length=255, blank=True)
    sowing_date = models.DateField(blank=True, null=True)
    harvesting_date = models.DateField(blank=True, null=True)
    rainfed_area = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    irrigated_area = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    fertilizer_rate = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Irrigated & Rainfed'
        verbose_name_plural = 'Irrigated & Rainfed'

    def __str__(self):
        return f"{self.crop} - {self.farmer}"
