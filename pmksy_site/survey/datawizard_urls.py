from django.urls import include, path

app_name = 'datawizard'

urlpatterns = [
    path('', include('data_wizard.urls')),
]
