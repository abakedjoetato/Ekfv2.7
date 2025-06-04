"""
Test SSH Encryption Fix - Verify the DH parameters fix works
"""

import asyncio
import asyncssh
import os

async def test_ssh_connection():
    """Test SSH connection with compatible encryption parameters"""
    try:
        print("Testing SSH connection with encryption compatibility fix...")
        
        # SSH credentials from sftp_credentials
        ssh_host = "79.127.236.1"
        ssh_port = 8822
        ssh_username = "baked" 
        ssh_password = os.getenv('SSH_PASSWORD')
        
        if not ssh_password:
            print("ERROR: SSH_PASSWORD environment variable not set")
            return False
            
        log_path = "/home/deadside/79.127.236.1_7020/actual1/Deadside/Saved/Logs/Deadside.log"
        
        print(f"Connecting to {ssh_host}:{ssh_port} as {ssh_username}")
        
        # Test connection with compatible encryption parameters
        async with asyncssh.connect(
            ssh_host,
            port=ssh_port,
            username=ssh_username,
            password=ssh_password,
            known_hosts=None,
            kex_algs=['diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'diffie-hellman-group-exchange-sha256'],
            encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-gcm@openssh.com', 'aes256-gcm@openssh.com'],
            mac_algs=['hmac-sha2-256', 'hmac-sha2-512', 'hmac-sha1'],
            connect_timeout=30.0
        ) as conn:
            print("✅ SSH connection successful!")
            
            async with conn.start_sftp_client() as sftp:
                print("✅ SFTP client started")
                
                # Test file access
                try:
                    file_stat = await sftp.stat(log_path)
                    print(f"✅ Log file accessible: {log_path}")
                    print(f"  File size: {file_stat.size} bytes")
                    print(f"  Modified: {file_stat.mtime}")
                    
                    # Read a small sample
                    async with sftp.open(log_path, 'r') as f:
                        sample = await f.read(1000)
                        print(f"✅ Sample read: {len(sample)} characters")
                        
                    return True
                    
                except Exception as e:
                    print(f"❌ File access error: {e}")
                    return False
                    
    except Exception as e:
        print(f"❌ SSH connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ssh_connection())
    if result:
        print("\n🎉 SSH encryption fix successful - unified parser will now work!")
    else:
        print("\n💥 SSH connection still failing - need alternative approach")