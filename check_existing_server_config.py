"""
Check Existing Server Configuration - Find how servers are actually stored
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_existing_server_config():
    """Check how servers are actually configured in the database"""
    try:
        # Initialize database connection
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        print("Checking guild_configs collection for server structures...")
        
        # Get the current guild configuration
        guild_config = await db.guild_configs.find_one({'guild_id': 1219706687980568769})
        
        if guild_config:
            print(f"Guild ID: {guild_config.get('guild_id')}")
            
            # Check all possible server storage locations
            if 'servers' in guild_config:
                print(f"\nServers array ({len(guild_config['servers'])} servers):")
                for i, server in enumerate(guild_config['servers']):
                    print(f"  Server {i+1}:")
                    for key, value in server.items():
                        if 'password' in key.lower():
                            print(f"    {key}: {'*' * len(str(value)) if value else 'None'}")
                        else:
                            print(f"    {key}: {value}")
                    print("")
            
            # Check other possible server configurations
            other_server_fields = ['server_configs', 'game_servers', 'deadside_servers']
            for field in other_server_fields:
                if field in guild_config:
                    print(f"\n{field}: {guild_config[field]}")
            
            # Check server_channels structure
            if 'server_channels' in guild_config:
                print(f"\nServer channels: {list(guild_config['server_channels'].keys())}")
                
        else:
            print("No guild configuration found")
            
        # Also check if there's a separate servers collection
        servers_collection = db.servers
        server_docs = await servers_collection.find({'guild_id': 1219706687980568769}).to_list(length=None)
        
        if server_docs:
            print(f"\nSeparate servers collection ({len(server_docs)} documents):")
            for server in server_docs:
                print(f"  Server: {server.get('server_name', 'Unknown')}")
                for key, value in server.items():
                    if 'password' in key.lower():
                        print(f"    {key}: {'*' * len(str(value)) if value else 'None'}")
                    else:
                        print(f"    {key}: {value}")
                print("")
        
    except Exception as e:
        print(f"Error checking server config: {e}")

if __name__ == "__main__":
    asyncio.run(check_existing_server_config())