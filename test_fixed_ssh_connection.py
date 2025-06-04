"""
Test Fixed SSH Connection - Verify the cold/hot start system with correct credentials
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager
from bot.parsers.scalable_unified_parser import ScalableUnifiedParser

async def test_fixed_ssh():
    """Test the cold/hot start system with fixed SSH credentials"""
    try:
        print("Initializing database connection...")
        mongo_uri = os.getenv('MONGO_URI')
        mongo_client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(mongo_client)
        await db_manager.initialize()
        
        print("Creating unified parser...")
        parser = ScalableUnifiedParser(None, db_manager)
        
        print("Testing SSH connection with correct credentials...")
        
        # Clear parser state to force cold start
        await db_manager.parser_states.delete_many({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        })
        
        print("Forced COLD START - cleared parser state")
        
        # Run the parser with corrected SSH credentials
        print("Running unified parser with fixed SSH connection...")
        await parser.run_log_parser()
        
        # Check results
        parser_state = await db_manager.parser_states.find_one({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        })
        
        if parser_state:
            print(f"SUCCESS: Parser state created")
            print(f"  Last processed line: {parser_state.get('last_processed_line', 0)}")
            print(f"  Last update: {parser_state.get('last_updated')}")
        else:
            print("FAILED: No parser state found after run")
            
        # Check player sessions
        sessions = await db_manager.player_sessions.find({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        }).to_list(length=5)
        
        print(f"Player sessions found: {len(sessions)}")
        for session in sessions:
            print(f"  EOS ID: {session.get('eos_id', 'Unknown')}")
            print(f"  State: {session.get('current_state', 'Unknown')}")
            print(f"  Player: {session.get('player_name', 'Unknown')}")
            
        print("Cold/hot start system test completed!")
        
    except Exception as e:
        print(f"Error testing SSH connection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_ssh())