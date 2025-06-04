"""
Test Regex Patterns Against Real Log Data
"""

import asyncio
import asyncssh
import os
import re
from datetime import datetime

async def test_regex_patterns():
    """Test the updated regex patterns against real log data"""
    try:
        host = "79.127.236.1"
        port = 8822
        username = os.getenv('SSH_USERNAME')
        password = os.getenv('SSH_PASSWORD')
        
        if not username or not password:
            print("Missing SSH credentials - SSH_USERNAME or SSH_PASSWORD not set")
            return
        
        print(f"Testing regex patterns against real log data from {host}:{port}...")
        
        async with asyncssh.connect(
            host, 
            port=port,
            username=username, 
            password=password,
            known_hosts=None,
            kex_algs=['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521'],
            encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', 'aes192-cbc', 'aes256-cbc'],
            mac_algs=['hmac-sha1', 'hmac-sha2-256', 'hmac-sha2-512'],
            compression_algs=['none'],
            server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss']
        ) as conn:
            async with conn.start_sftp_client() as sftp:
                log_path = "./79.127.236.1_7020/Logs/Deadside.log"
                
                try:
                    # Get recent log data
                    file_stat = await sftp.stat(log_path)
                    file_size = file_stat.size
                    
                    # Read the last 20KB to get more data for testing
                    start_pos = max(0, file_size - 20480)
                    
                    async with sftp.open(log_path, 'rb') as f:
                        await f.seek(start_pos)
                        recent_data = await f.read()
                        
                    log_content = recent_data.decode('utf-8', errors='ignore')
                    lines = [line.strip() for line in log_content.split('\n') if line.strip()]
                    
                    print(f"\nTesting patterns against {len(lines)} log lines")
                    print("-" * 80)
                    
                    # Test patterns from the bot
                    connection_patterns = {
                        'player_queue': re.compile(r'LogNet: Join request: /Game/Maps/world_[^?]*\?.*?login=([^?]+).*?eosid=\|([a-f0-9]+).*?Name=([^?]+)', re.IGNORECASE),
                        'player_connect': re.compile(r'LogOnline: Warning: Player \|([a-f0-9]+) successfully registered!', re.IGNORECASE),
                        'player_disconnect': re.compile(r'LogNet: UChannel::Close:.*UniqueId: EOS:\|([a-f0-9]+)', re.IGNORECASE)
                    }
                    
                    event_patterns = {
                        'mission_start': re.compile(r'LogSFPS: Mission (\w+) switched to READY', re.IGNORECASE),
                        'mission_end': re.compile(r'LogSFPS: Mission (\w+) switched to WAITING', re.IGNORECASE),
                        'airdrop': re.compile(r'LogSFPS: AirDrop switched to Dropping', re.IGNORECASE),
                        'patrol_active': re.compile(r'LogSFPS: PatrolPoint (\w+) switched to ACTIVE', re.IGNORECASE),
                        'patrol_initial': re.compile(r'LogSFPS: PatrolPoint (\w+) switched to INITIAL', re.IGNORECASE),
                        'vehicle_deleted': re.compile(r'LogSFPS: .*Del vehicle.*Total (\d+)', re.IGNORECASE)
                    }
                    
                    # Test connection patterns
                    print("Testing Connection Patterns:")
                    connection_matches = 0
                    
                    for line in lines:
                        for pattern_name, pattern in connection_patterns.items():
                            match = pattern.search(line)
                            if match:
                                connection_matches += 1
                                print(f"  {pattern_name}: {line}")
                                print(f"    Groups: {match.groups()}")
                                print()
                    
                    print(f"Total connection matches: {connection_matches}\n")
                    
                    # Test event patterns
                    print("Testing Event Patterns:")
                    event_matches = 0
                    
                    for line in lines:
                        for pattern_name, pattern in event_patterns.items():
                            match = pattern.search(line)
                            if match:
                                event_matches += 1
                                print(f"  {pattern_name}: {line}")
                                if match.groups():
                                    print(f"    Groups: {match.groups()}")
                                print()
                    
                    print(f"Total event matches: {event_matches}\n")
                    
                    # Parse timestamp pattern
                    print("Testing Timestamp Parsing:")
                    timestamp_pattern = re.compile(r'^\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]')
                    timestamp_matches = 0
                    
                    for line in lines[:10]:  # Test first 10 lines
                        match = timestamp_pattern.search(line)
                        if match:
                            timestamp_matches += 1
                            timestamp_str = match.group(1)
                            try:
                                timestamp = datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S:%f')
                                print(f"  Parsed: {timestamp_str} -> {timestamp}")
                            except ValueError as e:
                                print(f"  Failed: {timestamp_str} -> {e}")
                    
                    print(f"Timestamp parsing success: {timestamp_matches}/10\n")
                    
                    # Look for potential player activity
                    print("Scanning for potential player patterns:")
                    player_keywords = ['Join request', 'successfully registered', 'UChannel::Close', 'UniqueId: EOS']
                    
                    for keyword in player_keywords:
                        count = 0
                        for line in lines:
                            if keyword.lower() in line.lower():
                                count += 1
                                if count <= 3:  # Show first 3 examples
                                    print(f"  {keyword}: {line}")
                        print(f"  Total '{keyword}' occurrences: {count}\n")
                        
                except Exception as e:
                    print(f"Error reading log file: {e}")
                    
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_regex_patterns())