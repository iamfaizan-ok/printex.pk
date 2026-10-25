import threading
import time
import logging

logger = logging.getLogger("PrintX.Scheduler")

_scheduler_started = False
_scheduler_lock = threading.Lock()


def _run_periodic_cleanup():
    logger.info("PrintX auto-cleanup background worker started. Running every 30 minutes.")
    while True:
        try:
            from .cleanup_service import cleanup_completed_pdfs
            res = cleanup_completed_pdfs(cutoff_minutes=30)
            if res.get('cleaned_count', 0) > 0:
                logger.info(f"[Periodic Cleanup] Purged {res['cleaned_count']} completed PDFs older than 30 minutes.")
        except Exception as err:
            logger.error(f"[Periodic Cleanup] Scheduled worker error: {err}", exc_info=True)

        # Sleep for 30 minutes (1800 seconds)
        time.sleep(1800)


def start_cleanup_scheduler():
    """
    Spawns background daemon thread for 30-minute periodic PDF cleanup.
    Ensures safe, single execution across reloads.
    """
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

        thread = threading.Thread(
            target=_run_periodic_cleanup,
            name="PrintXAutoCleanupScheduler",
            daemon=True
        )
        thread.start()
        logger.info("PrintX auto-cleanup background scheduler thread launched successfully.")
