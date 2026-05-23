"""
WSGI config for uniben_portal project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uniben_portal.settings')

# Automatically run migrations on startup in production (e.g., Render)
# This guarantees that the database schema is updated before serving requests
# if the build command doesn't handle it.
if os.environ.get('RENDER') == 'true' or os.environ.get('RENDER') is not None:
    try:
        from django.core.management import call_command
        import django
        django.setup()
        call_command('migrate', '--noinput')
        print("Successfully ran automatic migrations.")
    except Exception as e:
        print(f"Error running automatic migrations: {e}")

application = get_wsgi_application()
