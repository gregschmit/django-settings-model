import importlib
import logging
import os
from pathlib import Path
from pytz import common_timezones
import sys

from django.conf import settings
from django.db import models, transaction
from django.db.utils import Error as DBError
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from .settings import get_setting


logger = logging.getLogger(__name__)


class SettingsModel(models.Model):
    """
    An abstract model that tracks settings and touches certain files on save to signal
    the web server to reload. The ``FILE_NAME`` is a required property.
    """

    name = models.CharField(default="Default", max_length=255, unique=True, blank=False)
    is_active = models.BooleanField(default=True)

    # class constants, overridable by subclasses
    READABLE_INDEX = 2
    WRITABLE_INDEX = 3
    CREATE_INITIAL = True

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    @property
    def __settings_filename__(self):
        """
        The property defines the filename for the settings file which will be written to
        the project folder.
        """
        raise NotImplementedError

    @property
    def __settings_map__(self):
        """
        This property maps fields to the settings file variables.

        Returns a list/tuple of tuples in the format:
            (field_name, setting_name, readable, writable)

        For example:
            [
                ("debug_mode", "DEBUG", True, True),
                ("from_email", "DEFAULT_FROM_EMAIL", True, True),
            ]

        This should be implemented by subclasses with a normal list or tuple.
        """
        raise NotImplementedError

    def _get_settings_file(self):
        """
        The settings file should be saved next to the settings that are active. We will
        use the ``DJANGO_SETTINGS_MODULE`` environment variable to locate the directory
        where that file is located.

        The user may be using multiple settings models, so each one should define a
        unique ``__settings_filename__`` and we will write to that file name.
        """
        settings_file = importlib.import_module(
            os.environ["DJANGO_SETTINGS_MODULE"]
        ).__file__
        return os.path.join(os.path.dirname(settings_file), self.__settings_filename__)

    def encode_setting(self, field):
        """
        Given a field, convert the field to a string representing the Python code that
        should be written to the settings file.
        """
        raise NotImplementedError

    @classmethod
    def init(cls):
        """
        See if we have settings. If so, read the actual settings values into it.
        """
        logger.info("running settings init")
        try:
            s = cls.objects.filter(is_active=True).first()
            if s:
                s.read_settings()
            elif cls.CREATE_INITIAL:
                s = cls()
                s.read_settings()
        except DBError:
            logger.warning("db not ready (error on {} model)".format(cls.__name__))
            return

    def read_settings(self):
        """
        Read settings from Django into this instance.
        """
        for s in [x for x in self.__settings_map__ if x[self.READABLE_INDEX]]:
            try:
                setattr(self, s[0], getattr(settings, s[1]))
            except AttributeError:  # setting not found
                pass
        return self.save(reboot=False)

    def write_settings(self):
        """
        Write the settings defined by this instance to the settings file.
        """
        text = '"""WARNING: Autogenerated by django-settings-model."""\n\n'
        for s in [x for x in self.__settings_map__ if x[self.WRITABLE_INDEX]]:
            content = self.encode_setting(getattr(self, s[0]))
            if content:
                text += "{} = {}\n".format(s[1], content)

        # write to settings file
        with open(self._get_settings_file(), "w") as f:
            logger.info("writing config to {}".format(f.name))
            f.write(text)

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Save this instance, check to ensure only one instance is active, and reboot, if
        necessary.
        """
        # extract custom kwargs
        reboot = kwargs.pop("reboot", True)

        # deactivate extra settings if needed
        actives = type(self).objects.filter(is_active=True).exclude(pk=self.pk)
        if self.is_active:
            actives.update(is_active=False)
        else:
            active = actives.first()
            actives.exclude(pk=active.pk).update(is_active=False)

        # if we are saving an active settings instance, reboot the web server
        if self.is_active:
            if reboot:
                transaction.on_commit(lambda: self.write_and_signal_reboot())
        return super().save(*args, **kwargs)

    @staticmethod
    def signal_reboot():
        """
        Find and touch the reboot files to signal the server to restart.
        """
        # get reboot files
        touch_files = get_setting("SETTINGS_MODEL_REBOOT_FILES")
        if not touch_files:
            touch_files = [
                os.path.join(get_setting("BASE_DIR"), "manage.py")
            ]  # dev server
            try:
                wsgi_module = get_setting("WSGI_APPLICATION").rsplit(".", 1)[0]
                try:
                    importlib.import_module(wsgi_module)
                except RuntimeError:
                    pass
                touch_files.append(sys.modules[wsgi_module].__file__)
            except (AttributeError, IndexError, KeyError, ImportError):
                pass

        # touch files to signal reboot
        logger.info("signalling webserver reboot")
        logger.debug("  touching:")
        for f in touch_files:
            p = Path(f)
            if p.exists():
                logger.debug("   - {}".format(f))
                p.touch()
            else:
                logger.debug("   - {} (skipped, doesn't exist)".format(f))

    def write_and_signal_reboot(self, commit=True):
        """
        Commit the configuration to disk and call `signal_reboot`.
        """
        if commit:
            logger.info("committing config to disk...")
            self.write_settings()

        # signal reboot
        self.signal_reboot()


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
