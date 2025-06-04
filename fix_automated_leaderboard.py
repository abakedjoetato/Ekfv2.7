
"""
Fix Automated Leaderboard Configuration
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_automated_leaderboard():
    """Fix automated leaderboard configuration"""
    try:
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        events_channel_id = 1361522248451756234  # Events channel
        
        print("Fixing automated leaderboard configuration...")
        
        # Update guild_configs collection with proper structure
        await db.guild_configs.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "guild_id": guild_id,
                    "leaderboard_enabled": True,
                    "leaderboard_channel": events_channel_id,
                    "leaderboard_interval_minutes": 60
                }
            },
            upsert=True
        )
        
        print("✅ Updated guild_configs collection")
        
        # Verify the configuration
        config = await db.guild_configs.find_one({"guild_id": guild_id})
        if config:
            print(f"Guild ID: {config['guild_id']}")
            print(f"Leaderboard enabled: {config.get('leaderboard_enabled', False)}")
            print(f"Leaderboard channel: {config.get('leaderboard_channel')}")
        
        # Test the query the automated leaderboard uses
        query = {
            "leaderboard_enabled": True,
            "leaderboard_channel": {"$exists": True, "$ne": None}
        }
        
        print(f"\nTesting automated leaderboard query:")
        cursor = db.guild_configs.find(query)
        guilds_with_leaderboard = await cursor.to_list(length=None)
        
        print(f"Found {len(guilds_with_leaderboard)} guilds with leaderboard configured")
        for guild_config in guilds_with_leaderboard:
            print(f"  Guild {guild_config['guild_id']}: Channel {guild_config.get('leaderboard_channel')}")
        
        client.close()
        print("✅ Automated leaderboard configuration fixed")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_automated_leaderboard())
