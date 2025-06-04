"""
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
        print("\nTest 1: Thread-Safe Database Wrapper")
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
        print("\nTest 2: Threaded Parser Wrapper")
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
    
    print("\n🎉 AsyncIO Loop Fix Verification Completed!")

if __name__ == "__main__":
    asyncio.run(verify_asyncio_fixes())
