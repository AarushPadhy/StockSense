"""
Supply Chain AI Django App Initialization.
Exposes the Celery application instance so shared tasks automatically bind to it.
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
