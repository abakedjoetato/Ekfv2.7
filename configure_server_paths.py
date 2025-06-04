"""
Configure Server Paths - Add missing killfeed and log paths to server configuration
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def configure_server_paths():
    """Configure the missing paths for the Emerald EU server"""
    
    print("Configuring server paths...")
    
    try:
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        database = client.emerald_killfeed
        guild_configs = database.guild_configs
        
        # Find the guild configuration
        guild_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
        
        if guild_doc:
            servers = guild_doc.get('servers', [])
            updated = False
            
            for server in servers:
                server_name = server.get('server_name', '')
                
                if server_name == 'Emerald EU':
                    print(f"Configuring paths for {server_name}")
                    
                    # Add standard Deadside server paths
                    server['killfeed_path'] = '/opt/deadside/logs/DeathLogs'
                    server['log_path'] = '/opt/deadside/logs'
                    server['base_path'] = '/opt/deadside'
                    
                    # Add port if missing
                    if 'port' not in server:
                        server['port'] = 8822
                    
                    updated = True
                    print(f"  killfeed_path: {server['killfeed_path']}")
                    print(f"  log_path: {server['log_path']}")
                    print(f"  base_path: {server['base_path']}")
                    print(f"  port: {server['port']}")
            
            if updated:
                # Update the document
                result = await guild_configs.update_one(
                    {'guild_id': 1219706687980568769},
                    {'$set': {'servers': servers}}
                )
                
                if result.modified_count > 0:
                    print("Successfully updated server paths")
                    
                    # Verify the update
                    updated_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
                    updated_servers = updated_doc.get('servers', [])
                    
                    print("\nVerified server configuration:")
                    for server in updated_servers:
                        if server.get('server_name') == 'Emerald EU':
                            print(f"Server: {server.get('server_name')}")
                            print(f"  Host: {server.get('host')}:{server.get('port')}")
                            print(f"  Username: {server.get('username')}")
                            print(f"  Enabled: {server.get('enabled')}")
                            print(f"  Killfeed Path: {server.get('killfeed_path')}")
                            print(f"  Log Path: {server.get('log_path')}")
                            print(f"  Base Path: {server.get('base_path')}")
                else:
                    print("Failed to update server paths")
            else:
                print("No updates needed")
        else:
            print("No guild configuration found")
            
    except Exception as e:
        print(f"Failed to configure server paths: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(configure_server_paths())