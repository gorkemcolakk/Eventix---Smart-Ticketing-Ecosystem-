"""
Background jobs for Eventix.
Runs in a separate daemon thread.
"""
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger('eventix.jobs')


def birthday_job(send_birthday_emails_func):
    """
    Runs in background, checks every 30 seconds.
    Sends birthday emails at exactly 00:00 UTC.
    """
    logger.info("Birthday background service started (waiting for 00:00)")
    while True:
        now = datetime.now(timezone.utc)
        if now.hour == 0 and now.minute == 0:
            try:
                send_birthday_emails_func()
            except Exception:
                logger.exception("Birthday email job failed")
            time.sleep(65)  # Prevent re-triggering in same minute
        else:
            time.sleep(30)
