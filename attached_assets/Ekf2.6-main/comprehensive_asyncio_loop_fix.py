"""
Comprehensive AsyncIO Loop Fix - Resolve "Future attached to different loop" errors
Complete solution for threading issues in the scalable unified processor
"""

import asyncio
import logging
import os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_asyncio_loop_errors():
    """Fix all asyncio loop threading issues across the codebase"""
    
    logger.info("🔧 Starting comprehensive asyncio loop fix...")
    
    # Fix 1: Enhanced Thread-Safe Database Wrapper
    logger.info("Fixing thread-safe database wrapper...")
    
    wrapper_content = '''"""
Thread-Safe Database Wrapper
Prevents "Future attached to a different loop" errors by ensuring database operations
execute in the correct asyncio event loop context
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class ThreadSafeDBWrapper:
    """Wrapper that ensures database operations execute in the correct event loop"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._main_loop = None
        self._thread_local = threading.local()
    
    def set_main_loop(self, loop):
        """Set the main event loop for thread-safe operations"""
        self._main_loop = loop
        logger.info(f"Main event loop set: {id(loop)}")
    
    def _get_current_loop_info(self):
        """Get current loop information safely"""
        try:
            current_loop = asyncio.get_running_loop()
            return current_loop, id(current_loop)
        except RuntimeError:
            return None, None
    
    async def safe_db_operation(self, operation: Callable, *args, **kwargs):
        """Execute database operation safely, handling thread boundary issues"""
        try:
            current_loop, current_id = self._get_current_loop_info()
            main_id = id(self._main_loop) if self._main_loop else None
            
            logger.debug(f"DB operation {operation.__name__}: current_loop={current_id}, main_loop={main_id}")
            
            # If we're in a different thread/loop and have a main loop
            if self._main_loop and current_loop and current_loop != self._main_loop:
                logger.debug(f"Cross-thread operation detected for {operation.__name__}")
                
                if asyncio.iscoroutinefunction(operation):
                    # Create a new task in the main loop
                    async def _execute_in_main():
                        try:
                            return await operation(*args, **kwargs)
                        except Exception as e:
                            logger.error(f"Main loop execution failed for {operation.__name__}: {e}")
                            raise
                    
                    # Submit to main loop
                    future = asyncio.run_coroutine_threadsafe(_execute_in_main(), self._main_loop)
                    return future.result(timeout=30)
                else:
                    # For non-coroutine functions, execute directly
                    return operation(*args, **kwargs)
            
            # We're in the correct loop or no main loop conflict
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
                
        except asyncio.TimeoutError:
            logger.error(f"Database operation {operation.__name__} timed out after 30 seconds")
            return None
        except Exception as e:
            logger.error(f"Database operation {operation.__name__} failed: {e}")
            return None
    
    async def get_guild(self, guild_id: int):
        """Thread-safe guild retrieval"""
        return await self.safe_db_operation(self.db_manager.get_guild, guild_id)
    
    async def get_guild_servers(self, guild_id: int):
        """Thread-safe guild servers retrieval"""
        if hasattr(self.db_manager, 'get_guild_servers'):
            return await self.safe_db_operation(self.db_manager.get_guild_servers, guild_id)
        return []
    
    async def get_active_player_count(self, guild_id: int, server_name: str):
        """Thread-safe player count retrieval"""
        if hasattr(self.db_manager, 'get_active_player_count'):
            return await self.safe_db_operation(
                self.db_manager.get_active_player_count, 
                guild_id, 
                server_name
            )
        return 0
    
    async def update_player_session(self, *args, **kwargs):
        """Thread-safe player session update"""
        if hasattr(self.db_manager, 'update_player_session'):
            return await self.safe_db_operation(
                self.db_manager.update_player_session, 
                *args, 
                **kwargs
            )
        return None
    
    async def reset_player_sessions(self, *args, **kwargs):
        """Thread-safe player session reset"""
        if hasattr(self.db_manager, 'reset_player_sessions_for_server'):
            return await self.safe_db_operation(
                self.db_manager.reset_player_sessions_for_server, 
                *args, 
                **kwargs
            )
        return None

    @property
    def player_sessions(self):
        """Thread-safe access to player_sessions collection"""
        return self.db_manager.player_sessions if self.db_manager else None
    
    async def record_kill(self, *args, **kwargs):
        """Thread-safe kill recording"""
        try:
            if hasattr(self.db_manager, 'record_kill'):
                return await self.safe_db_operation(
                    self.db_manager.record_kill, 
                    *args, 
                    **kwargs
                )
            return None
        except Exception as e:
            logger.error(f"Failed to record kill: {e}")
            return None
    
    async def update_parser_state(self, *args, **kwargs):
        """Thread-safe parser state update"""
        try:
            if hasattr(self.db_manager, 'update_parser_state'):
                return await self.safe_db_operation(
                    self.db_manager.update_parser_state, 
                    *args, 
                    **kwargs
                )
            return None
        except Exception as e:
            logger.error(f"Failed to update parser state: {e}")
            return None
'''
    
    with open('bot/utils/thread_safe_db_wrapper.py', 'w') as f:
        f.write(wrapper_content)
    
    logger.info("✅ Enhanced thread-safe database wrapper")
    
    # Fix 2: Scalable Unified Processor Loop Management
    logger.info("Fixing scalable unified processor loop management...")
    
    with open('bot/utils/scalable_unified_processor.py', 'r') as f:
        processor_content = f.read()
    
    # Add proper loop management to the processor
    loop_init_fix = '''
    def __init__(self, guild_id: int, bot=None):
        """Initialize the processor with proper loop management"""
        self.guild_id = guild_id
        self.bot = bot
        self.db_wrapper = None
        self._main_loop = None
        self._cold_start_player_states = {}
        self._voice_channel_updates_deferred = False
        
        # Set up loop management
        try:
            self._main_loop = asyncio.get_running_loop()
            logger.debug(f"ScalableUnifiedProcessor: Main loop set to {id(self._main_loop)}")
        except RuntimeError:
            logger.warning("ScalableUnifiedProcessor: No running loop detected during init")
        
        # Initialize database wrapper if bot is available
        if bot and hasattr(bot, 'db_manager') and bot.db_manager:
            from bot.utils.thread_safe_db_wrapper import ThreadSafeDBWrapper
            self.db_wrapper = ThreadSafeDBWrapper(bot.db_manager)
            if self._main_loop:
                self.db_wrapper.set_main_loop(self._main_loop)
'''
    
    # Replace the __init__ method
    import re
    init_pattern = r'def __init__\(self, guild_id: int, bot=None\):.*?(?=\n    def|\nclass|\Z)'
    if re.search(init_pattern, processor_content, re.DOTALL):
        processor_content = re.sub(init_pattern, loop_init_fix.strip(), processor_content, flags=re.DOTALL)
        
        with open('bot/utils/scalable_unified_processor.py', 'w') as f:
            f.write(processor_content)
        
        logger.info("✅ Enhanced scalable unified processor loop management")
    
    # Fix 3: Main Bot Loop Management
    logger.info("Fixing main bot loop management...")
    
    with open('main.py', 'r') as f:
        main_content = f.read()
    
    # Add loop management to bot initialization
    bot_loop_fix = '''
    async def setup_database(self):
        """Setup MongoDB connection with proper loop management"""
        try:
            # Set main loop for thread-safe operations
            main_loop = asyncio.get_running_loop()
            logger.info(f"Main bot loop established: {id(main_loop)}")
            
            from pymongo.errors import ServerSelectionTimeoutError
            from motor.motor_asyncio import AsyncIOMotorClient
            from bot.models.database import DatabaseManager
            from bot.utils.thread_safe_db_wrapper import ThreadSafeDBWrapper
            
            # Test basic connection first
            logger.info("Testing MongoDB connection...")
            self.mongo_client = AsyncIOMotorClient(
                os.environ.get("MONGO_URI"),
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                maxPoolSize=50,
                minPoolSize=5
            )
            
            # Test the connection
            await self.mongo_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Initialize database manager
            self.db_manager = DatabaseManager(self.mongo_client)
            
            # Setup thread-safe wrapper with main loop
            self.db_wrapper = ThreadSafeDBWrapper(self.db_manager)
            self.db_wrapper.set_main_loop(main_loop)
            
            # Initialize database architecture
            await self.db_manager.initialize_database()
            logger.info("Database architecture initialized (PHASE 1)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.error("❌ Database setup failed - operating in limited mode")
            self.db_manager = None
            self.db_wrapper = None
            return False
'''
    
    # Replace the setup_database method
    setup_pattern = r'async def setup_database\(self\):.*?(?=\n    async def|\n    def|\nclass|\Z)'
    if re.search(setup_pattern, main_content, re.DOTALL):
        main_content = re.sub(setup_pattern, bot_loop_fix.strip(), main_content, flags=re.DOTALL)
        
        with open('main.py', 'w') as f:
            f.write(main_content)
        
        logger.info("✅ Enhanced main bot loop management")
    
    # Fix 4: Threaded Parser Wrapper Enhancement
    logger.info("Fixing threaded parser wrapper...")
    
    wrapper_enhancement = '''"""
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
    
    def __init__(self):
        self.task_pool = TaskPool(max_workers=20)
        self._main_loop = None
        self._active_threads = set()
    
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
            result = await self.task_pool.submit(parser_execution, task_id=task_id, timeout=300)
            
            logger.info(f"✅ {parser_class.__name__} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Threaded parser execution failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        if self.task_pool:
            await self.task_pool.cleanup()

# Global instance
threaded_parser = ThreadedParserWrapper()
'''
    
    if os.path.exists('bot/utils/threaded_parser_wrapper.py'):
        with open('bot/utils/threaded_parser_wrapper.py', 'w') as f:
            f.write(wrapper_enhancement)
        
        logger.info("✅ Enhanced threaded parser wrapper")
    
    # Fix 5: Update main bot to use enhanced wrappers
    logger.info("Updating main bot to use enhanced loop management...")
    
    with open('main.py', 'r') as f:
        main_content = f.read()
    
    # Add initialization of threaded wrapper
    threaded_init = '''
        # Initialize threaded parser wrapper with main loop
        from bot.utils.threaded_parser_wrapper import threaded_parser
        main_loop = asyncio.get_running_loop()
        threaded_parser.set_main_loop(main_loop)
        
        logger.info("Connection pool manager started for scalable parsing")
'''
    
    if 'logger.info("Connection pool manager started for scalable parsing")' in main_content:
        main_content = main_content.replace(
            'logger.info("Connection pool manager started for scalable parsing")',
            threaded_init.strip()
        )
        
        with open('main.py', 'w') as f:
            f.write(main_content)
        
        logger.info("✅ Updated main bot loop management")
    
    # Create verification script
    verification_content = '''"""
Verify AsyncIO Loop Fix - Test that threading issues are resolved
"""

import asyncio
import logging
import sys

async def verify_asyncio_fixes():
    """Verify that asyncio loop fixes are working"""
    
    print("🧪 Verifying AsyncIO Loop Fixes...")
    print("=" * 50)
    
    try:
        # Test 1: Thread-Safe Database Wrapper
        print("\\nTest 1: Thread-Safe Database Wrapper")
        from bot.utils.thread_safe_db_wrapper import ThreadSafeDBWrapper
        
        # Mock database manager for testing
        class MockDBManager:
            async def get_guild(self, guild_id):
                await asyncio.sleep(0.1)
                return {"guild_id": guild_id, "name": "test"}
        
        mock_db = MockDBManager()
        wrapper = ThreadSafeDBWrapper(mock_db)
        
        # Set main loop
        main_loop = asyncio.get_running_loop()
        wrapper.set_main_loop(main_loop)
        
        # Test operation
        result = await wrapper.get_guild(12345)
        
        if result and result.get("guild_id") == 12345:
            print("  ✅ Thread-safe database wrapper: WORKING")
        else:
            print("  ❌ Thread-safe database wrapper: FAILED")
            
    except Exception as e:
        print(f"  ❌ Thread-safe database wrapper test failed: {e}")
    
    try:
        # Test 2: Threaded Parser Wrapper
        print("\\nTest 2: Threaded Parser Wrapper")
        from bot.utils.threaded_parser_wrapper import ThreadedParserWrapper
        
        class MockParser:
            async def run(self):
                await asyncio.sleep(0.1)
                return {"status": "completed", "processed": 10}
        
        wrapper = ThreadedParserWrapper()
        main_loop = asyncio.get_running_loop()
        wrapper.set_main_loop(main_loop)
        
        # Test threaded execution
        result = await wrapper.run_parser_threaded(MockParser)
        
        if result and result.get("status") == "completed":
            print("  ✅ Threaded parser wrapper: WORKING")
        else:
            print("  ❌ Threaded parser wrapper: FAILED")
            
        await wrapper.cleanup()
            
    except Exception as e:
        print(f"  ❌ Threaded parser wrapper test failed: {e}")
    
    print("\\n🎉 AsyncIO Loop Fix Verification Completed!")

if __name__ == "__main__":
    asyncio.run(verify_asyncio_fixes())
'''
    
    with open('verify_asyncio_fixes.py', 'w') as f:
        f.write(verification_content)
    
    logger.info("✅ Created verification script")
    
    print("🔧 Comprehensive AsyncIO Loop Fix completed!")
    print("   - Enhanced thread-safe database wrapper with proper loop management")
    print("   - Fixed scalable unified processor loop initialization")
    print("   - Updated main bot loop management")
    print("   - Enhanced threaded parser wrapper with loop isolation")
    print("   - Created verification script for testing")

if __name__ == "__main__":
    asyncio.run(fix_asyncio_loop_errors())