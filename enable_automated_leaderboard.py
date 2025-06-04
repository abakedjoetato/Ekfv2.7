"""
Enable Automated Leaderboard - Configure leaderboard system for the guild
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def enable_automated_leaderboard():
    """Enable automated leaderboard for the guild"""
    try:
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        events_channel_id = 1361522248451756234  # Events channel from channel config
        
        print("Enabling automated leaderboard...")
        
        # Update guilds collection for automated leaderboard task
        await db.guilds.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "leaderboard_enabled": True,
                    "channels": {"leaderboard": events_channel_id},
                    "leaderboard_interval_minutes": 60
                }
            },
            upsert=True
        )
        
        print(f"✅ Automated leaderboard enabled")
        print(f"Channel: {events_channel_id}")
        print(f"Interval: 60 minutes")
        
        # Verify configuration
        config = await db.guilds.find_one({"guild_id": guild_id})
        if config and config.get('leaderboard_enabled'):
            print("✅ Configuration verified")
        else:
            print("❌ Configuration failed")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(enable_automated_leaderboard())