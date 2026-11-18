"""
Database extension setup migration for PostgreSQL:
- pgvector extension
- TimescaleDB extension and hypertable creation for SalesHistory
Note: Skipped gracefully when running on SQLite or standard dev DBs.
"""

from django.db import migrations


def enable_pg_extensions_and_hypertable(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        # 1. Enable pgvector for semantic RAG embeddings
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception:
            pass

        # 2. Enable TimescaleDB for time-series sales telemetry
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            cursor.execute(
                "SELECT create_hypertable('inventory_core_saleshistory', 'recorded_at', if_not_exists => TRUE);"
            )
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory_core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=enable_pg_extensions_and_hypertable,
            reverse_code=migrations.RunPython.noop
        ),
    ]
