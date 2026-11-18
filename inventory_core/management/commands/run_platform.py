"""
Unified Platform Runner Management Command.
Usage: python manage.py run_platform
Combines migrations, seeding check, Django server, Celery worker, and Celery beat into ONE command.
"""

import os
import sys
import subprocess
import signal
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from inventory_core.models import Product

class Command(BaseCommand):
    help = "Runs database migrations, seed data, Django server, and Celery workers in one single command."

    def add_arguments(self, parser):
        parser.add_argument('--port', type=str, default='8000', help='Port to run Django on')
        parser.add_argument('--no-celery', action='store_true', help='Skip Celery background processes')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🚀 STARTING SUPPLY CHAIN & INVENTORY AI PLATFORM"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # 1. Automatic Migrations
        self.stdout.write("📦 [1/3] Running database migrations...")
        call_command('migrate', interactive=False)

        # 2. Check if seeding is needed
        if Product.objects.count() == 0:
            self.stdout.write("🌱 [2/3] Catalog empty: Seeding synthetic suppliers, products, and sales...")
            call_command('seed_supply_chain_data')
        else:
            self.stdout.write("✅ [2/3] Database populated with catalog and telemetry.")

        # 3. Launch Services
        self.stdout.write("🌐 [3/3] Spawning Platform Services...")
        port = options.get('port', '8000')
        skip_celery = options.get('no_celery', False)

        processes = []

        # Handler for graceful shutdown
        def shutdown_processes(signum, frame):
            self.stdout.write("\n🛑 Shutting down Supply Chain AI Platform...")
            for proc in processes:
                try:
                    proc.terminate()
                except Exception:
                    pass
            for proc in processes:
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
            self.stdout.write(self.style.SUCCESS("👋 All platform services stopped."))
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_processes)
        signal.signal(signal.SIGTERM, shutdown_processes)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        python_exec = sys.executable

        # Celery Worker
        if not skip_celery:
            self.stdout.write("⚙️  Starting Celery Worker...")
            worker_proc = subprocess.Popen(
                [python_exec, "-m", "celery", "-A", "supply_chain_ai", "worker", "-l", "info", "--concurrency=2"],
                cwd=base_dir
            )
            processes.append(worker_proc)

            # Celery Beat
            self.stdout.write("⏰ Starting Celery Beat Scheduler...")
            beat_proc = subprocess.Popen(
                [python_exec, "-m", "celery", "-A", "supply_chain_ai", "beat", "-l", "info"],
                cwd=base_dir
            )
            processes.append(beat_proc)

        # Django Web Server (Foreground)
        self.stdout.write(self.style.SUCCESS(f"\n✨ Web Dashboard active: http://127.0.0.1:{port}/"))
        self.stdout.write(self.style.SUCCESS(f"📡 REST API Root:      http://127.0.0.1:{port}/api/v1/"))
        self.stdout.write(self.style.SUCCESS(f"📋 Admin Portal:       http://127.0.0.1:{port}/admin/\n"))
        self.stdout.write("Press Ctrl+C to stop all services.\n")

        django_proc = subprocess.Popen(
            [python_exec, "manage.py", "runserver", f"0.0.0.0:{port}"],
            cwd=base_dir
        )
        processes.append(django_proc)

        try:
            django_proc.wait()
        except KeyboardInterrupt:
            shutdown_processes(None, None)
