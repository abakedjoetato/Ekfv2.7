#!/usr/bin/env python3
"""
Comprehensive /online Command Failure Diagnosis
Identifies all possible failure points in the /online command system
"""
import asyncio
import os
import motor.motor_asyncio
from datetime import datetime, timezone

async def diagnose_online_command():
    """Comprehensive diagnosis of /online command failure"""
    mongo_uri = os.environ.get('MONGO_URI')
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client.EmeraldDB
    
    guild_id = 1219706687980568769
    
    print("=== /ONLINE COMMAND FAILURE DIAGNOSIS ===")
    
    # 1. Check command registration status
    print("\n1. COMMAND REGISTRATION STATUS:")
    command_files = ["command_hash.txt", "command_sync_cooldown.txt", "global_sync_success.txt"]
    for file in command_files:
        exists = os.path.exists(file)
        print(f"  {file}: {'EXISTS' if exists else 'MISSING'}")
    
    # 2. Check player sessions database structure
    print("\n2. PLAYER SESSIONS DATABASE ANALYSIS:")
    
    # Check total sessions
    total_sessions = await db.player_sessions.count_documents({'guild_id': guild_id})
    print(f"  Total player sessions: {total_sessions}")
    
    # Check by state
    for state in ['online', 'offline', 'queued']:
        count = await db.player_sessions.count_documents({'guild_id': guild_id, 'state': state})
        print(f"  {state.capitalize()} sessions: {count}")
    
    # Check database field variations
    print("\n3. DATABASE FIELD STRUCTURE ANALYSIS:")
    sample_sessions = await db.player_sessions.find({'guild_id': guild_id}).limit(5).to_list(length=5)
    
    if sample_sessions:
        print("  Sample session fields:")
        for i, session in enumerate(sample_sessions, 1):
            print(f"    Session {i} fields: {list(session.keys())}")
            # Check for 'status' vs 'state' field
            if 'status' in session:
                print(f"      Uses 'status' field: {session['status']}")
            if 'state' in session:
                print(f"      Uses 'state' field: {session['state']}")
    else:
        print("  No sessions found for analysis")
    
    # 4. Check query compatibility issues
    print("\n4. QUERY COMPATIBILITY TEST:")
    
    # Test different query patterns that /online command uses
    test_queries = [
        {'guild_id': guild_id, 'status': 'online'},
        {'guild_id': guild_id, 'state': 'online'},
        {'guild_id': guild_id, 'server_name': 'Emerald EU', 'status': 'online'},
        {'guild_id': guild_id, 'server_name': 'Emerald EU', 'state': 'online'}
    ]
    
    for i, query in enumerate(test_queries, 1):
        count = await db.player_sessions.count_documents(query)
        print(f"  Query {i} {query}: {count} results")
    
    # 5. Check server configuration
    print("\n5. SERVER CONFIGURATION:")
    guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
    if guild_config:
        servers = guild_config.get('servers', [])
        print(f"  Configured servers: {len(servers)}")
        for server in servers:
            if isinstance(server, dict):
                server_name = server.get('name', 'Unknown')
                server_id = server.get('_id', server.get('id', 'Unknown'))
                print(f"    {server_name} (ID: {server_id})")
    else:
        print("  No guild configuration found")
    
    # 6. Check voice channel data source
    print("\n6. VOICE CHANNEL DATA SOURCE:")
    if guild_config:
        vc_id = guild_config.get('server_channels', {}).get('default', {}).get('playercountvc')
        print(f"  Voice channel ID configured: {vc_id}")
    
    # 7. Check recent parser activity
    print("\n7. RECENT PARSER ACTIVITY:")
    parser_states = await db.parser_states.find({'guild_id': guild_id}).to_list(length=10)
    for state in parser_states:
        parser_type = state.get('parser_type', 'unknown')
        server_name = state.get('server_name', 'unknown')
        last_updated = state.get('last_updated', 'unknown')
        print(f"  {parser_type}: {server_name} - {last_updated}")
    
    # 8. Database field mapping analysis
    print("\n8. FIELD MAPPING ANALYSIS:")
    if sample_sessions:
        session = sample_sessions[0]
        expected_fields = ['player_name', 'character_name', 'joined_at', 'platform', 'player_id', 'steam_id']
        print("  Field availability:")
        for field in expected_fields:
            has_field = field in session
            print(f"    {field}: {'PRESENT' if has_field else 'MISSING'}")
    
    # 9. Test actual online command queries
    print("\n9. ACTUAL ONLINE COMMAND QUERY TEST:")
    server_name = "Emerald EU"
    
    # Replicate exact queries from /online command
    queries_from_code = [
        {
            'guild_id': guild_id,
            'server_name': server_name,
            'status': 'online'
        },
        {
            'guild_id': guild_id,
            'server_id': server_name,  # Note: this might be wrong - server_id vs server_name
            'status': 'online'
        }
    ]
    
    for i, query in enumerate(queries_from_code, 1):
        try:
            cursor = db.player_sessions.find(query)
            results = await cursor.to_list(length=None)
            print(f"  Online command query {i}: {len(results)} results")
            if results:
                for result in results[:3]:
                    player_name = result.get('player_name', result.get('character_name', 'Unknown'))
                    print(f"    Player: {player_name}")
        except Exception as e:
            print(f"  Online command query {i}: FAILED - {e}")
    
    client.close()
    
    print("\n=== DIAGNOSIS SUMMARY ===")
    print("Key issues to investigate:")
    print("1. Field name mismatch: 'status' vs 'state'")
    print("2. Server identification: server_name vs server_id")
    print("3. Player name fields: player_name vs character_name")
    print("4. Command registration status")
    print("5. Database session persistence after cold start")

if __name__ == "__main__":
    asyncio.run(diagnose_online_command())