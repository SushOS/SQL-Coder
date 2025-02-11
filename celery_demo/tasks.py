# tasks.py
import time
from celery import Celery

# Create the Celery app with Redis as broker and backend.
celery_app = Celery('benchmark',
                    broker='redis://localhost:6379/0',
                    backend='redis://localhost:6379/0')

@celery_app.task
def heavy_task():
    # Simulate heavy processing by sleeping for 2 seconds.
    time.sleep(2)
    return "Done"