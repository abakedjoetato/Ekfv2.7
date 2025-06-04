"""
Check User Configured Channels - Show only channels configured via /setchannel commands
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_user_configured_channels():
    """Check what channels the user actually configured via /setchannel commands"""
    try:
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        print("=== User Configured Channels (via /setchannel) ===")
        
        # Get guild configuration
        guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
        
        if guild_config and 'server_channels' in guild_config:
            server_channels = guild_config['server_channels']
            
            for server_name, channels in server_channels.items():
                print(f"\nServer: {server_name}")
                for channel_type, channel_id in channels.items():
                    if channel_id:
                        print(f"  {channel_type}: {channel_id}")
                    else:
                        print(f"  {channel_type}: Not configured")
        else:
            print("No channels configured via /setchannel commands")
            
        # Remove the automatically configured voice channel
        if guild_config and 'server_channels' in guild_config:
            default_channels = guild_config['server_channels'].get('default', {})
            if 'voice_channel' in default_channels:
                print(f"\nRemoving auto-configured voice channel...")
                await db.guild_configs.update_one(
                    {'guild_id': guild_id},
                    {'$unset': {'server_channels.default.voice_channel': 1}}
                )
                print("Auto-configured voice channel removed")
                
        await client.close()
        print("\nUse /setchannel voice_channel <channel> to configure voice channel properly")
        
    except Exception as e:
        print(f"Error checking channels: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_configured_channels())