from django.contrib import admin

from . import models


@admin.register(models.Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_filter = ("is_active",)
    list_display = (
        ("name",)
        + list_filter
        + ("debug_mode", "secret_key", "time_zone", "append_slash", "allowed_hosts")
    )
    search_fields = list_display
    fieldsets = (
        (None, {"fields": ("name", "is_active")}),
        (
            "Settings",
            {
                "fields": (
                    "debug_mode",
                    "secret_key",
                    "time_zone",
                    "append_slash",
                    "allowed_hosts",
                )
            },
        ),
    )
