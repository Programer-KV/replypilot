# backend/services/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler."""
    scheduler.start()
    print("Background scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()
    print("Background scheduler stopped")
