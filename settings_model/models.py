import logging
from pytz import common_timezones

from django.db import models
from django.db.utils import Error as DBError
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from .base import SettingsModel


logger = logging.getLogger(__name__)


class Settings(SettingsModel):
    """
    A basic implementation of a settings model.
    """

    debug_mode = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=255, blank=True)
    tz_choices = [(x, x) for x in common_timezones]
    time_zone = models.CharField(max_length=255, blank=True, choices=tz_choices)
    append_slash = models.BooleanField(default=False)
    allowed_hosts = models.CharField(
        max_length=255,
        blank=True,
        help_text=_(
            "A comma-delimited list of hosts for which this application is allowed to "
            "respond to."
        ),
    )

    __settings_filename__ = "model_settings.py"

    __settings_map__ = [
        ("debug_mode", "DEBUG", True, True),
        ("secret_key", "SECRET_KEY", True, True),
        ("time_zone", "TIME_ZONE", True, True),
        ("append_slash", "APPEND_SLASH", True, True),
        ("allowed_hosts", "ALLOWED_HOSTS", True, True),
    ]

    class Meta:
        verbose_name = verbose_name_plural = "Settings"

    @classmethod
    def check_secret_key(cls):
        """
        Attempt to get the active settings, and if the secret key is set to the default
        one, then create a new randomized secret key.
        """
        logger.info("attempting to check the secret key...")
        try:
            s = cls.objects.filter(is_active=True).first()
            if s and s.secret_key == "not-a-very-good-secret":
                chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
                s.secret_key = get_random_string(50, chars)
                s.save()
        except DBError:
            logger.warning("db not ready (error on {} model)".format(cls.__name__))
            return

    def encode_setting(self, field):
        if field is self.allowed_hosts:
            return str(field)
        return field.__repr__()
