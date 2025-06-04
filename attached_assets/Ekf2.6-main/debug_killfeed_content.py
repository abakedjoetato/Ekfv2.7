#!/usr/bin/env python3
"""
Debug Killfeed Content - Examine actual CSV content to understand why no events are detected
"""
import asyncio
import asyncssh
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def examine_killfeed_content():
    """Examine the actual content of the killfeed CSV file"""
    try:
        # Connect to the server using same config as bot
        import os
        conn = await asyncssh.connect(
            '79.127.236.1',
            port=8822,
            username='baked',
            password=os.environ.get('SSH_PASSWORD'),
            known_hosts=None,
            kex_algs=['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521'],
            encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', 'aes192-cbc', 'aes256-cbc'],
            mac_algs=['hmac-sha1', 'hmac-sha2-256', 'hmac-sha2-512'],
            compression_algs=['none'],
            server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss']
        )
        
        sftp = await conn.start_sftp_client()
        
        # First explore the directory structure to find the correct path
        base_path = "./79.127.236.1_7020/actual1/deathlogs/"
        
        print(f"=== KILLFEED DIRECTORY EXPLORATION ===")
        print(f"Base path: {base_path}")
        
        # Explore directory structure recursively
        def explore_directory(path, depth=0):
            """Recursively explore directory structure"""
            indent = "  " * depth
            try:
                files = []
                if depth < 3:  # Prevent infinite recursion
                    items = sftp.listdir(path) if hasattr(sftp, 'listdir') else []
                    for item in items:
                        item_path = f"{path}/{item}" if not path.endswith('/') else f"{path}{item}"
                        try:
                            # Check if it's a file or directory
                            stat_info = sftp.stat(item_path) if hasattr(sftp, 'stat') else None
                            if item.endswith('.csv'):
                                files.append((item_path, item))
                                print(f"{indent}📄 CSV: {item}")
                            elif '.' not in item or item.startswith('.'):
                                print(f"{indent}📁 DIR: {item}")
                                sub_files = explore_directory(item_path, depth + 1)
                                files.extend(sub_files)
                            else:
                                print(f"{indent}📄 FILE: {item}")
                        except Exception as e:
                            print(f"{indent}❌ ERROR accessing {item}: {e}")
                return files
            except Exception as e:
                print(f"{indent}❌ ERROR listing {path}: {e}")
                return []
        
        try:
            csv_files = explore_directory(base_path)
            print(f"\n=== FOUND CSV FILES ===")
            for file_path, filename in csv_files:
                print(f"  {file_path}")
            
            if not csv_files:
                print("No CSV files found - checking alternate paths...")
                # Try different possible paths
                alternate_paths = [
                    "./79.127.236.1_7020/actual1/deathlogs/world_0/",
                    "./79.127.236.1_7020/deathlogs/",
                    "./deathlogs/",
                    "./world_0/deathlogs/"
                ]
                
                for alt_path in alternate_paths:
                    print(f"\nChecking alternate path: {alt_path}")
                    try:
                        alt_files = explore_directory(alt_path)
                        csv_files.extend(alt_files)
                    except Exception as e:
                        print(f"  Path not accessible: {e}")
            
            # Now analyze the newest CSV file if found
            if csv_files:
                # Sort by filename to get the newest
                csv_files.sort(key=lambda x: x[1], reverse=True)
                newest_csv = csv_files[0][0]
                print(f"\n=== ANALYZING NEWEST CSV: {newest_csv} ===")
                
                async with sftp.open(newest_csv, 'r') as file:
                content = await file.read()
                lines = content.split('\n')
                
                print(f"Total lines: {len(lines)}")
                print(f"File size: {len(content)} bytes")
                
                print(f"\n=== FIRST 10 LINES ===")
                for i, line in enumerate(lines[:10]):
                    if line.strip():
                        print(f"Line {i+1}: {line}")
                
                print(f"\n=== LAST 10 LINES ===")
                for i, line in enumerate(lines[-10:]):
                    if line.strip():
                        actual_line_num = len(lines) - 10 + i + 1
                        print(f"Line {actual_line_num}: {line}")
                
                # Look for kill patterns
                print(f"\n=== KILL EVENT ANALYSIS ===")
                kill_patterns = ['killed', 'eliminated', 'died', 'death', 'kill']
                for pattern in kill_patterns:
                    matching_lines = [line for line in lines if pattern.lower() in line.lower()]
                    print(f"Lines containing '{pattern}': {len(matching_lines)}")
                    if matching_lines:
                        print(f"  Example: {matching_lines[0][:100]}...")
                
                # Check CSV structure
                print(f"\n=== CSV STRUCTURE ANALYSIS ===")
                if lines:
                    first_line = lines[0].strip()
                    if first_line:
                        columns = first_line.split(',')
                        print(f"Columns ({len(columns)}): {columns}")
                        
                        # Check if it's a header row
                        print(f"Likely header row: {any(col.lower() in ['time', 'timestamp', 'killer', 'victim', 'weapon'] for col in columns)}")
                
                # Sample data rows
                print(f"\n=== SAMPLE DATA ROWS ===")
                data_rows = [line for line in lines[1:6] if line.strip()]
                for i, row in enumerate(data_rows):
                    print(f"Row {i+1}: {row}")
                
        except Exception as file_error:
            print(f"Failed to read CSV file: {file_error}")
            
            # Try listing the directory to see what files exist
            try:
                print(f"\n=== DIRECTORY LISTING ===")
                dir_path = "./79.127.236.1_7020/actual1/deathlogs/"
                files = await sftp.listdir(dir_path)
                print(f"Files in {dir_path}:")
                for file in sorted(files):
                    try:
                        stat = await sftp.stat(f"{dir_path}/{file}")
                        size = stat.st_size
                        print(f"  {file} ({size} bytes)")
                    except:
                        print(f"  {file} (stat failed)")
            except Exception as dir_error:
                print(f"Failed to list directory: {dir_error}")
        
        await conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(examine_killfeed_content())