"""
Find Max Players in Deadside Logs - Parse actual max player count from server logs
"""

import asyncio
import re
import os
from bot.utils.connection_pool import ConnectionPool

async def find_max_players_in_logs():
    """Find max player count from actual Deadside.log file"""
    
    print("=== Finding Max Players from Deadside Logs ===")
    
    # SSH connection details from environment
    ssh_host = os.getenv('SSH_HOST')
    ssh_port = int(os.getenv('SSH_PORT', 8822))
    ssh_username = os.getenv('SSH_USERNAME')
    ssh_password = os.getenv('SSH_PASSWORD')
    
    if not all([ssh_host, ssh_username, ssh_password]):
        print("Missing SSH credentials")
        return
    
    try:
        # Connect to server
        connection_pool = ConnectionPool()
        sftp = await connection_pool.get_connection(
            ssh_host, ssh_port, ssh_username, ssh_password
        )
        
        # Read Deadside.log file
        log_path = "./79.127.236.1_7020/Logs/Deadside.log"
        print(f"Reading log file: {log_path}")
        
        async with sftp.open(log_path, 'r') as f:
            log_content = await f.read()
            
        # Look for server configuration lines that mention max players
        lines = log_content.split('\n')
        
        # Common patterns in Deadside logs for max players
        max_player_patterns = [
            r'MaxPlayers[:\s=]+(\d+)',
            r'max_players[:\s=]+(\d+)',
            r'MaxPlayerCount[:\s=]+(\d+)',
            r'Server.*[Mm]ax.*?(\d+).*players',
            r'Player.*[Ll]imit.*?(\d+)',
            r'(\d+).*player.*[Ll]imit',
            r'Server.*[Cc]apacity.*?(\d+)',
        ]
        
        found_values = []
        
        print(f"Scanning {len(lines)} log lines for max player configuration...")
        
        for i, line in enumerate(lines):
            for pattern in max_player_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    for match in matches:
                        value = int(match)
                        if 10 <= value <= 200:  # Reasonable range for game servers
                            found_values.append((i, line.strip(), value))
                            print(f"Line {i}: Found max players {value}")
                            print(f"  Content: {line.strip()}")
        
        # Look for server startup messages
        startup_patterns = [
            r'Server.*[Ss]tarted.*(\d+)',
            r'[Ss]erver.*[Ii]nitialized.*(\d+)',
            r'Game.*[Ss]erver.*(\d+)',
        ]
        
        print("\nLooking for server startup messages...")
        for i, line in enumerate(lines[-100:], len(lines)-100):  # Check last 100 lines
            for pattern in startup_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    print(f"Line {i}: {line.strip()}")
        
        # Summary
        if found_values:
            unique_values = list(set(v[2] for v in found_values))
            print(f"\nFound potential max player values: {unique_values}")
            
            if len(unique_values) == 1:
                print(f"Consistent max player count: {unique_values[0]}")
            else:
                print("Multiple values found - need to determine which is correct")
        else:
            print("No max player configuration found in logs")
            print("Checking if we need to look at server config files instead...")
        
        await connection_pool.close_all()
        
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    asyncio.run(find_max_players_in_logs())