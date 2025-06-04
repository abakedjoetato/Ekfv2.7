"""
Fix Leaderboard Database Configuration - Ensure leaderboard config is in guild_configs collection
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_leaderboard_database():
    """Fix leaderboard configuration to be in the correct collection"""
    try:
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        events_channel_id = 1361522248451756234
        
        print("Fixing leaderboard database configuration...")
        
        # Update guild_configs collection with proper structure
        await db.guild_configs.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
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
            print(f"Leaderboard channel: {config.get('channels', {}).get('leaderboard')}")
        
        # Test the exact query the automated leaderboard uses
        query = {
            "$or": [
                {"channels.leaderboard": {"$exists": True, "$ne": None}},
                {"server_channels.default.leaderboard": {"$exists": True, "$ne": None}}
            ],
            "leaderboard_enabled": True
        }
        
        cursor = db.guild_configs.find(query)
        results = await cursor.to_list(length=None)
        
        print(f"\nQuery test - Found {len(results)} guilds with leaderboard config")
        for result in results:
            print(f"  Guild {result['guild_id']}: Channel {result.get('channels', {}).get('leaderboard')}")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_leaderboard_database())