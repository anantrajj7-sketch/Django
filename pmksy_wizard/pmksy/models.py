"""Database models describing the PMKSY socio-economic survey schema."""
from __future__ import annotations

import uuid

from django.db import models


class Farmer(models.Model):
    """Core demographic details for a farmer household."""

    farmer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    village = models.CharField(max_length=255, blank=True)
    taluka_block = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=255, blank=True)
    contact_no = models.CharField(max_length=50, blank=True)
    education = models.CharField(max_length=255, blank=True)
    caste_religion = models.CharField(max_length=255, blank=True)
    farming_experience_years = models.PositiveIntegerField(default=0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    altitude = models.FloatField(null=True, blank=True)
    family_males = models.PositiveIntegerField(default=0)
    family_females = models.PositiveIntegerField(default=0)
    family_children = models.PositiveIntegerField(default=0)
    family_adult = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LandHolding(models.Model):
    """Land details associated with a farmer."""

    land_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="land_holdings")
    category = models.CharField(max_length=255, blank=True)
    total_area_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    irrigated_area_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    irrigation_source = models.CharField(max_length=255, blank=True)
    irrigation_no = models.CharField(max_length=255, blank=True)
    irrigation_latitude = models.FloatField(null=True, blank=True)
    irrigation_longitude = models.FloatField(null=True, blank=True)
    soil_details = models.TextField(blank=True)

    class Meta:
        ordering = ["farmer__name", "category"]

    def __str__(self) -> str:
        return f"{self.farmer.name} - {self.category or 'Land Holding'}"


class Asset(models.Model):
    """Physical assets available with the household."""

    asset_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="assets")
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=0)
    years_owned = models.PositiveIntegerField(default=0)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "item_name"]

    def __str__(self) -> str:
        return f"{self.item_name} ({self.farmer.name})"


class CropHistory(models.Model):
    """Historical crop production details."""

    crop_hist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="crop_history")
    crop_name = models.CharField(max_length=255)
    variety = models.CharField(max_length=255, blank=True)
    season = models.CharField(max_length=100, blank=True)
    area_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    production_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sold_market_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    retained_seed_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    home_consumption_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "crop_name"]

    def __str__(self) -> str:
        return f"{self.crop_name} ({self.season})"


class CostOfCultivation(models.Model):
    """Cost inputs for a specific crop."""

    cost_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="cultivation_costs")
    crop_name = models.CharField(max_length=255)
    particular = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "crop_name", "particular"]

    def __str__(self) -> str:
        return f"{self.crop_name} - {self.particular}"


class WeedRecord(models.Model):
    """Weed management practices."""

    weed_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="weed_records")
    season = models.CharField(max_length=100, blank=True)
    weed_type = models.CharField(max_length=255, blank=True)
    weeding_time = models.CharField(max_length=255, blank=True)
    herbicide = models.CharField(max_length=255, blank=True)
    chemical_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    labour_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    labour_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "season"]

    def __str__(self) -> str:
        return f"{self.season} weed management"


class WaterManagement(models.Model):
    """Water management data for irrigation."""

    wm_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="water_management")
    season = models.CharField(max_length=100, blank=True)
    irrigation_source = models.CharField(max_length=255, blank=True)
    irrigation_count = models.PositiveIntegerField(default=0)
    depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    energy_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    labour_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "season"]

    def __str__(self) -> str:
        return f"{self.season} water management"


class PestDiseaseRecord(models.Model):
    """Pest and disease management data."""

    pest_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="pest_diseases")
    season = models.CharField(max_length=100, blank=True)
    pest_disease = models.CharField(max_length=255)
    chemical_used = models.CharField(max_length=255, blank=True)
    chemical_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    chemical_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    labour_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    labour_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "season", "pest_disease"]

    def __str__(self) -> str:
        return f"{self.pest_disease} ({self.season})"


class NutrientManagement(models.Model):
    """Nutrient management inputs for a crop."""

    nutrient_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="nutrient_management")
    season = models.CharField(max_length=100, blank=True)
    crop_name = models.CharField(max_length=255)
    fym_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    nitrogen_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    phosphate_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gromer_kg = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    other_fertilizer = models.TextField(blank=True)

    class Meta:
        ordering = ["farmer__name", "crop_name"]

    def __str__(self) -> str:
        return f"{self.crop_name} nutrient management"


class IncomeFromCrops(models.Model):
    """Income earned from individual crops."""

    income_crop_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="crop_income")
    season = models.CharField(max_length=100, blank=True)
    crop_name = models.CharField(max_length=255)
    production_qntl = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    yield_qntl_ha = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_rs_qntl = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gross_income_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    byproduct_income_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "crop_name"]

    def __str__(self) -> str:
        return f"{self.crop_name} income"


class Enterprise(models.Model):
    """Allied enterprises operated by the household."""

    enterprise_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="enterprises")
    enterprise_type = models.CharField(max_length=255)
    number = models.PositiveIntegerField(default=0)
    production = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    home_consumption = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sold_market = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    market_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "enterprise_type"]

    def __str__(self) -> str:
        return self.enterprise_type


class AnnualFamilyIncome(models.Model):
    """Annual income from different household sources."""

    afi_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="annual_income")
    source = models.CharField(max_length=255)
    income_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    employment_days = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["farmer__name", "source"]

    def __str__(self) -> str:
        return f"{self.source} income"


class MigrationRecord(models.Model):
    """Migration characteristics for household members."""

    migration_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="migration_records")
    age_gender = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    migration_type = models.CharField(max_length=255, blank=True)
    remittance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "age_gender"]

    def __str__(self) -> str:
        return f"Migration - {self.age_gender}"


class AdaptationStrategy(models.Model):
    """Climate adaptation strategies known or adopted."""

    strategy_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="adaptation_strategies")
    strategy = models.CharField(max_length=255)
    aware = models.BooleanField(default=False)
    adopted = models.BooleanField(default=False)

    class Meta:
        ordering = ["farmer__name", "strategy"]

    def __str__(self) -> str:
        return self.strategy


class FinancialRecord(models.Model):
    """Financial inclusion, credit and support data."""

    fin_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="financials")
    loan = models.BooleanField(default=False)
    loan_purpose = models.CharField(max_length=255, blank=True)
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
        ordering = ["farmer__name"]

    def __str__(self) -> str:
        return f"Financial record for {self.farmer.name}"


class ConsumptionPattern(models.Model):
    """Monthly consumption of agricultural produce."""

    cp_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="consumption_patterns")
    crop = models.CharField(max_length=255)
    crop_product = models.CharField(max_length=255, blank=True)
    consumption_kg_month = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchased = models.BooleanField(default=False)
    pds = models.BooleanField(default=False)

    class Meta:
        ordering = ["farmer__name", "crop"]

    def __str__(self) -> str:
        return f"{self.crop} consumption"


class MarketPrice(models.Model):
    """Market price realization for crops."""

    price_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="market_prices")
    crop = models.CharField(max_length=255)
    season = models.CharField(max_length=100, blank=True)
    area_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    production_tons = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_rs_qntl = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "crop"]

    def __str__(self) -> str:
        return f"{self.crop} market price"


class IrrigatedRainfed(models.Model):
    """Split of irrigated and rainfed areas for crops."""

    ir_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="irrigated_rainfed")
    crop = models.CharField(max_length=255)
    sowing_date = models.DateField(null=True, blank=True)
    harvesting_date = models.DateField(null=True, blank=True)
    rainfed_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    irrigated_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fertilizer_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["farmer__name", "crop"]

    def __str__(self) -> str:
        return f"{self.crop} irrigated/rainfed split"
