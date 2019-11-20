import importlib
import logging
import os
from pathlib import Path
import sys

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.db.utils import Error as DBError

from .settings import get_setting


logger = logging.getLogger(__name__)


class SettingsQuerySet(models.query.QuerySet):
    """
    Prevent deletion of active settings.
    """

    def delete(self, *args, **kwargs):
        if self.filter(is_active=True) and not self.model.ALLOW_NO_SETTINGS:
            raise PermissionDenied("Cannot delete settings which are currently active.")
        return super().delete(*args, **kwargs)


class SettingsModel(models.Model):
    """
    An abstract model that tracks settings and touches certain files on save to signal
    the web server to reload. Classes which inherit from this one should ensure that
    they implement all methods which raise NotImplementedError.
    """

    name = models.CharField(default="Default", max_length=255, unique=True, blank=False)
    is_active = models.BooleanField(default=True)

    objects = SettingsQuerySet.as_manager()

    # class constants, overridable by subclasses
    READABLE_INDEX = 2
    WRITABLE_INDEX = 3
    ALLOW_NO_SETTINGS = False

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

    def encode_setting(self, field):
        """
        Given a field, convert the field to a string representing the Python code that
        should be written to the settings file.
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

    @classmethod
    def init(cls):
        """
        See if we have settings; then:
         - If so, read the actual settings values into it, to ensure that the model
           always reflects reality. (Note: if you notice that settings are always
           "reverted", this usually means there is a problem with your `encode_setting`
           method, or possibly your core `settings.py` is not importing the
           `__settings_filename__` properly.) If other active settings exist, then
           `save` will be called t ensure the file is written and other settings are
           deactivated.
         - If not, and `ALLOW_NO_SETTINGS` is `False`, then either activate the first
           settings we find, or, if there are no settings objects, create one.
        """
        logger.info("running settings init")
        try:
            s = cls.objects.filter(is_active=True).first()
            if s:
                s.read_settings()
                if cls.objects.filter(is_active=True).exclude(pk=s.pk):
                    # need to invalidate other settings and ensure the settings file
                    # maps to this instance, so call the save() method.
                    s.save()
            elif not cls.ALLOW_NO_SETTINGS:
                s = cls.objects.all()
                if s:
                    s = s.first()
                    s.is_active = True
                    s.save()
                else:
                    s = cls()
                    s.read_settings()
                    s.save()
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

    def delete_settings(self):
        """
        Delete the settings file.
        """
        os.remove(self._get_settings_file())

    def clean(self):
        """
        Raise validation error if our `is_active` is False but there are no other
        active settings.
        """
        if self.pk:
            q = models.Q(pk=self.pk)
        else:
            q = models.Q()
        other_actives = type(self).objects.filter(is_active=True).exclude(q)
        if not (self.is_active or other_actives or self.ALLOW_NO_SETTINGS):
            raise ValidationError("No other active settings, so these must be active.")

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Save this instance, check to ensure only one instance is active, and reboot, if
        necessary.
        """
        # extract custom kwargs
        reboot = kwargs.pop("reboot", True)

        # deactivate extra settings if needed; ensure settings rules are followed
        actives = type(self).objects.filter(is_active=True).exclude(pk=self.pk)
        if self.is_active:  # if we are active, disable all others
            actives.update(is_active=False)
        else:  # if we are not active, then ensure one is active if we need one
            active = actives.first()
            if active:  # disable extraneous settings
                actives.exclude(pk=active.pk).update(is_active=False)
            else:  # set self to active if a settings is required, otherwise delete
                if self.ALLOW_NO_SETTINGS:
                    self.delete_settings()
                    transaction.on_commit(lambda: self.signal_reboot())
                else:
                    self.is_active = True

        if self.is_active and reboot:
            transaction.on_commit(lambda: self.write_and_signal_reboot())

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_active and not self.ALLOW_NO_SETTINGS:
            raise PermissionDenied("Cannot delete settings which are currently active.")
        return super().delete(*args, **kwargs)

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
