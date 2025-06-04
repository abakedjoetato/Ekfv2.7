"""
Check Server Max Players Configuration - Find where max player count should come from
"""

import asyncio
from bot.models.database import DatabaseManager

async def check_server_max_players():
    """Check what max player data is actually stored in server configuration"""
    
    db_manager = DatabaseManager()
    await db_manager.connect()
    
    print("=== Checking Server Max Players Configuration ===")
    
    # Check guild configuration
    guild_config = await db_manager.guild_configs.find_one({'guild_id': 1219706687980568769})
    if guild_config:
        print(f"Found guild config with {len(guild_config.get('servers', []))} servers")
        
        servers = guild_config.get('servers', [])
        for i, server in enumerate(servers):
            print(f"\nServer {i+1}:")
            print(f"  Server ID: {server.get('server_id')}")
            print(f"  Server Name: {server.get('server_name') or server.get('name')}")
            print(f"  Max Players: {server.get('max_players')}")
            print(f"  Player Limit: {server.get('player_limit')}")
            print(f"  All fields: {list(server.keys())}")
            
            # Show all server data
            for key, value in server.items():
                if 'player' in key.lower() or 'max' in key.lower() or 'limit' in key.lower():
                    print(f"  {key}: {value}")
    else:
        print("No guild configuration found")
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_server_max_players())