"""
Test Cold/Hot Start System - Verify real server connection and player state tracking
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager
from bot.parsers.scalable_unified_parser import ScalableUnifiedParser

async def test_cold_hot_start():
    """Test the cold/hot start system with real server connection"""
    try:
        print("Initializing database connection...")
        mongo_uri = os.getenv('MONGO_URI')
        mongo_client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(mongo_client)
        await db_manager.initialize()
        
        print("Creating unified parser...")
        parser = ScalableUnifiedParser(None, db_manager)
        
        print("Testing cold/hot start system...")
        
        # Force a cold start by clearing parser state
        await db_manager.parser_states.delete_many({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        })
        
        print("✅ Parser state cleared - forcing COLD START")
        
        # Run the parser
        print("🔍 Running unified parser with real server connection...")
        await parser.run_log_parser()
        
        # Check parser state after run
        parser_state = await db_manager.parser_states.find_one({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        })
        
        if parser_state:
            print(f"✅ Parser state created: {parser_state.get('last_processed_line', 0)} lines processed")
            print(f"   Last update: {parser_state.get('last_updated')}")
        else:
            print("❌ No parser state found after run")
            
        # Check player sessions
        sessions = await db_manager.player_sessions.find({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        }).to_list(length=10)
        
        print(f"📊 Found {len(sessions)} player sessions:")
        for session in sessions[:5]:  # Show first 5
            print(f"   Player: {session.get('eos_id', 'Unknown')}")
            print(f"   State: {session.get('current_state', 'Unknown')}")
            print(f"   Last seen: {session.get('last_seen')}")
            
        # Test hot start by running again
        print("\n🔥 Testing HOT START - running parser again...")
        await parser.run_log_parser()
        
        # Check updated parser state
        updated_state = await db_manager.parser_states.find_one({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        })
        
        if updated_state:
            print(f"✅ Hot start completed: {updated_state.get('last_processed_line', 0)} lines processed")
        
        print("\n🎉 Cold/hot start system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing cold/hot start system: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cold_hot_start())