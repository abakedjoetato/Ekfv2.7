"""
Server Query Utilities
Direct server querying for real-time player counts
"""

import socket
import struct
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ServerQuery:
    """Query game servers for real-time information"""
    
    @staticmethod
    async def query_source_server(host: str, port: int, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Query Source engine server using A2S_INFO protocol"""
        try:
            # A2S_INFO packet
            packet = b'\xFF\xFF\xFF\xFF\x54Source Engine Query\x00'
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            
            # Send query
            sock.sendto(packet, (host, port))
            
            # Receive response
            data, addr = sock.recvfrom(1024)
            sock.close()
            
            if len(data) < 5:
                return None
                
            # Parse response
            if data[4] == 0x49:  # A2S_INFO response
                pos = 5
                
                # Skip protocol version
                pos += 1
                
                # Server name
                name_end = data.find(b'\x00', pos)
                server_name = data[pos:name_end].decode('utf-8', errors='ignore')
                pos = name_end + 1
                
                # Map name
                map_end = data.find(b'\x00', pos)
                map_name = data[pos:map_end].decode('utf-8', errors='ignore')
                pos = map_end + 1
                
                # Folder name
                folder_end = data.find(b'\x00', pos)
                pos = folder_end + 1
                
                # Game name
                game_end = data.find(b'\x00', pos)
                pos = game_end + 1
                
                # Skip app ID
                pos += 2
                
                # Player count
                players = struct.unpack('<B', data[pos:pos+1])[0]
                pos += 1
                
                # Max players
                max_players = struct.unpack('<B', data[pos:pos+1])[0]
                
                return {
                    'server_name': server_name,
                    'map': map_name,
                    'players': players,
                    'max_players': max_players,
                    'query_successful': True
                }
                
        except Exception as e:
            logger.debug(f"Server query failed for {host}:{port} - {e}")
            
        return None
    
    @staticmethod
    async def query_deadside_server(host: str, query_port: int = None) -> Optional[Dict[str, Any]]:
        """Query Deadside server for player information"""
        
        # Try common Deadside query ports
        ports_to_try = []
        if query_port:
            ports_to_try.append(query_port)
        
        # Common Deadside query ports (game port + 1, or specific query ports)
        ports_to_try.extend([7021, 27015, 27016, 7020])
        
        for port in ports_to_try:
            result = await ServerQuery.query_source_server(host, port)
            if result and result.get('query_successful'):
                logger.info(f"✅ Server query successful on {host}:{port}")
                return result
                
        logger.warning(f"❌ All server query attempts failed for {host}")
        return None