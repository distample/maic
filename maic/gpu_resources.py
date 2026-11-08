"""Release volume-owned models without unloading shared YOLO/LaMa state."""
import gc
import sys


class TemporaryModels:
    """Own synchronous passes; exit only after their page walk has unwound."""

    def __init__(self, log_fn):
        self._models = []
        self._log = log_fn

    def add(self, model):
        self._models.append(model)
        return model

    def __enter__(self):
        return self

    def _log_safely(self, message):
        try:
            self._log(message)
        except Exception:
            pass  # Cleanup must not replace an original conversion exception.

    def __exit__(self, *_exc):
        if not self._models:
            return False
        torch = sys.modules.get("torch")
        cuda = getattr(torch, "cuda", None)
        initialized = cuda is not None and cuda.is_initialized()
        before = None
        if initialized:
            try:
                before = (cuda.memory_allocated(), cuda.memory_reserved())
            except Exception as exc:
                self._log_safely(f"GPU CLEANUP: measurement unavailable ({exc})")
        for model in self._models:
            try:
                model.close()  # The pass lock waits for concurrent apply calls.
            except Exception as exc:
                self._log_safely(f"GPU CLEANUP: model release failed ({exc})")
        self._models.clear()
        gc.collect()
        if initialized:
            try:
                # Live allocations of other threads/global models remain intact.
                cuda.empty_cache()
                after = (cuda.memory_allocated(), cuda.memory_reserved())
                self._log_safely(
                    f"GPU CLEANUP: allocated/reserved bytes before={before} after={after}"
                )
            except Exception as exc:
                self._log_safely(f"GPU CLEANUP: allocator release failed ({exc})")
        return False
