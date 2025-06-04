"""
Configure Leaderboard System - Set up automated leaderboard with proper channel routing
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

async def configure_leaderboard_system():
    """Configure the leaderboard system to use existing channel setup"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        print("Configuring leaderboard system...")
        
        # Get current guild configuration
        guild_config = await db.guild_configs.find_one({"guild_id": guild_id})
        if not guild_config:
            print("No guild config found")
            return
            
        print(f"Found guild config with {len(guild_config.get('servers', []))} servers")
        
        # Check current channel configuration
        channels = guild_config.get('channels', [])
        print(f"Current channels: {channels}")
        
        # Find events channel from the list
        events_channel_id = None
        for channel in channels:
            if 'events' in channel.get('embed_types', []):
                events_channel_id = channel.get('channel_id')
                break
        if events_channel_id:
            print(f"Setting leaderboard channel to events channel: {events_channel_id}")
            
            # Update guild config to enable leaderboard
            await db.guild_configs.update_one(
                {"guild_id": guild_id},
                {
                    "$set": {
                        "leaderboard_enabled": True,
                        "channels.leaderboard": events_channel_id,
                        "leaderboard_interval_minutes": 60  # Update every hour
                    }
                }
            )
            
            # Also update the guilds collection for the automated task
            await db.guilds.update_one(
                {"guild_id": guild_id},
                {
                    "$set": {
                        "leaderboard_enabled": True,
                        "channels.leaderboard": events_channel_id,
                        "leaderboard_interval_minutes": 60
                    }
                },
                upsert=True
            )
            
            print("✅ Leaderboard system configured")
            
        else:
            print("No events channel configured - leaderboard needs a channel to post to")
            
        # Verify configuration
        updated_config = await db.guilds.find_one({"guild_id": guild_id})
        if updated_config:
            print(f"Verification - Leaderboard enabled: {updated_config.get('leaderboard_enabled')}")
            print(f"Verification - Leaderboard channel: {updated_config.get('channels', {}).get('leaderboard')}")
        
        client.close()
        
    except Exception as e:
        print(f"Error configuring leaderboard: {e}")

if __name__ == "__main__":
    asyncio.run(configure_leaderboard_system())