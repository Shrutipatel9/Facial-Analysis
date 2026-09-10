"""Dedicated thread for CPU-bound MediaPipe/onnxruntime CV work.

photo_validation_service, face_identity_service, and facial_measurement_service
each hold a module-level `@lru_cache`d MediaPipe/onnxruntime model singleton
(FaceDetector, FaceLandmarker, ArcFace InferenceSession) and call it directly
from async request handlers. Run today, that blocks the whole asyncio event
loop -- including unrelated requests like GET /health -- for the duration of
every detect()/run() call.

A single-worker executor moves that work off the event loop without changing
behavior: MediaPipe's Task API is not documented as safe for concurrent
detect() calls on the same instance from multiple threads, so max_workers is
pinned at 1 to keep every call into these singletons serialized exactly as it
already is today (one call in flight at a time) -- only now on a worker
thread instead of the event loop thread, so other requests keep being served
while it runs.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cv-worker")


async def run_cv_task[T](func: Callable[..., T], *args: object) -> T:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, func, *args)
