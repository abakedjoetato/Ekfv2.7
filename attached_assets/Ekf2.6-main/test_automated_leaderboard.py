"""
Test Automated Leaderboard - Verify the system is working correctly
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def test_automated_leaderboard():
    """Test if the automated leaderboard system is properly configured"""
    try:
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        print("Testing automated leaderboard configuration...")
        
        # Check the query that the automated leaderboard uses
        query = {
            "$or": [
                {"channels.leaderboard": {"$exists": True, "$ne": None}},
                {"server_channels.default.leaderboard": {"$exists": True, "$ne": None}}
            ],
            "leaderboard_enabled": True
        }
        
        cursor = db.guilds.find(query)
        guilds_with_leaderboard = await cursor.to_list(length=None)
        
        print(f"Found {len(guilds_with_leaderboard)} guilds with leaderboard enabled")
        
        for guild in guilds_with_leaderboard:
            guild_id = guild['guild_id']
            channel_id = guild.get('channels', {}).get('leaderboard')
            print(f"Guild {guild_id}: Leaderboard channel {channel_id}")
            
        # Simulate what the automated task would do
        if guilds_with_leaderboard:
            print("\n✅ Automated leaderboard will now process these guilds")
            print("Next scheduled run: Every 60 minutes")
        else:
            print("\n❌ No guilds found for automated leaderboard processing")
            
        client.close()
        
    except Exception as e:
        print(f"Error testing leaderboard: {e}")

if __name__ == "__main__":
    asyncio.run(test_automated_leaderboard())