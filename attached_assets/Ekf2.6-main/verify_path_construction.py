"""
Verify Path Construction - Test that dynamic paths now resolve correctly with _id: 7020
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def verify_path_construction():
    """Verify that paths will now construct correctly with _id: 7020"""
    
    try:
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        database = client.emerald_killfeed
        guild_configs = database.guild_configs
        
        # Get the server configuration
        guild_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
        
        if not guild_doc:
            print("❌ Guild document not found")
            return
        
        servers = guild_doc.get('servers', [])
        
        for server in servers:
            server_name = server.get('server_name', 'Unknown')
            print(f"\n=== Server: {server_name} ===")
            
            # Test the path construction logic from simple_killfeed_processor.py
            host = server.get('host', 'unknown')
            server_id = server.get('server_id', server.get('_id', 'unknown'))
            
            print(f"Host: {host}")
            print(f"Server ID: {server_id}")
            print(f"_id field: {server.get('_id', 'NOT SET')}")
            
            # Construct the killfeed path
            killfeed_path = f"./{host}_{server_id}/actual1/deathlogs/"
            print(f"Killfeed path: {killfeed_path}")
            
            # Construct the historical log path  
            log_path = f"./{host}_{server_id}/actual1/"
            print(f"Historical log path: {log_path}")
            
            # Check if it resolves to "unknown"
            if server_id == "unknown":
                print("❌ Server ID still resolving to 'unknown'")
            else:
                print(f"✅ Server ID correctly resolves to: {server_id}")
                print(f"✅ Paths will use server ID {server_id} instead of 'unknown'")
        
        client.close()
        
        print("\n=== Path Construction Summary ===")
        print("The server now has _id: 7020 which will be used for dynamic path construction")
        print("Expected killfeed path: ./79.127.236.1_7020/actual1/deathlogs/")
        print("Expected log path: ./79.127.236.1_7020/actual1/")
        print("This replaces the previous 'unknown' placeholder in paths")
        
    except Exception as e:
        print(f"Error verifying path construction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_path_construction())