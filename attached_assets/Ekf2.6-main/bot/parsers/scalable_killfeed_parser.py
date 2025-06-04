"""
Scalable Killfeed Parser
Enterprise-grade real-time killfeed processing with state coordination and connection pooling
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from bot.utils.simple_killfeed_processor import MultiServerSimpleKillfeedProcessor
from bot.utils.shared_parser_state import get_shared_state_manager

logger = logging.getLogger(__name__)

class ScalableKillfeedParser:
    """Scalable killfeed parser with connection pooling and state coordination"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions: Dict[int, MultiServerSimpleKillfeedProcessor] = {}
        self.state_manager = get_shared_state_manager()
        
    async def run_killfeed_parser(self):
        """Main scheduled killfeed parser execution"""
        try:
            logger.info("🔍 Starting scalable killfeed parser run...")
            
            # Get all guilds with connected servers
            guilds_with_servers = await self._get_all_guilds_with_servers()
            
            if not guilds_with_servers:
                logger.info("🔍 Scalable killfeed parser: Found 0 connected servers")
                return
            
            total_servers = sum(len(servers) for servers in guilds_with_servers.values())
            logger.info(f"🔍 Scalable killfeed parser: Found {len(guilds_with_servers)} guilds with {total_servers} connected servers")
            
            # Process all guilds concurrently
            tasks = []
            for guild_id, servers in guilds_with_servers.items():
                task = self._process_guild_killfeed(guild_id, servers)
                tasks.append(task)
            
            # Execute all guild processing tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log summary
            successful_guilds = sum(1 for result in results if isinstance(result, dict) and result.get('success'))
            total_processed = sum(result.get('processed_servers', 0) for result in results if isinstance(result, dict))
            total_skipped = sum(result.get('skipped_servers', 0) for result in results if isinstance(result, dict))
            
            logger.info(f"📊 Scalable killfeed parser completed: {successful_guilds} guilds, {total_processed} servers processed, {total_skipped} servers skipped")
            
            # Cleanup stale sessions periodically
            if self.state_manager:
                await self.state_manager.cleanup_stale_sessions()
            
        except Exception as e:
            logger.error(f"Scalable killfeed parser execution failed: {e}")
    
    async def _get_all_guilds_with_servers(self) -> Dict[int, List[Dict[str, Any]]]:
        """Get all guilds that have connected servers using direct database access"""
        guilds_with_servers = {}
        
        try:
            # Use direct MongoDB connection for thread safety
            import os
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_uri = os.environ.get('MONGO_URI')
            if not mongo_uri:
                logger.error("MONGO_URI not available")
                return guilds_with_servers
            
            client = AsyncIOMotorClient(mongo_uri)
            database = client.emerald_killfeed
            collection = database.guild_configs
            
            # Find guilds with enabled servers for killfeed processing
            cursor = collection.find({
                'servers': {
                    '$exists': True,
                    '$not': {'$size': 0},
                    '$elemMatch': {'enabled': True}
                }
            })
            
            guild_docs = await cursor.to_list(length=None)
            
            for guild_doc in guild_docs:
                guild_id = guild_doc.get('guild_id')
                servers = guild_doc.get('servers', [])
                
                if guild_id and servers:
                    # Filter for enabled servers only
                    enabled_servers = [s for s in servers if s.get('enabled', False)]
                    
                    if enabled_servers:
                        # Add guild_id to each server config
                        for server in enabled_servers:
                            server['guild_id'] = guild_id
                        
                        guilds_with_servers[guild_id] = enabled_servers
            
            logger.info(f"Found {len(guilds_with_servers)} guilds with enabled servers for killfeed")
            
        except Exception as e:
            logger.error(f"Failed to get guilds with servers: {e}")
        
        return guilds_with_servers
    
    async def _process_guild_killfeed(self, guild_id: int, servers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process killfeed for all servers in a guild"""
        try:
            logger.debug(f"Processing killfeed for guild {guild_id} with {len(servers)} servers")
            
            # Create multi-server processor using simplified approach
            processor = MultiServerSimpleKillfeedProcessor(guild_id, self.bot)
            self.active_sessions[guild_id] = processor
            
            # Process available servers (excluding those under historical processing)
            results = await processor.process_available_servers(servers)
            
            # Log results
            if results.get('skipped_servers', 0) > 0:
                logger.info(f"🔄 Guild {guild_id}: Skipped {results['skipped_servers']} servers under historical processing")
            
            if results.get('processed_servers', 0) > 0:
                logger.info(f"✅ Guild {guild_id}: Processed {results['processed_servers']} servers successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to process guild {guild_id} killfeed: {e}")
            return {
                'success': False,
                'guild_id': guild_id,
                'error': str(e)
            }
        finally:
            # Cleanup session
            if guild_id in self.active_sessions:
                del self.active_sessions[guild_id]
    
    async def process_server_killfeed_manual(self, guild_id: int, server_name: str) -> Dict[str, Any]:
        """Manually trigger killfeed processing for a specific server"""
        try:
            # Get server configuration
            guild_config = await getattr(self.bot, 'cached_db_manager', self.bot.db_manager).get_guild(guild_id)
            if not guild_config or not guild_config.get('servers'):
                return {
                    'success': False,
                    'error': 'No servers configured for this guild'
                }
            
            # Find the specific server
            target_server = None
            for server in guild_config.get('servers', []):
                if server.get('name') == server_name or server.get('server_name') == server_name:
                    if server.get('killfeed_enabled'):
                        server['guild_id'] = guild_id
                        target_server = server
                        break
            
            if not target_server:
                return {
                    'success': False,
                    'error': f'Server {server_name} not found or killfeed not enabled'
                }
            
            # Process single server using simplified approach
            processor = MultiServerSimpleKillfeedProcessor(guild_id, self.bot)
            results = await processor.process_available_servers([target_server])
            
            return {
                'success': True,
                'server_name': server_name,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Manual killfeed processing failed for {guild_id}/{server_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_killfeed_status(self, guild_id: int) -> Dict[str, Any]:
        """Get current killfeed processing status for a guild"""
        try:
            status = {
                'guild_id': guild_id,
                'active_session': guild_id in self.active_sessions,
                'servers_configured': 0,
                'killfeed_enabled_servers': 0,
                'historical_conflicts': 0
            }
            
            # Get guild configuration
            guild_config = await getattr(self.bot, 'cached_db_manager', self.bot.db_manager).get_guild(guild_id)
            if guild_config and guild_config.get('servers'):
                status['servers_configured'] = len(guild_config['servers'])
                
                killfeed_servers = []
                for server in guild_config['servers']:
                    if server.get('killfeed_enabled'):
                        status['killfeed_enabled_servers'] += 1
                        server['guild_id'] = guild_id
                        killfeed_servers.append(server)
                
                # Check for historical processing conflicts
                if self.state_manager and killfeed_servers:
                    available_servers = await self.state_manager.get_available_servers_for_killfeed(killfeed_servers)
                    status['historical_conflicts'] = len(killfeed_servers) - len(available_servers)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get killfeed status for guild {guild_id}: {e}")
            return {
                'guild_id': guild_id,
                'error': str(e)
            }
    
    async def cleanup_killfeed_connections(self):
        """Cleanup killfeed parser connections"""
        try:
            # Cancel any active sessions
            for guild_id, processor in list(self.active_sessions.items()):
                for server_processor in processor.active_processors.values():
                    server_processor.cancel()
                del self.active_sessions[guild_id]
            
            logger.info("Cleaned up scalable killfeed parser connections")
            
        except Exception as e:
            logger.error(f"Failed to cleanup killfeed connections: {e}")
    
    def get_active_sessions(self) -> Dict[int, Any]:
        """Get currently active killfeed processing sessions"""
        return {
            guild_id: {
                'guild_id': guild_id,
                'processors': len(processor.active_processors),
                'active': True
            }
            for guild_id, processor in self.active_sessions.items()
        }