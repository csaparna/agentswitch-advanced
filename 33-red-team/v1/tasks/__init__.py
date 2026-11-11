"""Seat 33 v1 tasks 3–5 (Padmanabh)."""

from .rt_email_privacy import run as rt_email_privacy
from .rt_skill_write_blocked import run as rt_skill_write_blocked
from .rt_task_write_foreign import run as rt_task_write_foreign

TASKS = (
    ("rt_email_privacy", rt_email_privacy),
    ("rt_skill_write_blocked", rt_skill_write_blocked),
    ("rt_task_write_foreign", rt_task_write_foreign),
)

__all__ = [
    "TASKS",
    "rt_email_privacy",
    "rt_skill_write_blocked",
    "rt_task_write_foreign",
]
