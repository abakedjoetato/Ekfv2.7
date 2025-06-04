"""
Test Player Session Tracking - Simulate log processing to verify session updates
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager
from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor

class MockBot:
    def __init__(self, db_manager):
        self.db_manager = db_manager

async def test_player_session_tracking():
    """Test player session tracking with simulated log data"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        # Create mock bot and processor
        bot = MockBot(db_manager)
        processor = ScalableUnifiedProcessor(bot)
        
        # Simulate log data with connection events
        test_log_data = """[2025.06.04-17.00.01:123456] Player "TestPlayer1" (id=12345) has been connected
[2025.06.04-17.00.05:234567] Player "TestPlayer2" (id=23456) has been connected
[2025.06.04-17.01.30:345678] Player "TestPlayer1" (id=12345) has been disconnected
[2025.06.04-17.02.15:456789] Mission Survivor: PvP Event
[2025.06.04-17.03.00:567890] Player "TestPlayer3" (id=34567) has been connected"""
        
        # Server configuration
        server_config = {
            'name': 'Test Server',
            'guild_id': 1219706687980568769,  # Emerald Servers guild ID
            'path': '/test/path'
        }
        
        print("Processing test log data...")
        
        # Process the log data
        events = await processor.process_log_data(test_log_data, server_config)
        print(f"Parsed {len(events)} events from log data")
        
        for event in events:
            print(f"  Event: {event['type']} - {event.get('event', event.get('raw_message'))}")
        
        # Update player sessions
        if events:
            success = await processor.update_player_sessions(events)
            print(f"Player session update success: {success}")
        
        # Check resulting player sessions
        guild_id = server_config['guild_id']
        total_sessions = await db_manager.player_sessions.count_documents({'guild_id': guild_id})
        online_sessions = await db_manager.player_sessions.count_documents({
            'guild_id': guild_id,
            'state': 'online'
        })
        
        print(f"\nDatabase Results:")
        print(f"  Total sessions: {total_sessions}")
        print(f"  Online sessions: {online_sessions}")
        
        # List all sessions
        sessions = await db_manager.player_sessions.find({'guild_id': guild_id}).to_list(length=20)
        print(f"\nPlayer Sessions:")
        for session in sessions:
            print(f"  {session.get('character_name')} - {session.get('state')} - Last seen: {session.get('last_seen')}")
        
        await client.close()
        print(f"\nTest completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_player_session_tracking())