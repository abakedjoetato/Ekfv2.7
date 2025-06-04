"""
Check Server Credentials - Verify database contains proper SSH credentials
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_server_credentials():
    """Check if server configurations contain proper SSH credentials"""
    
    print("Checking server credentials in database...")
    
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
            print(f"Found {len(servers)} servers configured")
            
            for i, server in enumerate(servers):
                server_name = server.get('server_name', 'unnamed')
                host = server.get('host', 'no-host')
                port = server.get('port', 22)
                username = server.get('username', 'no-username')
                enabled = server.get('enabled', False)
                
                print(f"\nServer {i+1}: {server_name}")
                print(f"  Host: {host}:{port}")
                print(f"  Username: {username}")
                print(f"  Enabled: {enabled}")
                
                # Check for password field
                if 'password' in server:
                    password_len = len(server.get('password', ''))
                    print(f"  Password: {'*' * password_len} ({password_len} chars)")
                else:
                    print("  Password: NOT SET")
                
                # Check for other credential fields
                credential_fields = ['ssh_key', 'private_key', 'key_file']
                for field in credential_fields:
                    if field in server:
                        print(f"  {field}: PRESENT")
                
                # Check for path configurations
                path_fields = ['killfeed_path', 'log_path', 'base_path']
                for field in path_fields:
                    if field in server:
                        print(f"  {field}: {server.get(field)}")
                    else:
                        print(f"  {field}: NOT SET")
        else:
            print("No guild configuration found")
            
    except Exception as e:
        print(f"Failed to check server credentials: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_server_credentials())