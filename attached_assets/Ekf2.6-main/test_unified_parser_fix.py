"""
Test Unified Parser Fix - Verify SSH connection and player session tracking
"""

import asyncio
import sys
import os

# Add bot directory to path
sys.path.insert(0, os.path.join(os.getcwd(), 'bot'))

async def test_unified_parser():
    """Test the unified parser with the SSH connection fix"""
    try:
        from bot.parsers.scalable_unified_parser import ScalableUnifiedParser
        from bot.database.database_manager import DatabaseManager
        
        # Create mock bot with database manager
        class MockBot:
            def __init__(self):
                self.db_manager = None
                
            async def setup_db(self):
                self.db_manager = DatabaseManager()
                await self.db_manager.initialize()
                return True
        
        bot = MockBot()
        if not await bot.setup_db():
            print("❌ Database setup failed")
            return
        
        # Create parser
        parser = ScalableUnifiedParser(bot)
        
        print("🔍 Testing unified parser with SSH connection fix...")
        
        # Run parser manually
        await parser.run_log_parser()
        
        # Check if player sessions were created
        guild_id = 1219706687980568769
        sessions = await bot.db_manager.player_sessions.find(
            {'guild_id': guild_id, 'state': 'online'}
        ).to_list(length=10)
        
        print(f"✅ Found {len(sessions)} online player sessions")
        
        if sessions:
            for session in sessions:
                print(f"   Player: {session.get('character_name', session.get('player_name'))}")
                print(f"   Server: {session.get('server_name')}")
                print(f"   Status: {session.get('state')}")
        else:
            print("   No online sessions found - checking if connection worked...")
            
            # Check all sessions regardless of state
            all_sessions = await bot.db_manager.player_sessions.find(
                {'guild_id': guild_id}
            ).to_list(length=10)
            print(f"   Total sessions in database: {len(all_sessions)}")
        
        await bot.db_manager.close()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_unified_parser())