"""
Unit tests
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from . import wsgi
from .models import Settings
from .settings import get_setting


class SettingsTestCase(TestCase):
    def test_bad_setting(self):
        self.assertIsNone(get_setting("INTENTIONALLY_BAD_VARIABLE"))


class SettingsModelTestCase(TestCase):
    """
    Test the example Settings implementation.
    """

    def setUp(self):
        Settings.init()
        self.settings = Settings.objects.filter(is_active=True).first()

    def test_constructor(self):
        self.assertTrue(self.settings)
        self.assertEqual(self.settings.name, "Default")

    def test_change_settings(self):
        old_debug = self.settings.debug_mode
        self.settings.debug_mode = not old_debug
        self.settings.save()
        self.assertEqual(self.settings.debug_mode, not old_debug)

    def test_write_and_reboot(self):
        self.settings.write_and_signal_reboot()


class SettingsModelAdminTestCase(TestCase):
    """
    Tests to ensure that the model admin returns an OK response.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="test_user",
            password="test_password",
            email="test_email@example.org",
        )
        self.client = Client()
        self.login = self.client.login(username="test_user", password="test_password")

    def test_changelist_view(self):
        self.assertTrue(self.login)
        response = self.client.get(reverse("admin:settings_model_settings_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_add_view(self):
        self.assertTrue(self.login)
        response = self.client.get(reverse("admin:settings_model_settings_add"))
        self.assertEqual(response.status_code, 200)


class WSGITestCase(TestCase):
    """
    Test WSGI module.
    """

    def test_wsgi_simple(self):
        self.assertTrue(wsgi.application)
