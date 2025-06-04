"""
Threaded Parser Wrapper - Enhanced with proper loop management
Prevents asyncio loop conflicts during threaded operations
"""

import asyncio
import logging
import threading
from typing import Any, Callable
from bot.utils.task_pool import TaskPool

logger = logging.getLogger(__name__)

class ThreadedParserWrapper:
    """Enhanced wrapper for running parsers in background threads with proper loop management"""
    
    def __init__(self, parser=None):
        self.task_pool = TaskPool(max_workers=20)
        self._main_loop = None
        self._active_threads = set()
        self.parser = parser
    
    def set_main_loop(self, loop):
        """Set the main event loop for coordination"""
        self._main_loop = loop
        logger.info(f"ThreadedParserWrapper: Main loop set to {id(loop)}")
    
    async def run_parser_threaded(self, parser_class, *args, **kwargs):
        """Run parser in background thread with proper loop isolation"""
        try:
            # Create a unique task ID
            task_id = f"{parser_class.__name__}_run_global"
            
            logger.info(f"🔄 Starting {parser_class.__name__} in background thread...")
            
            # Define the parser execution function
            def parser_execution():
                """Execute parser in isolated thread with new event loop"""
                try:
                    # Create new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # Create parser instance
                    parser = parser_class(*args, **kwargs)
                    
                    # Run the parser
                    result = new_loop.run_until_complete(parser.run())
                    
                    # Clean up
                    new_loop.close()
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"{parser_class.__name__} execution failed: {e}")
                    raise
            
            # Submit to task pool
            result = await self.task_pool.run(parser_execution, task_id=task_id, timeout=300)
            
            logger.info(f"✅ {parser_class.__name__} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Threaded parser execution failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        if self.task_pool:
            await self.task_pool.shutdown()

# Global instance
threaded_parser = ThreadedParserWrapper()
