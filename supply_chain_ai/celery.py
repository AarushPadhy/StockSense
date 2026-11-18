import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module for 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'supply_chain_ai.settings')

app = Celery('supply_chain_ai')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Scheduled Periodic Tasks
app.conf.beat_schedule = {
    'monitor-supplier-disruptions-hourly': {
        'task': 'inventory_core.tasks.task_monitor_supplier_disruptions',
        'schedule': crontab(minute=0, hour='*'),  # Every hour
        'args': (),
    },
    'recalculate-stock-cover-daily': {
        'task': 'inventory_core.tasks.task_recalculate_all_stock_cover',
        'schedule': crontab(minute=30, hour=1),   # Daily at 01:30 UTC
        'args': (),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
