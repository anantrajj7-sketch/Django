from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
from django.views.generic import TemplateView
from data_wizard.models import Run

from . import models


class DashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_counts = {
            'Farmers': models.Farmer.objects.count(),
            'Land Holdings': models.LandHolding.objects.count(),
            'Crop History': models.CropHistory.objects.count(),
            'Assets': models.Asset.objects.count(),
            'Cost of Cultivation': models.CostOfCultivation.objects.count(),
            'Water Management': models.WaterManagement.objects.count(),
            'Pest & Disease': models.PestDisease.objects.count(),
            'Nutrient Management': models.NutrientManagement.objects.count(),
            'Income from Crops': models.IncomeFromCrops.objects.count(),
            'Enterprises': models.Enterprise.objects.count(),
        }
        context['model_counts'] = model_counts
        context['recent_runs'] = Run.objects.order_by('-created')[:5]
        context['datawizard_url'] = '/datawizard/'
        context['admin_url'] = reverse('admin:index')
        return context
