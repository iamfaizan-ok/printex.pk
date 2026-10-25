import os
import sys
from django.apps import AppConfig


class PrintingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.printing'

    def ready(self):
        # Prevent running during management commands like migrate, makemigrations, etc.
        running_mgmt_cmds = ['migrate', 'makemigrations', 'collectstatic', 'check', 'cleanup_completed_pdfs']
        if any(cmd in sys.argv for cmd in running_mgmt_cmds):
            return

        # Start cleanup background scheduler thread
        # In runserver, start only in the main worker process (RUN_MAIN == 'true')
        # In production WSGI/ASGI, RUN_MAIN is not present, so start directly
        is_runserver = 'runserver' in sys.argv
        if not is_runserver or os.environ.get('RUN_MAIN') == 'true':
            try:
                from .scheduler import start_cleanup_scheduler
                start_cleanup_scheduler()
            except Exception as e:
                import logging
                logging.getLogger("PrintX.Apps").warning(f"Failed to start cleanup scheduler: {e}")

