"""
Check Leaderboard Configuration - Debug why automated leaderboard finds 0 guilds
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

async def check_leaderboard_config():
    """Check current leaderboard configuration in database"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        print("Checking leaderboard configuration...")
        
        # Check guild configuration
        guild_id = 1219706687980568769
        guild_config = await db.guilds.find_one({"guild_id": guild_id})
        
        if guild_config:
            print(f"Guild config found for {guild_id}")
            print(f"Leaderboard enabled: {guild_config.get('leaderboard_enabled', False)}")
            print(f"Channels config: {guild_config.get('channels', {})}")
            print(f"Server channels config: {guild_config.get('server_channels', {})}")
        else:
            print(f"No guild config found for {guild_id}")
            
        # Check what the automated leaderboard query would find
        query = {
            "$or": [
                {"channels.leaderboard": {"$exists": True, "$ne": None}},
                {"server_channels.default.leaderboard": {"$exists": True, "$ne": None}}
            ],
            "leaderboard_enabled": True
        }
        
        print(f"\nQuerying with automated leaderboard criteria:")
        print(f"Query: {query}")
        
        cursor = db.guilds.find(query)
        guilds_with_leaderboard = await cursor.to_list(length=None)
        
        print(f"Found {len(guilds_with_leaderboard)} guilds with leaderboard config")
        
        if guilds_with_leaderboard:
            for guild in guilds_with_leaderboard:
                print(f"Guild {guild['guild_id']}: {guild.get('channels', {})}")
        
        # Check if we need to enable leaderboard for this guild
        if not guild_config or not guild_config.get('leaderboard_enabled'):
            print("\nLeaderboard not enabled for this guild - enabling now...")
            await db.guilds.update_one(
                {"guild_id": guild_id},
                {
                    "$set": {
                        "leaderboard_enabled": True,
                        "channels.leaderboard": None  # Will be set when user configures with /setchannel
                    }
                },
                upsert=True
            )
            print("✅ Leaderboard enabled for guild")
        
        client.close()
        
    except Exception as e:
        print(f"Error checking leaderboard config: {e}")

if __name__ == "__main__":
    asyncio.run(check_leaderboard_config())