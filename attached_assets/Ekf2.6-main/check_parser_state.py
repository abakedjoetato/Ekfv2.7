#!/usr/bin/env python3
"""
Check current parser state after recent runs
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def check_parser_state():
    """Check the current parser state"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI not found in environment")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.emerald_killfeed
    
    try:
        guild_id = 1219706687980568769
        
        print(f"🔍 Checking parser state for guild {guild_id}")
        
        # Check all parser states
        parser_states = []
        async for state in db.parser_states.find({"guild_id": guild_id}):
            parser_states.append(state)
        
        print(f"📊 Found {len(parser_states)} parser states")
        
        for state in parser_states:
            server_id = state.get('server_id')
            parser_type = state.get('parser_type')
            last_position = state.get('last_position', 0)
            last_byte_position = state.get('last_byte_position', 0)
            last_line = state.get('last_line', 0)
            last_run = state.get('last_run')
            file_name = state.get('file_name')
            file_timestamp = state.get('file_timestamp')
            
            print(f"\n📋 Parser State for Server {server_id}:")
            print(f"   Type: {parser_type}")
            print(f"   File: {file_name}")
            print(f"   Last position: {last_position}")
            print(f"   Last byte position: {last_byte_position}")
            print(f"   Last line: {last_line}")
            print(f"   Last run: {last_run}")
            print(f"   File timestamp/hash: {file_timestamp}")
        
        # Check recent data
        print(f"\n🔍 Checking recent database activity...")
        
        # Check kills
        kills_count = await db.kills.count_documents({"guild_id": guild_id})
        print(f"📊 Total kills: {kills_count}")
        
        # Check player sessions
        sessions_count = await db.player_sessions.count_documents({"guild_id": guild_id})
        print(f"📊 Total player sessions: {sessions_count}")
        
        # Check latest session update
        latest_session = await db.player_sessions.find_one(
            {"guild_id": guild_id},
            sort=[("last_seen", -1)]
        )
        if latest_session:
            print(f"🕒 Latest session update: {latest_session.get('last_seen')}")
        
        # Check server configuration
        guild_doc = await db.guilds.find_one({"guild_id": guild_id})
        if guild_doc:
            servers = guild_doc.get('servers', [])
            print(f"\n📋 Server Configuration:")
            for server in servers:
                server_id = server.get('_id') or server.get('server_id')
                name = server.get('name')
                enabled = server.get('enabled', False)
                log_path = server.get('log_path')
                print(f"   Server {server_id} ({name}): enabled={enabled}, log_path={log_path}")
        
    except Exception as e:
        print(f"❌ Error checking parser state: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_parser_state())