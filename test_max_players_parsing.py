"""
Test Max Players Parsing - Verify we can find playersmaxcount in actual logs
"""

import asyncio
import re
import os
from bot.utils.connection_pool import ConnectionPool

async def test_max_players_parsing():
    """Test parsing max players from actual Deadside.log"""
    
    print("=== Testing Max Players Parsing ===")
    
    # Use environment SSH credentials
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
        sftp = await connection_pool.get_connection(ssh_host, ssh_port, ssh_username, ssh_password)
        
        # Read Deadside.log file
        log_path = "./79.127.236.1_7020/Logs/Deadside.log"
        print(f"Reading log file: {log_path}")
        
        async with sftp.open(log_path, 'r') as f:
            content = await f.read()
            
        lines = content.split('\n')
        print(f"Log file has {len(lines)} lines")
        
        # Look for the LogInit command line
        found_command_line = False
        found_max_count = None
        
        for i, line in enumerate(lines):
            if 'LogInit: Command Line:' in line:
                print(f"Line {i}: Found LogInit command line")
                print(f"  Content: {line.strip()}")
                found_command_line = True
                
                # Look for playersmaxcount pattern
                if 'playersmaxcount=' in line:
                    match = re.search(r'-playersmaxcount=(\d+)', line)
                    if match:
                        found_max_count = int(match.group(1))
                        print(f"  ✅ Found max players: {found_max_count}")
                    else:
                        print(f"  ❌ playersmaxcount found but regex failed")
                        # Try alternative patterns
                        alt_match = re.search(r'playersmaxcount=(\d+)', line)
                        if alt_match:
                            found_max_count = int(alt_match.group(1))
                            print(f"  ✅ Found with alternative pattern: {found_max_count}")
                else:
                    print(f"  ❌ No playersmaxcount found in this command line")
        
        if not found_command_line:
            print("❌ No LogInit command line found")
            print("Checking recent lines for any server startup info...")
            for i, line in enumerate(lines[-20:], len(lines)-20):
                if any(keyword in line.lower() for keyword in ['command', 'server', 'init', 'start']):
                    print(f"Line {i}: {line.strip()}")
        
        if found_max_count:
            print(f"\n✅ SUCCESS: Max player count is {found_max_count}")
        else:
            print(f"\n❌ FAILED: Could not find max player count")
            print("Checking if we need to look at different log sections...")
        
        await connection_pool.close_all()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_max_players_parsing())