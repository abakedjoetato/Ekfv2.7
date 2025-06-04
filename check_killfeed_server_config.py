"""
Check Killfeed Server Configuration - Find the working SSH credentials
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_killfeed_server_config():
    """Check the killfeed server configuration that's actually working"""
    try:
        # Initialize database connection
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        print("Checking guild configurations for working SSH setup...")
        
        # Check guild_configs collection
        guild_configs = await db.guild_configs.find({}).to_list(length=None)
        print(f"Found {len(guild_configs)} guild configurations")
        
        for config in guild_configs:
            print(f"\nGuild Config: {config.get('guild_id')}")
            
            # Check if it has servers with SSH credentials
            servers = config.get('servers', [])
            print(f"  Servers: {len(servers)}")
            
            for server in servers:
                print(f"\n  Server: {server.get('server_name', 'Unknown')}")
                print(f"    Server ID: {server.get('server_id')}")
                print(f"    SSH Host: {server.get('ssh_host', 'NOT SET')}")
                print(f"    SSH Username: {server.get('ssh_username', 'NOT SET')}")
                print(f"    SSH Port: {server.get('ssh_port', 'NOT SET')}")
                print(f"    SSH Password: {'SET' if server.get('ssh_password') else 'NOT SET'}")
                print(f"    Log Path: {server.get('log_path', 'NOT SET')}")
                print(f"    Killfeed Path: {server.get('killfeed_path', 'NOT SET')}")
                
        # Also check killfeed_configs collection
        killfeed_configs = await db.killfeed_configs.find({}).to_list(length=None)
        print(f"\nFound {len(killfeed_configs)} killfeed configurations")
        
        for config in killfeed_configs:
            print(f"\nKillfeed Config: {config.get('guild_id')}")
            servers = config.get('servers', [])
            
            for server in servers:
                print(f"\n  Killfeed Server: {server.get('server_name', 'Unknown')}")
                print(f"    Server ID: {server.get('server_id')}")
                print(f"    SSH Host: {server.get('ssh_host', 'NOT SET')}")
                print(f"    SSH Username: {server.get('ssh_username', 'NOT SET')}")
                print(f"    SSH Port: {server.get('ssh_port', 'NOT SET')}")
                print(f"    SSH Password: {'SET' if server.get('ssh_password') else 'NOT SET'}")
                print(f"    Killfeed Path: {server.get('killfeed_path', 'NOT SET')}")
                
    except Exception as e:
        print(f"Error checking killfeed server config: {e}")

if __name__ == "__main__":
    asyncio.run(check_killfeed_server_config())