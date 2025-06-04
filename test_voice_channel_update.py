"""
Test voice channel update functionality to verify player count calculation
"""
import asyncio
import sys
sys.path.append('.')

from bot.models.database import DatabaseManager
from bot.utils.voice_channel_batch import VoiceChannelBatcher
import discord

async def test_voice_channel_update():
    """Test voice channel update functionality"""
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        guild_id = 1219706687980568769
        server_name = "Emerald EU"
        
        # Check active player count
        player_count = await db_manager.get_active_player_count(guild_id, server_name)
        print(f"Active player count for {server_name}: {player_count}")
        
        # Get guild config to find voice channel
        guild_config = await db_manager.get_guild(guild_id)
        if guild_config:
            print(f"Guild config found for {guild_id}")
            
            # Check server channels config
            server_channels_config = guild_config.get('server_channels', {})
            print(f"Server channels config: {server_channels_config}")
            
            # Check legacy channels
            legacy_channels = guild_config.get('channels', {})
            print(f"Legacy channels: {legacy_channels}")
            
            # Find voice channel ID
            default_server = server_channels_config.get('default', {})
            vc_id = (default_server.get('playercountvc') or 
                    legacy_channels.get('playercountvc'))
            
            print(f"Voice channel ID found: {vc_id}")
            
            if vc_id:
                print(f"Would update voice channel {vc_id} with {player_count} players")
            else:
                print("No voice channel configured")
        
        # Check recent player sessions
        sessions = await db_manager.get_active_player_sessions(guild_id)
        print(f"Total active sessions: {len(sessions)}")
        
        # Check server-specific sessions
        server_sessions = [s for s in sessions if s.get('server_name') == server_name]
        print(f"Active sessions for {server_name}: {len(server_sessions)}")
        
        for session in server_sessions[:5]:  # Show first 5
            print(f"  - Player {session.get('player_id', 'unknown')}: {session.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"Error testing voice channel update: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_voice_channel_update())