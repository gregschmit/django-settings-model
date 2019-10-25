from django.apps import AppConfig


class CustomConfig(AppConfig):
    name = "settings_model"
    verbose_name = "Settings"

    def ready(self, *args, **kwargs):
        # run settings initializer
        from .models import Settings

        Settings.init()
        Settings.check_secret_key()
