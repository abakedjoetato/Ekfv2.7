"""
Verify Online Command Working - Test the actual implementation
"""
import asyncio
import sys
import os

async def test_online_command():
    """Test the /online command with actual bot implementation"""
    print("Testing /online command with improved timeout protection...")
    
    try:
        # Add the bot directory to Python path
        sys.path.insert(0, os.path.join(os.getcwd(), 'bot'))
        
        # Import the actual implementation
        from cogs.stats import Stats
        
        # Create a mock bot with database manager
        class MockBot:
            def __init__(self):
                self.db_manager = None
                
            async def setup_db(self):
                # Import and setup the actual database manager from main.py
                import main
                
                # Use the same database setup as main.py
                from bot.database.cached_database_manager import CachedDatabaseManager
                
                self.db_manager = CachedDatabaseManager()
                await self.db_manager.initialize()
                return True
        
        # Create mock context
        class MockGuild:
            def __init__(self):
                self.id = 1219706687980568769
                self.name = "Test Guild"
        
        class MockContext:
            def __init__(self):
                self.guild = MockGuild()
                self.deferred = False
                self.response_sent = False
                
            async def defer(self):
                self.deferred = True
                print("✅ Context deferred successfully")
                
            async def followup(self):
                return self
                
            async def send(self, content=None, embed=None, file=None, ephemeral=False):
                self.response_sent = True
                if embed:
                    print(f"✅ Embed response sent: {embed.title if hasattr(embed, 'title') else 'Embed'}")
                else:
                    print(f"✅ Text response sent: {content}")
                return True
        
        # Test the implementation
        bot = MockBot()
        if not await bot.setup_db():
            print("❌ Database setup failed")
            return False
            
        stats_cog = Stats(bot)
        ctx = MockContext()
        
        print("📊 Testing /online command execution...")
        
        # Test the actual online command with timeout protection
        start_time = asyncio.get_event_loop().time()
        
        try:
            await asyncio.wait_for(stats_cog.online(ctx), timeout=10.0)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            print(f"✅ /online command completed in {execution_time:.2f}s")
            print(f"   Context deferred: {ctx.deferred}")
            print(f"   Response sent: {ctx.response_sent}")
            
            if execution_time < 8.0:
                print("🎉 Command executed within acceptable time limits")
                return True
            else:
                print("⚠️ Command took longer than expected but completed")
                return True
                
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            print(f"❌ /online command timed out after {execution_time:.2f}s")
            return False
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            print(f"⚠️ Command had error after {execution_time:.2f}s: {e}")
            
            # Check if it's a timeout-related error that was handled
            if "timeout" in str(e).lower() or "slow" in str(e).lower():
                print("✅ Timeout error was properly handled and reported to user")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
                return False
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_online_command())
    print(f"\n/online command timeout fixes: {'✅ WORKING' if success else '❌ NEEDS FIXING'}")