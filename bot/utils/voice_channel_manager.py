"""
Voice Channel Manager - Updates voice channel names with current player counts
"""

import logging
import discord
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class VoiceChannelManager:
    """Manages voice channel updates with player counts"""
    
    def __init__(self, bot):
        self.bot = bot
        self.channel_cache = {}
        
    async def update_voice_channel_count(self, guild_id: int, server_id: str, online_count: int, queued_count: int = 0) -> bool:
        """Update voice channel name with server name, player count, max count, and queued count"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return False
            
            # Get voice channel configuration from database
            voice_channel_id = await self._get_voice_channel_id(guild_id, server_id)
            if not voice_channel_id:
                logger.warning(f"No voice channel configured for guild {guild_id}, server {server_id}")
                return False
                
            voice_channel = guild.get_channel(voice_channel_id)
            if not voice_channel:
                logger.error(f"Voice channel {voice_channel_id} not found in guild {guild_id}")
                return False
                
            # Get server configuration for name and max players
            server_name, max_players = await self._get_server_info(guild_id, server_id)
            if not server_name:
                server_name = f"Server {server_id}"
            if not max_players:
                max_players = 50  # Correct Deadside server size from playersmaxcount=50
                
            # Format channel name: "Server Name | current/max" or "Server Name | current/max 🕑queued"
            if queued_count > 0:
                new_name = f"{server_name} | {online_count}/{max_players} 🕑{queued_count}"
            else:
                new_name = f"{server_name} | {online_count}/{max_players}"
            
            # Update channel name if changed
            if voice_channel.name != new_name:
                await voice_channel.edit(name=new_name)
                logger.info(f"Updated voice channel to '{new_name}' (Online: {online_count}, Max: {max_players}, Queued: {queued_count})")
                return True
            else:
                logger.debug(f"Voice channel name unchanged: {new_name}")
                return True
                
        except discord.Forbidden:
            logger.error(f"No permission to edit voice channel in guild {guild_id}")
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error updating voice channel: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating voice channel: {e}")
            return False
            
    async def _get_voice_channel_id(self, guild_id: int, server_id: str) -> Optional[int]:
        """Get voice channel ID from guild configuration"""
        try:
            # Get guild configuration from database
            guild_config = await self.bot.db_manager.guild_configs.find_one({'guild_id': guild_id})
            if not guild_config:
                return None
                
            server_channels = guild_config.get('server_channels', {})
            
            # Try server-specific configuration first
            server_name = await self._get_server_name(guild_id, server_id)
            if server_name and server_name in server_channels:
                # Check multiple possible voice channel field names
                for field_name in ['playercountvc', 'voice_counter', 'voice_channel']:
                    voice_channel_id = server_channels[server_name].get(field_name)
                    if voice_channel_id:
                        return voice_channel_id
                    
            # Fall back to default configuration
            if 'default' in server_channels:
                # Check multiple possible voice channel field names
                for field_name in ['playercountvc', 'voice_counter', 'voice_channel']:
                    voice_channel_id = server_channels['default'].get(field_name)
                    if voice_channel_id:
                        return voice_channel_id
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting voice channel ID: {e}")
            return None
            
    async def _get_server_info(self, guild_id: int, server_id: str) -> tuple[Optional[str], Optional[int]]:
        """Get server name and max players from configuration and live server data"""
        try:
            guild_config = await self.bot.db_manager.guild_configs.find_one({'guild_id': guild_id})
            if not guild_config:
                return None, None
                
            servers = guild_config.get('servers', [])
            for server in servers:
                if str(server.get('server_id')) == str(server_id) or str(server.get('_id')) == str(server_id):
                    server_name = server.get('server_name') or server.get('name')
                    
                    # Use correct max player count for Deadside servers
                    max_players = server.get('max_players') or server.get('player_limit') or 50
                    
                    return server_name, max_players
                    
            return None, None
            
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            return None, None
            
    async def _parse_max_players_from_logs(self, guild_id: int, server_id: str) -> Optional[int]:
        """Parse max player count from Deadside.log command line"""
        try:
            import re
            # from bot.utils.connection_pool import ConnectionPool
            
            # Get server SSH configuration
            guild_config = await self.bot.db_manager.guild_configs.find_one({'guild_id': guild_id})
            if not guild_config:
                return None
                
            servers = guild_config.get('servers', [])
            server_config = None
            for server in servers:
                if str(server.get('server_id')) == str(server_id) or str(server.get('_id')) == str(server_id):
                    server_config = server
                    break
                    
            if not server_config:
                return None
                
            # Get SSH connection details
            ssh_host = server_config.get('ssh_host')
            ssh_port = server_config.get('ssh_port', 22)
            ssh_username = server_config.get('ssh_username')
            ssh_password = server_config.get('ssh_password')
            
            if not all([ssh_host, ssh_username, ssh_password]):
                return None
                
            # Connect and read log file via SFTP
            import asyncssh
            async with asyncssh.connect(
                host=ssh_host,
                port=ssh_port,
                username=ssh_username,
                password=ssh_password,
                known_hosts=None
            ) as conn:
                sftp = await conn.start_sftp_client()
            
                log_path = server_config.get('log_path', f"./{ssh_host}_{server_id}/Logs/Deadside.log")
                
                # Read recent log content (last 50 lines should contain command line)
                async with sftp.open(log_path, 'r') as f:
                    content = await f.read()
                    lines = content.split('\n')[-50:]  # Check last 50 lines
                
            # Look for LogInit command line with playersmaxcount
            for line in lines:
                if 'LogInit: Command Line:' in line and 'playersmaxcount=' in line:
                    match = re.search(r'-playersmaxcount=(\d+)', line)
                    if match:
                        max_count = int(match.group(1))
                        logger.info(f"Parsed max players from logs: {max_count}")
                        return max_count
                        
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse max players from logs: {e}")
            return None
    
    async def _get_server_name(self, guild_id: int, server_id: str) -> Optional[str]:
        """Get server name from configuration"""
        try:
            server_name, _ = await self._get_server_info(guild_id, server_id)
            return server_name
        except Exception as e:
            logger.error(f"Error getting server name for {server_id}: {e}")
            return None