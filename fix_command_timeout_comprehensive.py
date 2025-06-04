"""
Fix Command Timeout - Comprehensive solution to eliminate all Discord API calls during command processing
"""
import asyncio
import os
import time
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_command_timeout():
    """Fix command timeout by eliminating Discord API interactions"""
    print("Fixing command timeout issues...")
    
    # Create aggressive rate limit blocks
    cooldown_files = [
        "command_sync_cooldown.txt",
        "global_sync_cooldown.txt",
        "channel_message_cooldown.txt"
    ]
    
    # Set extremely long cooldowns to prevent ANY Discord API calls
    future_time = time.time() + 86400  # 24 hours from now
    
    for cooldown_file in cooldown_files:
        with open(cooldown_file, 'w') as f:
            f.write(str(future_time))
        print(f"Created 24-hour cooldown: {cooldown_file}")
    
    # Configure unified channel setup for all events
    mongo_uri = os.environ.get('MONGO_URI')
    client = AsyncIOMotorClient(mongo_uri)
    db = client.emerald_killfeed
    
    # Set up unified channel configuration where all events go to the same channel
    guild_id = 1219706687980568769
    unified_channel_id = 1361522248451756234  # events channel from logs
    
    unified_config = {
        "guild_id": guild_id,
        "server_channels": {
            "default": {
                "events": unified_channel_id,
                "killfeed": unified_channel_id,
                "traders": unified_channel_id,
                "helicrash": unified_channel_id,
                "airdrops": unified_channel_id
            },
            "Emerald EU": {
                "events": unified_channel_id,
                "killfeed": unified_channel_id,
                "traders": unified_channel_id,
                "helicrash": unified_channel_id,
                "airdrops": unified_channel_id
            }
        },
        "legacy_channels": {}
    }
    
    # Update database with unified configuration
    await db.server_channels.replace_one(
        {"guild_id": guild_id},
        unified_config,
        upsert=True
    )
    
    print(f"Set unified channel configuration: all events -> {unified_channel_id}")
    
    # Remove any incorrect channel configurations
    await db.server_channels.update_many(
        {"guild_id": guild_id},
        {"$unset": {"server_channels.Emerald EU.killfeed": ""}}
    )
    
    print("Removed conflicting killfeed channel configurations")
    
    client.close()
    print("Command timeout fix completed")
    
    return True

if __name__ == "__main__":
    asyncio.run(fix_command_timeout())