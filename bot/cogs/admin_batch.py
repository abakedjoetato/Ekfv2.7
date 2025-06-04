"""
Admin Batch Management Cog - Monitor and control batch sender
"""

import discord
import discord
import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class AdminBatch(discord.Cog):
    """Admin commands for batch sender management"""

    def __init__(self, bot):
        self.bot = bot
    
    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access - unified validation"""
        try:

            pass
            if hasattr(self.bot, 'premium_manager_v2'):
                return await self.bot.premium_manager_v2.has_premium_access(guild_id)
            else:
                return False
        except Exception as e:
            logger.error(f"Premium access check failed: {e}")
            return False

    @discord.slash_command(name="batch_stats", description="Show current batch sender statistics")
    @discord.default_permissions(administrator=True)
    async def batch_stats(self, ctx: discord.ApplicationContext):
        """Show current batch sender statistics"""
        if not ctx.guild:
            await ctx.respond("❌ This command must be used in a server", ephemeral=True)
            return
            
        guild_id = ctx.guild.id
        server_id = "default"  # Default server for batch operations
        if not ctx.guild:
            await ctx.respond("❌ This command must be used in a server", ephemeral=True)
            return
            
        server_id = "default"  # Default server for batch operations
        if not ctx.guild:
            await ctx.respond("❌ This command must be used in a server", ephemeral=True)
            return
            
        server_id = "default"  # Default server for batch stats
        """Show current batch sender statistics"""
        try:

            pass
            await ctx.defer()
            guild_id = ctx.guild_id

            # Get all servers for this guild
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                await ctx.respond("No guild configuration found", ephemeral=True)
                return

            servers = guild_config.get('servers', [])
            if not servers:
                await ctx.respond("No servers configured for this guild", ephemeral=True)
                return

            embed = discord.Embed(
                title="🐛 Player Count Debug Information",
                color=0xff9900,
                timestamp=datetime.now(timezone.utc)
            )

            # Check intelligent connection parser
            if hasattr(self.bot, 'log_parser') and hasattr(self.bot.log_parser, 'connection_parser'):
                connection_parser = self.bot.log_parser.connection_parser

                for server_config in servers:
                    server_name = server_config.get('name', 'Unknown')
                    current_server_id = str(server_config.get('_id', 'unknown'))

                    # Skip if specific server requested and this isn't it
                    if server_id and current_server_id != server_id:
                        continue

                    server_key = f"{guild_id}_{current_server_id}"

                    # Get current stats
                    stats = connection_parser.get_server_stats(server_key)

                    # Debug the state
                    connection_parser.debug_server_state(server_key)

                    embed.add_field(
                        name=f"🖥️ {server_name} (ID: {current_server_id})",
                        value=f"**Queue Count:** {stats.get('queue_count', 0)}\n"
                              f"**Player Count:** {stats.get('player_count', 0)}\n"
                              f"**Server Key:** `{server_key}`",
                        inline=False
                    )

                # Check if specific server was requested but not found
                if server_id:
                    found_server = any(str(s.get('_id', '')) == server_id for s in servers)
                    if not found_server:
                        embed.add_field(
                            name="Server Not Found",
                            value=f"Server ID `{server_id}` not found in guild configuration",
                            inline=False
                        )

            else:
                embed.add_field(
                    name="Parser Not Available",
                    value="Connection parser not found or not initialized",
                    inline=False
                )

            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in debug_player_count command: {e}")
            await ctx.respond(f"Error debugging player count: {str(e)}", ephemeral=True)

    @discord.slash_command(name="reset_player_count", description="Reset player count tracking for a server")
    @discord.default_permissions(administrator=True)
    async def reset_player_count(self, ctx: discord.ApplicationContext, server_id: str):
        """Reset player count tracking for a server"""
        if not ctx.guild:
            await ctx.respond("❌ This command must be used in a server", ephemeral=True)
            return
            
        guild_id = ctx.guild.id
        if not server_id:
            server_id = "default"
        if not ctx.guild:
            await ctx.respond("❌ This command must be used in a server", ephemeral=True)
            return
            
        guild_id = ctx.guild.id
        server_id = server_id or "default"  # Use provided or default
        try:

            pass
            guild_id = ctx.guild_id
            server_key = f"{guild_id}_{server_id}"

            # Reset in intelligent connection parser
            if hasattr(self.bot, 'log_parser') and hasattr(self.bot.log_parser, 'connection_parser'):
                connection_parser = self.bot.log_parser.connection_parser
                connection_parser.reset_server_counts(server_key)

                embed = discord.Embed(
                    title="🔄 Player Count Reset",
                    description=f"Player count tracking has been reset for server `{server_id}`",
                    color=0x00ff88,
                    timestamp=datetime.now(timezone.utc)
                )

                embed.add_field(
                    name="New Counts",
                    value="**Queue Count:** 0\n**Player Count:** 0",
                    inline=False
                )

                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.respond("Connection parser not available for reset", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in reset_player_count command: {e}")
            await ctx.respond(f"Error resetting player count: {e}", ephemeral=True)

def setup(bot):
    bot.add_cog(AdminBatch(bot))