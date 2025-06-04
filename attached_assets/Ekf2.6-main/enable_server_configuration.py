"""
Enable Server Configuration - Fix disabled server issue
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def enable_server_configuration():
    """Enable the configured server that's currently disabled"""
    
    print("Enabling disabled server configuration...")
    
    try:
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        database = client.emerald_killfeed
        guild_configs = database.guild_configs
        
        # Find the guild configuration
        guild_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
        
        if guild_doc:
            print(f"Found guild configuration with {len(guild_doc.get('servers', []))} servers")
            
            servers = guild_doc.get('servers', [])
            enabled_count = 0
            
            # Enable all disabled servers
            for server in servers:
                server_name = server.get('server_name', 'unnamed')
                current_enabled = server.get('enabled', False)
                
                print(f"Server: {server_name} - Currently enabled: {current_enabled}")
                
                if not current_enabled:
                    server['enabled'] = True
                    enabled_count += 1
                    print(f"Enabling server: {server_name}")
            
            if enabled_count > 0:
                # Update the document
                result = await guild_configs.update_one(
                    {'guild_id': 1219706687980568769},
                    {'$set': {'servers': servers}}
                )
                
                if result.modified_count > 0:
                    print(f"Successfully enabled {enabled_count} servers")
                    
                    # Verify the update
                    updated_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
                    updated_servers = updated_doc.get('servers', [])
                    
                    print("\nUpdated server status:")
                    for server in updated_servers:
                        server_name = server.get('server_name', 'unnamed')
                        enabled = server.get('enabled', False)
                        host = server.get('host', 'no-host')
                        print(f"- {server_name} ({host}): Enabled = {enabled}")
                        
                else:
                    print("Failed to update server configuration")
            else:
                print("All servers are already enabled")
                
        else:
            print("No guild configuration found")
            
        # Check if parsers should now find the enabled servers
        enabled_servers_query = {
            'servers': {
                '$exists': True,
                '$not': {'$size': 0},
                '$elemMatch': {'enabled': True}
            }
        }
        
        enabled_server_count = await guild_configs.count_documents(enabled_servers_query)
        print(f"\nGuilds with enabled servers: {enabled_server_count}")
        
        if enabled_server_count > 0:
            print("Parsers should now detect configured servers")
        else:
            print("Parsers may still not detect servers - checking filter logic")
            
    except Exception as e:
        print(f"Failed to enable server configuration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(enable_server_configuration())