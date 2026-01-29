"""
Lite mode task queue - runs tasks synchronously without Redis/Celery.

In lite mode, tasks are executed immediately instead of being queued.
This simplifies local development but tasks run in the same process.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class LiteTaskResult:
    """Simple task result for lite mode."""
    
    def __init__(self, task_id: str, result: Any = None):
        self.id = task_id
        self._result = result
        self._ready = True
    
    def ready(self) -> bool:
        return self._ready
    
    def get(self, timeout: Optional[float] = None) -> Any:
        return self._result


class LiteTask:
    """Wrapper for a task function in lite mode."""
    
    _task_counter = 0
    
    def __init__(self, func: Callable, name: Optional[str] = None):
        self.func = func
        self.name = name or f"{func.__module__}.{func.__name__}"
        wraps(func)(self)
    
    def delay(self, *args, **kwargs) -> LiteTaskResult:
        """Execute task immediately (synchronous wrapper)."""
        task_id = f"lite-{LiteTask._task_counter}"
        LiteTask._task_counter += 1
        
        logger.info(f"[LiteQueue] Executing task {self.name} (id={task_id})")
        
        try:
            # Check if function is async
            if asyncio.iscoroutinefunction(self.func):
                # Run in event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create task for running loop
                    future = asyncio.ensure_future(self.func(*args, **kwargs))
                    result = None  # Can't wait in running loop
                else:
                    result = loop.run_until_complete(self.func(*args, **kwargs))
            else:
                result = self.func(*args, **kwargs)
            
            logger.info(f"[LiteQueue] Task {self.name} completed")
            return LiteTaskResult(task_id, result)
        except Exception as e:
            logger.error(f"[LiteQueue] Task {self.name} failed: {e}")
            return LiteTaskResult(task_id, {"error": str(e)})
    
    def apply_async(self, args=None, kwargs=None) -> LiteTaskResult:
        """Execute task (same as delay in lite mode)."""
        args = args or ()
        kwargs = kwargs or {}
        return self.delay(*args, **kwargs)
    
    def __call__(self, *args, **kwargs):
        """Direct call executes the function."""
        return self.func(*args, **kwargs)


class LiteCeleryApp:
    """Mock Celery app for lite mode."""
    
    def __init__(self, name: str = "findablex"):
        self.name = name
        self._tasks: Dict[str, LiteTask] = {}
    
    def task(self, bind: bool = False, name: Optional[str] = None):
        """Decorator to register a task."""
        def decorator(func: Callable) -> LiteTask:
            task_name = name or f"{func.__module__}.{func.__name__}"
            
            if bind:
                # For bound tasks, wrap to inject self
                @wraps(func)
                def bound_func(*args, **kwargs):
                    # Create a mock task instance
                    mock_self = type('MockTask', (), {
                        'retry': lambda *a, **kw: None,
                        'request': type('Request', (), {'id': 'lite-task'})(),
                    })()
                    return func(mock_self, *args, **kwargs)
                task = LiteTask(bound_func, task_name)
            else:
                task = LiteTask(func, task_name)
            
            self._tasks[task_name] = task
            return task
        
        return decorator
    
    def send_task(self, name: str, args=None, kwargs=None) -> LiteTaskResult:
        """Send a task by name."""
        task = self._tasks.get(name)
        if task:
            return task.apply_async(args, kwargs)
        else:
            logger.warning(f"[LiteQueue] Unknown task: {name}")
            return LiteTaskResult("unknown", {"error": f"Unknown task: {name}"})
    
    def signature(self, name: str):
        """Create a task signature."""
        return LiteTaskSignature(self, name)


class LiteTaskSignature:
    """Task signature for lite mode."""
    
    def __init__(self, app: LiteCeleryApp, name: str):
        self.app = app
        self.name = name
    
    def delay(self, *args, **kwargs) -> LiteTaskResult:
        return self.app.send_task(self.name, args, kwargs)
    
    def apply_async(self, args=None, kwargs=None) -> LiteTaskResult:
        return self.app.send_task(self.name, args, kwargs)


class LiteRedis:
    """In-memory Redis mock for lite mode."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lists: Dict[str, list] = {}
    
    def get(self, key: str) -> Optional[bytes]:
        value = self._data.get(key)
        if value is not None:
            return value.encode() if isinstance(value, str) else value
        return None
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        return True
    
    def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
            if key in self._lists:
                del self._lists[key]
                count += 1
        return count
    
    def rpush(self, key: str, *values: Any) -> int:
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        return len(self._lists[key])
    
    def lpop(self, key: str) -> Optional[Any]:
        if key in self._lists and self._lists[key]:
            return self._lists[key].pop(0)
        return None
    
    def lrange(self, key: str, start: int, end: int) -> list:
        if key not in self._lists:
            return []
        return self._lists[key][start:end + 1 if end != -1 else None]
    
    def exists(self, *keys: str) -> int:
        return sum(1 for k in keys if k in self._data or k in self._lists)
    
    def keys(self, pattern: str = "*") -> list:
        # Simple pattern matching
        if pattern == "*":
            return list(self._data.keys()) + list(self._lists.keys())
        # Basic prefix matching
        prefix = pattern.rstrip("*")
        return [k for k in list(self._data.keys()) + list(self._lists.keys()) 
                if k.startswith(prefix)]
    
    @classmethod
    def from_url(cls, url: str) -> "LiteRedis":
        return cls()


# Global instances for lite mode
_lite_redis: Optional[LiteRedis] = None
_lite_celery: Optional[LiteCeleryApp] = None


def get_lite_redis() -> LiteRedis:
    """Get lite Redis instance."""
    global _lite_redis
    if _lite_redis is None:
        _lite_redis = LiteRedis()
    return _lite_redis


def get_lite_celery() -> LiteCeleryApp:
    """Get lite Celery app."""
    global _lite_celery
    if _lite_celery is None:
        _lite_celery = LiteCeleryApp()
    return _lite_celery
