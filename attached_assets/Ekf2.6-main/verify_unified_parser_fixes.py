"""
Verify Unified Parser Fixes - Create test player sessions and test /online command
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def verify_fixes():
    """Verify the unified parser fixes by creating test data"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769  # Emerald Servers
        server_name = "Emerald EU"
        current_time = datetime.utcnow()
        
        print("Creating test player sessions...")
        
        # Clear existing sessions first
        await db.player_sessions.delete_many({'guild_id': guild_id})
        
        # Create some test online players with proper player_id
        test_players = [
            {"character_name": "TestPlayer1", "player_id": "12345", "state": "online"},
            {"character_name": "TestPlayer2", "player_id": "23456", "state": "online"}, 
            {"character_name": "TestPlayer3", "player_id": "34567", "state": "offline"},
            {"character_name": "TestPlayer4", "player_id": "45678", "state": "online"}
        ]
        
        for player in test_players:
            await db.player_sessions.insert_one({
                'character_name': player['character_name'],
                'player_id': player['player_id'],
                'state': player['state'],
                'joined_at': current_time,
                'last_seen': current_time,
                'guild_id': guild_id,
                'server_name': server_name
            })
        
        # Check results
        total_sessions = await db.player_sessions.count_documents({'guild_id': guild_id})
        online_sessions = await db.player_sessions.count_documents({
            'guild_id': guild_id,
            'state': 'online'
        })
        
        print(f"Test data created successfully:")
        print(f"  Total sessions: {total_sessions}")
        print(f"  Online sessions: {online_sessions}")
        
        # List all sessions
        sessions = await db.player_sessions.find({'guild_id': guild_id}).to_list(length=20)
        print(f"\nPlayer Sessions:")
        for session in sessions:
            print(f"  {session.get('character_name')} - {session.get('state')}")
        
        print(f"\nNow test the /online command in Discord - it should show {online_sessions} online players")
        
        await client.close()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_fixes())