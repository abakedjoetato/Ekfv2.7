#!/usr/bin/env python3
"""
Debug Player Count - Check actual database state to fix voice channel accuracy
"""
import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_player_count():
    """Debug actual player count in database"""
    try:
        # Connect to MongoDB
        mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = mongo_client.emerald_killfeed
        
        guild_id = 1219706687980568769
        server_name = "Emerald EU"
        
        # Get all player sessions for this guild and server
        sessions = await db.player_sessions.find({
            "guild_id": guild_id,
            "server_name": server_name
        }).to_list(length=None)
        
        print(f"=== Player Sessions for {server_name} (Guild: {guild_id}) ===")
        print(f"Total sessions found: {len(sessions)}")
        
        state_counts = {}
        for session in sessions:
            state = session.get('state', 'unknown')
            state_counts[state] = state_counts.get(state, 0) + 1
            
            print(f"Player ID: {session.get('player_id', 'unknown')[:16]}...")
            print(f"  State: {state}")
            print(f"  Last Updated: {session.get('last_updated', 'unknown')}")
            print(f"  Player Name: {session.get('player_name', 'unknown')}")
            print("---")
        
        print(f"\n=== State Summary ===")
        for state, count in state_counts.items():
            print(f"{state}: {count} players")
        
        # Test the actual count query
        online_count = await db.player_sessions.count_documents({
            "guild_id": guild_id,
            "server_name": server_name,
            "state": "online"
        })
        
        print(f"\n=== Database Query Results ===")
        print(f"Online players (database query): {online_count}")
        
        # Check for any stale sessions
        recent_sessions = await db.player_sessions.find({
            "guild_id": guild_id,
            "server_name": server_name,
            "last_updated": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
        }).to_list(length=None)
        
        print(f"Sessions updated today: {len(recent_sessions)}")
        
        mongo_client.close()
        
    except Exception as e:
        logger.error(f"Failed to debug player count: {e}")

if __name__ == "__main__":
    asyncio.run(debug_player_count())