"""
Background task services for story and audio generation.

DEPRECATED: This module is kept for backwards compatibility.
Use webapp.tasks with Celery for production background tasks.
"""

from typing import Dict, Any, Optional
from datetime import datetime

# In-memory task store (for development/testing only)
# Production uses Celery with Redis - see webapp/tasks.py
task_store: Dict[str, Dict[str, Any]] = {}


def update_task_status(
    task_id: str,
    status: str,
    progress: float = None,
    message: str = None,
    result: dict = None
):
    """Update task status in in-memory store (dev only)."""
    task_store[task_id] = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message,
        "result": result,
        "updated_at": datetime.utcnow().isoformat()
    }


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status from in-memory store (dev only)."""
    return task_store.get(task_id)
