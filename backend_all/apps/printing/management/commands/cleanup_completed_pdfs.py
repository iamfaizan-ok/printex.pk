import time
from django.core.management.base import BaseCommand
from apps.printing.cleanup_service import cleanup_completed_pdfs


class Command(BaseCommand):
    help = "Automatically cleans up PDF files for completed print jobs older than 30 minutes, preserving order data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=30,
            help="Retention period in minutes from order creation (default: 30)"
        )
        parser.add_argument(
            '--loop',
            action='store_true',
            help="Run continuously in a loop every 30 minutes (scheduler mode)"
        )

    def handle(self, *args, **options):
        minutes = options.get('minutes', 30)
        is_loop = options.get('loop', False)

        if is_loop:
            self.stdout.write(self.style.SUCCESS(
                f"Starting PrintX Continuous Auto-Cleanup Scheduler (every {minutes} minutes)..."
            ))
            while True:
                try:
                    res = cleanup_completed_pdfs(cutoff_minutes=minutes)
                    self.stdout.write(
                        f"[{res['cutoff_time']}] Cleanup run completed. "
                        f"Purged PDFs: {res['cleaned_count']}, Incomplete preserved: {res['preserved_incomplete_count']}."
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error during cleanup loop: {e}"))
                time.sleep(minutes * 60)
        else:
            self.stdout.write(f"Executing completed PDF cleanup (cutoff: {minutes} minutes)...")
            res = cleanup_completed_pdfs(cutoff_minutes=minutes)
            self.stdout.write(self.style.SUCCESS(
                f"Completed! Purged {res['cleaned_count']} PDF(s). Incomplete orders preserved: {res['preserved_incomplete_count']}."
            ))
            if res.get('errors'):
                for err in res['errors']:
                    self.stdout.write(self.style.WARNING(f"  Warning: {err}"))
