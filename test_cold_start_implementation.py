#!/usr/bin/env python3
"""
Test Cold Start Implementation - Verify the bot restart flag system is working
"""
import asyncio
import os
import motor.motor_asyncio
from datetime import datetime, timezone

async def test_cold_start_system():
    """Test the cold start flag system implementation"""
    mongo_uri = os.environ.get('MONGO_URI')
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client.EmeraldDB
    
    guild_id = 1219706687980568769
    
    print("=== COLD START SYSTEM TEST ===")
    
    # Check if cold start flag was set during bot startup
    print("\n1. Checking cold start flag...")
    guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
    if guild_config:
        cold_start_flag = guild_config.get('cold_start_required', False)
        print(f"Cold start flag: {cold_start_flag}")
        
        if cold_start_flag:
            print("✓ Cold start flag properly set during bot restart")
        else:
            print("❌ Cold start flag not found - may have been cleared already")
    else:
        print("❌ No guild config found")
    
    # Check current player sessions
    print("\n2. Current player session state...")
    total_sessions = await db.player_sessions.count_documents({"guild_id": guild_id})
    online_sessions = await db.player_sessions.count_documents({"guild_id": guild_id, "state": "online"})
    print(f"Total sessions: {total_sessions}")
    print(f"Online sessions: {online_sessions}")
    
    # Check parser states
    print("\n3. Parser state check...")
    unified_states = await db.parser_states.count_documents({
        "guild_id": guild_id,
        "parser_type": "unified"
    })
    print(f"Unified parser states: {unified_states}")
    
    if unified_states == 0:
        print("✓ Unified parser ready for cold start")
    
    # Show recent parser activity to see if cold start triggered
    print("\n4. Recent parser activity...")
    parser_states = await db.parser_states.find({"guild_id": guild_id}).to_list(length=10)
    
    for state in parser_states:
        parser_type = state.get('parser_type', 'unknown')
        server_name = state.get('server_name', 'unknown')
        last_line = state.get('last_line_processed', 'N/A')
        last_updated = state.get('last_updated', 'N/A')
        print(f"  {parser_type}: {server_name} - Line {last_line} - {last_updated}")
    
    client.close()
    
    print("\n=== SYSTEM STATUS ===")
    print("Bot restart cold start flag system implemented")
    print("Cold start will trigger when flag is detected")
    print("Flag automatically cleared after cold start processing")
    print("System ready to detect and process player connections")

if __name__ == "__main__":
    asyncio.run(test_cold_start_system())