from rest_framework.permissions import IsAdminUser
from data_wizard.models import Run
from data_wizard.views import DataWizardViewSet


class StaffDataWizardViewSet(DataWizardViewSet):
    permission_classes = [IsAdminUser]
    queryset = Run.objects.all()
