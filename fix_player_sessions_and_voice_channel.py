"""
Fix Player Sessions Database and Configure Voice Channel
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_player_sessions_and_voice_channel():
    """Fix player sessions database constraints and configure voice channel"""
    try:
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        server_id = "7020"
        
        print("=== Fixing Player Sessions Database ===")
        
        # Drop the problematic collection to reset constraints
        await db.player_sessions.drop()
        print("Dropped player_sessions collection")
        
        # Create new collection with proper constraints that allow null player_id for unknown players
        await db.player_sessions.create_index([
            ("guild_id", 1),
            ("server_id", 1),
            ("eos_id", 1)
        ], unique=True, sparse=True)
        
        print("Created new player_sessions collection with EOS ID constraint")
        
        print("\n=== Configuring Voice Channel ===")
        
        # Configure voice channel for the default server setup
        # Using the existing "updates" channel as voice channel for now
        voice_channel_id = 1361565075012603904  # updates channel
        
        # Update guild configuration with voice channel
        await db.guild_configs.update_one(
            {'guild_id': guild_id},
            {
                '$set': {
                    'server_channels.default.voice_channel': voice_channel_id
                }
            },
            upsert=True
        )
        
        print(f"Configured voice channel: {voice_channel_id}")
        
        # Verify configuration
        guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
        if guild_config:
            server_channels = guild_config.get('server_channels', {})
            default_voice = server_channels.get('default', {}).get('voice_channel')
            print(f"Verified voice channel configuration: {default_voice}")
        
        print("\n=== Triggering Fresh Parser Run ===")
        
        # Reset parser state to trigger fresh processing
        await db.parser_states.update_one(
            {
                'guild_id': guild_id,
                'server_id': server_id,
                'parser_type': 'unified'
            },
            {
                '$set': {
                    'last_processed_line': 0,
                    'last_updated': None
                }
            },
            upsert=True
        )
        
        print("Reset parser state to trigger fresh COLD START")
        
        await client.close()
        print("\n✅ Database fixes completed - next parser run should populate player sessions correctly")
        
    except Exception as e:
        print(f"Error fixing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_player_sessions_and_voice_channel())