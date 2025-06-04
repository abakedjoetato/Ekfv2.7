"""
Scalable Historical Parser
Enterprise-grade historical data processing with connection pooling and chronological integrity
"""

import asyncio
import discord
import logging
from typing import Optional, Dict, List, Optional, Any
from datetime import datetime, timezone
from bot.utils.connection_pool import connection_manager
from bot.utils.chronological_processor import MultiServerProcessor, ProcessingPhase

logger = logging.getLogger(__name__)

class ScalableProgressUI(discord.ui.View):
    """Enhanced progress UI for scalable historical processing"""
    
    def __init__(self, parser_instance, guild_id: int):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.parser = parser_instance
        self.guild_id = guild_id
        self.cancelled = False
        self.paused = False
        
    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.paused:
            self.paused = False
            button.label = "Pause"
            button.emoji = "⏸️"
            await interaction.response.edit_message(content="Processing resumed...", view=self)
        else:
            self.paused = True
            button.label = "Resume"
            button.emoji = "▶️"
            await interaction.response.edit_message(content="Processing paused...", view=self)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.cancelled = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Cancelling processing...", view=self)
    
    @discord.ui.button(label="Stats", style=discord.ButtonStyle.primary, emoji="📊")
    async def stats_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        stats = connection_manager.get_pool_stats()
        
        embed = discord.Embed(
            title="Connection Pool Statistics",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="Global Stats",
            value=f"Guilds: {stats['total_guilds']}\nServers: {stats['total_servers']}",
            inline=True
        )
        
        if str(self.guild_id) in stats.get('guild_details', {}):
            guild_stats = stats['guild_details'][str(self.guild_id)]
            embed.add_field(
                name="This Guild",
                value=f"Servers: {guild_stats['servers']}\nConnections: {guild_stats['total_connections']}\nFailed: {guild_stats['failed_servers']}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ScalableHistoricalParser:
    """Scalable historical parser with connection pooling and chronological processing"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions: Dict[int, MultiServerProcessor] = {}
        self.progress_messages: Dict[str, discord.Message] = {}
        
    async def start_connection_manager(self):
        """Initialize the connection manager"""
        await connection_manager.start()
        logger.info("Scalable historical parser connection manager started")
    
    async def stop_connection_manager(self):
        """Cleanup the connection manager"""
        await connection_manager.stop()
        logger.info("Scalable historical parser connection manager stopped")
    
    async def process_guild_servers(self, guild_id: int, target_channel: discord.TextChannel = None) -> Dict[str, Any]:
        """Process all servers for a guild with scalable architecture"""
        try:
            # Get all servers for the guild
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config or not guild_config.get('servers'):
                return {
                    'success': False,
                    'error': 'No servers configured for this guild'
                }
            
            servers = guild_config.get('servers', [])
            logger.info(f"Starting scalable processing for {len(servers)} servers in guild {guild_id}")
            
            # Send initial progress message to Discord
            if target_channel:
                initial_embed = discord.Embed(
                    title="🔍 Historical Data Processing Started",
                    description=f"Processing {len(servers)} servers for historical data...",
                    color=0x3498DB,
                    timestamp=datetime.now(timezone.utc)
                )
                initial_embed.add_field(
                    name="Status",
                    value="Initializing connections...",
                    inline=False
                )
                progress_msg = await target_channel.send(embed=initial_embed)
                self.progress_messages[f"{guild_id}"] = progress_msg
            
            # Find appropriate channel
            if not target_channel:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            target_channel = channel
                            break
            
            if not target_channel:
                return {
                    'success': False,
                    'error': 'No suitable channel found for progress updates'
                }
            
            # Create multi-server processor
            processor = MultiServerProcessor(guild_id, self.bot.db_manager)
            self.active_sessions[guild_id] = processor
            
            # Create progress UI
            progress_ui = ScalableProgressUI(self, guild_id)
            session_key = f"{guild_id}_scalable"
            
            # Send initial processing message
            initial_embed = discord.Embed(
                title="Scalable Historical Processing Started",
                description=f"Processing {len(servers)} servers with enterprise-grade architecture",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc)
            )
            
            initial_embed.add_field(
                name="Processing Architecture",
                value="• Connection pooling for efficiency\n• Chronological data integrity\n• Parallel server processing\n• Real-time progress tracking",
                inline=False
            )
            
            initial_embed.add_field(
                name="Guild Information",
                value=f"**Guild ID:** {guild_id}\n**Servers:** {len(servers)}\n**Status:** Initializing...",
                inline=False
            )
            
            progress_message = await target_channel.send(embed=initial_embed, view=progress_ui)
            self.progress_messages[session_key] = progress_message
            
            # Define progress callback
            async def progress_callback(stats):
                if progress_ui.cancelled:
                    return
                
                while progress_ui.paused:
                    await asyncio.sleep(1)
                    if progress_ui.cancelled:
                        return
                
                # Update progress embed
                embed = await self._create_progress_embed(guild_id, len(servers), stats)
                try:
                    await progress_message.edit(embed=embed, view=progress_ui)
                except discord.NotFound:
                    pass  # Message was deleted
                except Exception as e:
                    logger.error(f"Failed to update progress message: {e}")
            
            # Process all servers
            results = await processor.process_servers(servers, progress_callback)
            
            # Send completion message
            completion_embed = await self._create_completion_embed(results)
            try:
                # Disable UI buttons
                for item in progress_ui.children:
                    item.disabled = True
                await progress_message.edit(embed=completion_embed, view=progress_ui)
            except Exception as e:
                logger.error(f"Failed to update completion message: {e}")
            
            # Cleanup
            if guild_id in self.active_sessions:
                del self.active_sessions[guild_id]
            if session_key in self.progress_messages:
                del self.progress_messages[session_key]
            
            return results
            
        except Exception as e:
            logger.error(f"Scalable processing failed for guild {guild_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _create_progress_embed(self, guild_id: int, total_servers: int, stats) -> discord.Embed:
        """Create progress embed with current statistics"""
        embed = discord.Embed(
            title="Scalable Historical Processing",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Processing phase
        phase_emoji = {
            ProcessingPhase.DISCOVERY: "🔍",
            ProcessingPhase.CACHING: "💾",
            ProcessingPhase.PROCESSING: "⚡",
            ProcessingPhase.COMPLETE: "✅",
            ProcessingPhase.FAILED: "❌"
        }
        
        current_phase = getattr(stats, 'phase', ProcessingPhase.DISCOVERY)
        embed.add_field(
            name=f"{phase_emoji.get(current_phase, '🔄')} Current Phase",
            value=current_phase.title(),
            inline=True
        )
        
        # Server progress
        embed.add_field(
            name="Server Progress",
            value=f"{total_servers} servers processing in parallel",
            inline=True
        )
        
        # File statistics
        files_discovered = getattr(stats, 'files_discovered', 0)
        files_cached = getattr(stats, 'files_cached', 0)
        embed.add_field(
            name="File Progress",
            value=f"Discovered: {files_discovered}\nCached: {files_cached}",
            inline=True
        )
        
        # Data statistics
        total_lines = getattr(stats, 'total_lines', 0)
        valid_kills = getattr(stats, 'valid_kills', 0)
        processed_kills = getattr(stats, 'processed_kills', 0)
        
        embed.add_field(
            name="Data Processing",
            value=f"Total Lines: {total_lines:,}\nValid Kills: {valid_kills:,}\nProcessed: {processed_kills:,}",
            inline=True
        )
        
        # Performance metrics
        start_time = getattr(stats, 'start_time', None)
        if start_time:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            rate = processed_kills / max(1, duration)
            embed.add_field(
                name="Performance",
                value=f"Duration: {duration:.1f}s\nRate: {rate:.1f} kills/sec",
                inline=True
            )
        
        # Current file
        current_file = getattr(stats, 'current_file', '')
        if current_file:
            embed.add_field(
                name="Current File",
                value=current_file,
                inline=False
            )
        
        embed.set_footer(text="Scalable architecture ensures optimal performance and data integrity")
        return embed
    
    async def _create_completion_embed(self, results: Dict[str, Any]) -> discord.Embed:
        """Create completion embed with final results"""
        success = results.get('successful_servers', 0) == results.get('total_servers', 0)
        
        embed = discord.Embed(
            title="✅ Scalable Processing Complete" if success else "⚠️ Processing Complete with Issues",
            color=0x2ECC71 if success else 0xF39C12,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="Server Summary",
            value=f"Total: {results.get('total_servers', 0)}\nSuccessful: {results.get('successful_servers', 0)}\nFailed: {results.get('total_servers', 0) - results.get('successful_servers', 0)}",
            inline=True
        )
        
        embed.add_field(
            name="Data Processed",
            value=f"Files: {results.get('total_files_processed', 0):,}\nKills: {results.get('total_kills_processed', 0):,}",
            inline=True
        )
        
        # Connection pool stats
        pool_stats = connection_manager.get_pool_stats()
        embed.add_field(
            name="Resource Usage",
            value=f"Active Connections: {pool_stats.get('total_servers', 0)}\nGuilds Served: {pool_stats.get('total_guilds', 0)}",
            inline=True
        )
        
        embed.set_footer(text="All data processed in chronological order to ensure accurate kill streaks")
        return embed
    
    async def auto_refresh_after_server_add(self, guild_id: int, server_config: Dict[str, Any], target_channel=None):
        """Auto-trigger scalable processing after server addition"""
        try:
            logger.info(f"Auto-triggering scalable historical processing for guild {guild_id}")
            
            # Process just the newly added server initially
            # Full guild processing can be triggered manually
            await self.process_guild_servers(guild_id, target_channel)
            
        except Exception as e:
            logger.error(f"Auto-refresh failed for guild {guild_id}: {e}")
    
    def get_session_status(self, guild_id: int) -> Dict[str, Any]:
        """Get status of active processing session"""
        if guild_id in self.active_sessions:
            return {
                'active': True,
                'guild_id': guild_id,
                'processor': self.active_sessions[guild_id]
            }
        return {'active': False}