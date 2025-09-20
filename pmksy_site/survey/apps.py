from django.apps import AppConfig


class SurveyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'survey'
    verbose_name = 'PMKSY Survey'

    def ready(self):
        # Import data wizard registration when app is ready
        from . import datawizard  # noqa: F401
