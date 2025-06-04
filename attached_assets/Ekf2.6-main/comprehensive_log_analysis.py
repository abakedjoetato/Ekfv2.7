"""
Comprehensive Log Analysis - Find actual player connection patterns in Deadside logs
"""

import asyncio
import asyncssh
import os
import re

async def analyze_log_patterns():
    """Analyze actual log patterns to understand player connections and events"""
    try:
        host = "79.127.236.1"
        port = 8822
        username = os.getenv('SSH_USERNAME')
        password = os.getenv('SSH_PASSWORD')
        
        if not username or not password:
            print("Missing SSH credentials - SSH_USERNAME or SSH_PASSWORD not set")
            return
        
        print(f"Analyzing Deadside log patterns on {host}:{port}...")
        
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
                    # Get a much larger sample to find player patterns
                    file_stat = await sftp.stat(log_path)
                    file_size = file_stat.size
                    
                    # Read the last 10KB to get more data
                    start_pos = max(0, file_size - 10240)
                    
                    async with sftp.open(log_path, 'rb') as f:
                        await f.seek(start_pos)
                        recent_data = await f.read()
                        
                    log_content = recent_data.decode('utf-8', errors='ignore')
                    lines = [line.strip() for line in log_content.split('\n') if line.strip()]
                    
                    print(f"\nAnalyzing {len(lines)} log lines for patterns:")
                    print(f"File size: {file_size:,} bytes")
                    print("-" * 80)
                    
                    # Categorize all log types
                    log_categories = {}
                    
                    for line in lines:
                        # Extract the log type (e.g., LogSFPS, LogNet, etc.)
                        if ']Log' in line:
                            log_type_match = re.search(r'\]Log(\w+):', line)
                            if log_type_match:
                                log_type = log_type_match.group(1)
                                if log_type not in log_categories:
                                    log_categories[log_type] = []
                                log_categories[log_type].append(line)
                    
                    print("Log categories found:")
                    for log_type, entries in log_categories.items():
                        print(f"  {log_type}: {len(entries)} entries")
                        # Show first 2 examples
                        for i, entry in enumerate(entries[:2]):
                            print(f"    Example {i+1}: {entry[:120]}...")
                        print()
                    
                    # Look for specific keywords that might indicate player activity
                    player_keywords = ['player', 'user', 'client', 'auth', 'login', 'connect', 'disconnect', 'session', 'spawn', 'join', 'leave']
                    
                    print("Searching for player-related patterns:")
                    player_lines = []
                    for line in lines:
                        line_lower = line.lower()
                        for keyword in player_keywords:
                            if keyword in line_lower:
                                player_lines.append(line)
                                break
                    
                    if player_lines:
                        print(f"Found {len(player_lines)} potential player-related lines:")
                        for line in player_lines[:10]:  # Show first 10
                            print(f"  -> {line}")
                    else:
                        print("No player-related patterns found with standard keywords")
                    
                    # Test our current regex patterns against actual data
                    print("\nTesting current regex patterns:")
                    
                    # Event patterns
                    event_patterns = {
                        'mission_start': re.compile(r'LogSFPS: Mission (\w+) switched to READY', re.IGNORECASE),
                        'mission_end': re.compile(r'LogSFPS: Mission (\w+) switched to WAITING', re.IGNORECASE),
                        'airdrop': re.compile(r'LogSFPS: AirDrop switched to Dropping', re.IGNORECASE),
                        'patrol_active': re.compile(r'LogSFPS: PatrolPoint (\w+) switched to ACTIVE', re.IGNORECASE),
                    }
                    
                    total_matches = 0
                    for pattern_name, pattern in event_patterns.items():
                        matches = []
                        for line in lines:
                            if pattern.search(line):
                                matches.append(line)
                                total_matches += 1
                        
                        if matches:
                            print(f"  {pattern_name}: {len(matches)} matches")
                            for match in matches[:3]:  # Show first 3
                                print(f"    -> {match}")
                        else:
                            print(f"  {pattern_name}: 0 matches")
                    
                    print(f"\nTotal event matches found: {total_matches}")
                    
                    # Look for any patterns that might indicate online players
                    print("\nSearching for active player indicators:")
                    
                    # Check for any numeric patterns that might indicate player counts
                    for line in lines[-20:]:  # Last 20 lines
                        if any(word in line.lower() for word in ['total', 'count', 'active', 'online']):
                            print(f"  Potential count: {line}")
                        
                        # Look for numbers that might be player counts (1-60 range)
                        numbers = re.findall(r'\b([1-9]|[1-5][0-9]|60)\b', line)
                        if numbers:
                            print(f"  Numbers found in: {line[:100]}... -> {numbers}")
                        
                except Exception as e:
                    print(f"Error reading log file: {e}")
                    
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_log_patterns())