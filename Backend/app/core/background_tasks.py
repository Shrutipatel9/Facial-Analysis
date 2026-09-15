"""Fire-and-forget background coroutine scheduling, shared by any service
that needs an in-process asyncio background task (no task-queue exists
anywhere in this stack -- see analysis_service.py's own docstring for why
one call site doesn't justify adding one).

Extracted out of analysis_service.py (Milestone 2) once a second caller
(report_visual_service.py, for FR-022's AI image generation) needed the
exact same held-reference pattern -- see the module-level set below for
why a bare `asyncio.create_task()` is not safe on its own.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any

# asyncio only keeps a *weak* reference to a task once create_task()'s
# return value is discarded -- an unreferenced task can be garbage-collected
# mid-execution with no error, no log, nothing (see the Python docs' own
# "Important" note on asyncio.create_task). Every scheduled task is added
# here and removed via its own done-callback, so it stays referenced for
# its whole lifetime regardless of GC pressure.
_background_tasks: set[asyncio.Task[None]] = set()


def schedule_background_task(coro: Coroutine[Any, Any, None]) -> None:
    """Schedules a fire-and-forget background coroutine with a held
    reference (see _background_tasks above) -- the one correct way to use
    asyncio.create_task() for a task nothing else awaits."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
