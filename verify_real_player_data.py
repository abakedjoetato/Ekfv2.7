"""
Verify Real Player Data - Check if the bot is tracking actual players from the server
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def verify_player_data():
    """Check current player sessions and server status"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        # Check current player sessions
        sessions = await db.player_sessions.find({'active': True}).to_list(None)
        
        print(f"Current active player sessions: {len(sessions)}")
        
        if sessions:
            print("\nActive players:")
            for session in sessions:
                print(f"  - {session.get('player_name')} (ID: {session.get('player_id')})")
                print(f"    Server: {session.get('server_id')}")
                print(f"    Session start: {session.get('session_start')}")
                print(f"    Last seen: {session.get('last_seen')}")
        else:
            print("No active player sessions found")
        
        # Check recent parser states
        parser_states = await db.parser_states.find().sort('last_run', -1).limit(5).to_list(None)
        
        print(f"\nRecent parser runs: {len(parser_states)}")
        for state in parser_states:
            print(f"  - Server {state.get('server_id')}: {state.get('last_run')}")
            print(f"    Last position: {state.get('last_position', 0)} bytes")
        
        # Check total player sessions (including inactive)
        total_sessions = await db.player_sessions.count_documents({})
        print(f"\nTotal player sessions in database: {total_sessions}")
        
        client.close()
        
    except Exception as e:
        print(f"Failed to verify player data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_player_data())