from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from survey.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', DashboardView.as_view(), name='dashboard'),
    path('datawizard/', include('survey.datawizard_urls', namespace='datawizard')),
]
