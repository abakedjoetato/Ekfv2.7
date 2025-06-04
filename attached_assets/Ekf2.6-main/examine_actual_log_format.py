"""
Examine Actual Log Format
Direct examination of the CSV file format to understand why parsing is failing
"""

import asyncio
import asyncssh
import os

async def examine_log_format():
    """Examine the actual log format to fix parsing"""
    try:
        host = "79.127.236.1"
        port = 8822
        username = os.getenv('SSH_USERNAME')
        password = os.getenv('SSH_PASSWORD')
        
        if not username or not password:
            print("Missing SSH credentials - SSH_USERNAME or SSH_PASSWORD not set")
            return
        
        print(f"Connecting to {host}:{port} to examine log format...")
        
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
                    # Get the last 2000 bytes to see recent activity
                    file_stat = await sftp.stat(log_path)
                    file_size = file_stat.size
                    
                    # Read the last portion of the file
                    start_pos = max(0, file_size - 2000)
                    
                    async with sftp.open(log_path, 'rb') as f:
                        await f.seek(start_pos)
                        recent_data = await f.read()
                        
                    log_content = recent_data.decode('utf-8', errors='ignore')
                    lines = log_content.split('\n')
                    
                    print(f"\nExamining last {len(lines)} lines from log file:")
                    print(f"File size: {file_size} bytes")
                    print(f"Reading from position: {start_pos}")
                    print("-" * 80)
                    
                    # Look for player connection patterns
                    connection_lines = []
                    for i, line in enumerate(lines[-50:]):  # Last 50 lines
                        if line.strip():
                            # Look for potential player connection keywords
                            if any(keyword in line.lower() for keyword in ['player', 'connect', 'disconnect', 'join', 'leave', 'login', 'logout', 'auth']):
                                connection_lines.append(line)
                            print(f"Line {i}: {line}")
                    
                    print("-" * 80)
                    print(f"\nFound {len(connection_lines)} potential connection-related lines:")
                    for line in connection_lines:
                        print(f"  -> {line}")
                    
                    # Also check for common event patterns
                    event_lines = []
                    for line in lines[-100:]:
                        if any(keyword in line.lower() for keyword in ['mission', 'helicopter', 'airdrop', 'trader', 'event']):
                            event_lines.append(line)
                    
                    print(f"\nFound {len(event_lines)} potential event-related lines:")
                    for line in event_lines[:10]:  # Show first 10
                        print(f"  -> {line}")
                        
                except Exception as e:
                    print(f"Error reading log file: {e}")
                    
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(examine_log_format())