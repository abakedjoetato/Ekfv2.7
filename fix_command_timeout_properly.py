"""
Fix Command Timeout Properly - Allow Discord API for bot functionality but prevent command sync
"""
import asyncio
import os
import time
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_command_timeout_properly():
    """Fix command timeout by targeting only command sync operations"""
    print("Fixing command timeout issues properly...")
    
    # Remove the overly aggressive cooldowns that block ALL Discord API
    cooldown_files = [
        "channel_message_cooldown.txt"  # This blocks normal message sending
    ]
    
    for cooldown_file in cooldown_files:
        if os.path.exists(cooldown_file):
            os.remove(cooldown_file)
            print(f"Removed excessive cooldown: {cooldown_file}")
    
    # Keep only command sync cooldowns (these are the problem)
    command_sync_files = [
        "command_sync_cooldown.txt",
        "global_sync_cooldown.txt"
    ]
    
    future_time = time.time() + 86400  # 24 hours
    
    for cooldown_file in command_sync_files:
        with open(cooldown_file, 'w') as f:
            f.write(str(future_time))
        print(f"Maintained command sync cooldown: {cooldown_file}")
    
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
    
    client.close()
    print("Command timeout fix completed properly")
    
    return True

if __name__ == "__main__":
    asyncio.run(fix_command_timeout_properly())