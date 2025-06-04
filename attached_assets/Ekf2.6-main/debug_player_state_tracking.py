"""
Debug Player State Tracking - Find why player count shows 0 when players are online
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_player_state():
    """Debug current player state tracking"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(os.environ['MONGO_URI'])
        db = client.emerald_killfeed
        
        print("=== PLAYER STATE DEBUGGING ===")
        
        # Check current player sessions
        sessions = await db.player_sessions.find({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        }).to_list(None)
        
        print(f"\n📊 Total player sessions found: {len(sessions)}")
        
        if sessions:
            print("\n🔍 Player sessions breakdown:")
            state_counts = {}
            for session in sessions:
                state = session.get('state', 'unknown')
                state_counts[state] = state_counts.get(state, 0) + 1
                
                print(f"  Player: {session.get('player_name', 'Unknown')[:20]}")
                print(f"    State: {state}")
                print(f"    EOS ID: {session.get('eos_id', 'None')[:20]}...")
                print(f"    Last Updated: {session.get('last_updated', 'None')}")
                print()
            
            print("📈 State Summary:")
            for state, count in state_counts.items():
                print(f"  {state}: {count} players")
        
        # Check voice channel configuration
        print("\n🔊 Voice Channel Configuration:")
        guild_config = await db.guild_configurations.find_one({
            'guild_id': 1219706687980568769
        })
        
        if guild_config and 'servers' in guild_config:
            for server in guild_config['servers']:
                if server.get('server_id') == '7020':
                    channels = server.get('channels', {})
                    voice_channel = channels.get('playercountvc')
                    print(f"  Voice Channel ID: {voice_channel}")
                    print(f"  Server Name: {server.get('server_name', 'Unknown')}")
                    break
        
        # Check recent parser states
        print("\n📝 Recent Parser States:")
        parser_states = await db.parser_states.find({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        }).to_list(None)
        
        for state in parser_states:
            print(f"  Parser Type: {state.get('parser_type')}")
            print(f"  Last Timestamp: {state.get('last_timestamp')}")
            print(f"  Last Updated: {state.get('last_updated')}")
            print()
        
        # Check live server data by looking at recent log events
        print("\n🔍 Recent Connection Events (last 10):")
        recent_events = await db.player_sessions.find({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        }).sort('last_updated', -1).limit(10).to_list(None)
        
        for event in recent_events:
            print(f"  {event.get('player_name', 'Unknown')}: {event.get('state')} - {event.get('last_updated')}")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Error debugging player state: {e}")

if __name__ == "__main__":
    asyncio.run(debug_player_state())