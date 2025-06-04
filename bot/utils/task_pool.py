"""
Thread Pool Manager for Non-Blocking Task Execution
Eliminates command timeouts by moving heavy operations to background threads
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable, Dict, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class TaskTimer:
    """Context manager for tracking task execution time"""
    
    def __init__(self, label: str):
        self.label = label
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"🚀 Starting task: {self.label}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type:
                logger.error(f"❌ Task {self.label} failed after {duration:.2f}s: {exc_val}")
            else:
                logger.info(f"✅ Task {self.label} completed in {duration:.2f}s")

class TaskPool:
    """Thread pool manager for non-blocking task execution"""
    
    def __init__(self, max_workers: int = 20, task_timeout: int = 300):
        self.max_workers = max_workers
        self.task_timeout = task_timeout
        self.executor = None
        self.semaphore = None
        self._task_locks: Dict[str, asyncio.Lock] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize the task pool"""
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="TaskPool")
        self.semaphore = asyncio.Semaphore(self.max_workers)
        logger.info(f"🔧 TaskPool initialized with {self.max_workers} workers")
        
    async def shutdown(self):
        """Clean shutdown of task pool"""
        if self.executor:
            logger.info("🔄 Shutting down TaskPool...")
            
            # Cancel active tasks
            for task_id, task in self._active_tasks.items():
                if not task.done():
                    logger.info(f"⏹️ Cancelling active task: {task_id}")
                    task.cancel()
            
            # Wait for tasks to complete with timeout
            if self._active_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._active_tasks.values(), return_exceptions=True),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Some tasks did not complete within shutdown timeout")
            
            # Shutdown executor
            self.executor.shutdown(wait=True, cancel_futures=True)
            logger.info("✅ TaskPool shutdown completed")
    
    def get_task_lock(self, lock_key: str) -> asyncio.Lock:
        """Get or create a lock for task deduplication"""
        if lock_key not in self._task_locks:
            self._task_locks[lock_key] = asyncio.Lock()
        return self._task_locks[lock_key]
    
    async def run(self, func: Callable, *args, task_id: str = None, timeout: Optional[int] = None, **kwargs) -> Any:
        """Run a function in the thread pool with proper error handling"""
        
        if not self.executor:
            raise RuntimeError("TaskPool not initialized. Call initialize() first.")
        
        task_timeout = timeout or self.task_timeout
        task_label = task_id or f"{func.__name__}({len(args)} args)"
        
        async with self.semaphore:
            try:
                with TaskTimer(task_label):
                    loop = asyncio.get_event_loop()
                    
                    # Create future and track it
                    future = loop.run_in_executor(
                        self.executor, 
                        lambda: func(*args, **kwargs)
                    )
                    
                    if task_id:
                        self._active_tasks[task_id] = future
                    
                    try:
                        result = await asyncio.wait_for(future, timeout=task_timeout)
                        return result
                        
                    except asyncio.TimeoutError:
                        logger.error(f"⏰ Task {task_label} timed out after {task_timeout}s")
                        future.cancel()
                        raise
                        
                    finally:
                        if task_id and task_id in self._active_tasks:
                            del self._active_tasks[task_id]
                            
            except Exception as e:
                logger.exception(f"❌ Task {task_label} failed: {e}")
                raise
    
    async def run_with_lock(self, func: Callable, *args, lock_key: str, task_id: str = None, **kwargs) -> Any:
        """Run a function with task deduplication using locks"""
        
        async with self.get_task_lock(lock_key):
            return await self.run(func, *args, task_id=task_id, **kwargs)

# Global task pool instance
_global_task_pool: Optional[TaskPool] = None

async def get_task_pool() -> TaskPool:
    """Get or create the global task pool instance"""
    global _global_task_pool
    
    if _global_task_pool is None:
        _global_task_pool = TaskPool(max_workers=20)
        await _global_task_pool.initialize()
    
    return _global_task_pool

async def dispatch_background(func: Callable, *args, task_id: str = None, timeout: Optional[int] = None, **kwargs) -> Any:
    """Universal background task dispatcher"""
    
    task_pool = await get_task_pool()
    return await task_pool.run(func, *args, task_id=task_id, timeout=timeout, **kwargs)

async def dispatch_background_with_lock(func: Callable, *args, lock_key: str, task_id: str = None, **kwargs) -> Any:
    """Background task dispatcher with deduplication"""
    
    task_pool = await get_task_pool()
    return await task_pool.run_with_lock(func, *args, lock_key=lock_key, task_id=task_id, **kwargs)

async def shutdown_task_pool():
    """Shutdown the global task pool"""
    global _global_task_pool
    
    if _global_task_pool:
        await _global_task_pool.shutdown()
        _global_task_pool = None

@asynccontextmanager
async def task_pool_context():
    """Context manager for task pool lifecycle"""
    try:
        yield await get_task_pool()
    finally:
        await shutdown_task_pool()