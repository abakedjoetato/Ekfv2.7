#!/usr/bin/env python3
"""
Configure Discord Channels for Event Delivery
Set up proper channel configuration for mission, helicrash, and event embeds
"""
import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def configure_channels():
    """Configure Discord channels for proper event delivery"""
    try:
        # Connect to MongoDB
        mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = mongo_client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        print(f"=== CONFIGURING DISCORD CHANNELS ===")
        
        # Get current guild configuration
        guild_config = await db.guilds.find_one({"guild_id": guild_id})
        
        if not guild_config:
            print("No guild configuration found - creating new configuration")
            guild_config = {
                "guild_id": guild_id,
                "servers": [],
                "premium": False
            }
        
        # Configure server channels for event delivery
        server_config = {
            "_id": "7020",
            "name": "Emerald EU",
            "host": "79.127.236.1",
            "port": 8822,
            "username": "baked",
            "log_path": "/home/baked/servers/server_{server_id}/logs/Deadside.log",
            "max_players": 50,
            "channels": {
                "mission": 1361147601298129129,  # Configure mission channel
                "event": 1361147601298129129,    # Configure event channel (helicrash, airdrop, trader)
                "voice": 1361147601298129129,    # Configure voice channel for player count
                "killfeed": 1361147601298129129, # Configure killfeed channel
                "connections": 1361147601298129129 # Configure connection events
            },
            "enabled": True,
            "killfeed_enabled": False,
            "unified_logging": True
        }
        
        # Update or create server configuration
        await db.guilds.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "guild_id": guild_id,
                    "servers": [server_config],
                    "premium": False
                }
            },
            upsert=True
        )
        
        print(f"✅ Configured channels for Emerald EU server")
        print(f"  Mission channel: {server_config['channels']['mission']}")
        print(f"  Event channel: {server_config['channels']['event']}")
        print(f"  Voice channel: {server_config['channels']['voice']}")
        print(f"  Killfeed channel: {server_config['channels']['killfeed']}")
        print(f"  Connection channel: {server_config['channels']['connections']}")
        
        # Verify configuration
        updated_config = await db.guilds.find_one({"guild_id": guild_id})
        if updated_config and updated_config.get('servers'):
            server = updated_config['servers'][0]
            channels = server.get('channels', {})
            
            print(f"\n=== VERIFICATION ===")
            print(f"Guild ID: {updated_config['guild_id']}")
            print(f"Server count: {len(updated_config['servers'])}")
            print(f"Channels configured: {len(channels)}")
            
            channel_types = ['mission', 'event', 'voice', 'killfeed', 'connections']
            for channel_type in channel_types:
                channel_id = channels.get(channel_type)
                status = "✅ Configured" if channel_id else "❌ Not configured"
                print(f"  {channel_type}: {status}")
            
            print(f"\n🎉 CHANNEL CONFIGURATION COMPLETE")
            print(f"Events will now be delivered to configured Discord channels")
        else:
            print(f"❌ Configuration verification failed")
        
        mongo_client.close()
        
    except Exception as e:
        logger.error(f"Failed to configure channels: {e}")

if __name__ == "__main__":
    asyncio.run(configure_channels())