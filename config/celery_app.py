import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("poupeai_finance_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "remove_expired_profiles_daily": {
        "task": "poupeai_finance_service.profiles.tasks.remove_expired_profiles",
        "schedule": crontab(hour=23, minute=59),
    },
    "check-overdue-invoices-daily": {
        "task": "poupeai_finance_service.credit_cards.tasks.check_and_notify_overdue_invoices",
        "schedule": crontab(hour=9, minute=0),
    },
    "check-due-soon-invoices-daily": {
        "task": "poupeai_finance_service.credit_cards.tasks.check_and_notify_due_soon_invoices",
        "schedule": crontab(hour=9, minute=5),
    },
}