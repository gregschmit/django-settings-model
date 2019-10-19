Settings Model
==============

.. inclusion-marker-do-not-remove

.. image:: https://travis-ci.org/gregschmit/django-settings-model.svg?branch=master
    :alt: TravisCI
    :target: https://travis-ci.org/gregschmit/django-settings-model

.. image:: https://img.shields.io/pypi/v/django-settings-model
    :alt: PyPI
    :target: https://pypi.org/project/django-settings-model/

.. image:: https://coveralls.io/repos/github/gregschmit/django-settings-model/badge.svg?branch=master
    :alt: Coveralls
    :target: https://coveralls.io/github/gregschmit/django-settings-model?branch=master

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code Style
    :target: https://github.com/ambv/black

Documentation: https://django-settings-model.readthedocs.io

Source: https://github.com/gregschmit/django-settings-model

PyPI: https://pypi.org/project/django-settings-model/

This Django reusable app implements a base ``SettingsModel`` class to allow settings to
be edited and saved in the database. For any particular project, you probably want to
customize which settings are exposed, so while there is a ``Settings`` example
implementation that you can use, the abstract model ``SettingsModel`` can be used to
construct your own settings model(s), and things like webserver restarts are handled in
the abstract model class.

**The Problem**: Sometimes you want to build an app that can run on an arbitrary piece
of equipment, and things like timezone, hostname, or SMTP settings may need to be
editable from the UI.

**The Solution**: This app implements a base ``SettingsModel`` class that allows you to
expose settings to the database.


How to Use
==========

.. code-block:: shell

    $ pip install django-settings-model

Include ``settings_model`` in your ``INSTALLED_APPS``.


Settings
--------

- ``SETTINGS_MODEL_REBOOT_FILES`` (default ``[]``): This is a list of files that should
  be touched when the settings model is saved to signal to the webserver to update. If
  it is falsy, then the system will try to find and touch the file
  ``BASE_DIR/manage.py`` and the ``wsgi.py`` file defined by ``WSGI_APPLICATION``.


Contributing
============

Submit a pull request if you would like to contribute. You must only contribute code
that you have authored or otherwise hold the copyright to, and you must make any
contributions to this project available under the MIT license.