"""Emerald's Killfeed - Parser Management System
Manage killfeed parsing, log processing, and data collection
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import discord
from discord.ext import commands
from bot.cogs.autocomplete import ServerAutocomplete
from bot.parsers.scalable_historical_parser import ScalableHistoricalParser
from discord import Option

logger = logging.getLogger(__name__)

class Parsers(discord.Cog):
    """
    PARSER MANAGEMENT
    - Killfeed parser controls
    - Log processing management
    - Data collection status
    """

    def __init__(self, bot):
        self.bot = bot
        self.scalable_historical_parser = ScalableHistoricalParser(bot)
    
    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access - unified validation"""
        try:

            pass
            if hasattr(self.bot, 'premium_manager_v2'):
                return await self.bot.premium_manager_v2.has_premium_access(guild_id)
            elif hasattr(self.bot, 'db_manager') and hasattr(self.bot.db_manager, 'has_premium_access'):
                return await self.bot.db_manager.has_premium_access(guild_id)
            else:
                return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Premium access check failed: {e}")
            return False

    # Create subcommand group using SlashCommandGroup
    parser = discord.SlashCommandGroup("parser", "Parser management commands")

    @parser.command(name="status", description="Check parser status")
    async def parser_status(self, ctx: discord.ApplicationContext):
        """Check the status of all parsers"""
        try:

            pass
            embed = discord.Embed(
                title="🔍 Parser Status",
                description="Current status of all data parsers",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc)
            )

            # Killfeed parser status
            killfeed_status = " Active" if hasattr(self.bot, 'killfeed_parser') and self.bot.killfeed_parser else " Inactive"

            # Log parser status
            log_status = " Active" if hasattr(self.bot, 'log_parser') and self.bot.log_parser else " Inactive"

            # Historical parser status
            historical_status = " Active" if hasattr(self.bot, 'historical_parser') and self.bot.historical_parser else " Inactive"

            embed.add_field(
                name="📡 Killfeed Parser",
                value=f"Status: **{killfeed_status}**\nMonitors live PvP events",
                inline=True
            )

            embed.add_field(
                name="📜 Log Parser",
                value=f"Status: **{log_status}**\nProcesses server log files",
                inline=True
            )

            embed.add_field(
                name="📚 Historical Parser",
                value=f"Status: **{historical_status}**\nRefreshes historical data",
                inline=True
            )

            # Scheduler status
            scheduler_status = " Running" if self.bot.scheduler.running else " Stopped"
            embed.add_field(
                name="Background Scheduler",
                value=f"Status: **{scheduler_status}**\nManages automated tasks",
                inline=False
            )

            main_file = discord.File("./assets/main.png", filename="main.png")


            embed.set_thumbnail(url="attachment://main.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed, file=main_file)

        except Exception as e:
            logger.error(f"Failed to check parser status: {e}")
            await ctx.respond("Failed to retrieve parser status.", ephemeral=True)

    @parser.command(name="refresh", description="Manually refresh data for a server")
    @commands.has_permissions(administrator=True)
    @discord.option(
        name="server",
        description="Select a server",
        
    )
    async def parser_refresh(self, ctx: discord.ApplicationContext, server: str = "default"):
        """Manually trigger a data refresh for a server"""
        try:

            pass
            guild_id = ctx.guild.id

            # Check if server exists in guild config - fixed database call
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                await ctx.respond("This guild is not configured!", ephemeral=True)
                return

            # Find the server - now using server ID from autocomplete
            servers = guild_config.get('servers', [])
            server_found = False
            server_name = "Unknown"
            for srv in servers:
                if str(srv.get('_id')) == server:
                    server_found = True
                    server_name = srv.get('name', 'Unknown')
                    break

            if not server_found:
                await ctx.respond(f"Server not found in this guild!", ephemeral=True)
                return

            # Defer response for potentially long operation
            await ctx.defer()

            # Trigger historical refresh with Discord progress updates
            if hasattr(self.bot, 'historical_parser') and self.bot.historical_parser:
                try:

                    pass
                    # Get server config for the historical parser
                    servers = guild_config.get('servers', [])
                    server_config = None
                    for srv in servers:
                        if str(srv.get('_id')) == server:
                            server_config = srv
                            break
                    
                    if server_config:
                        await self.bot.historical_parser.auto_refresh_after_server_add(guild_id, server_config, ctx.channel)
                    else:
                        await self.bot.historical_parser.refresh_historical_data(guild_id, server)

                    embed = discord.Embed(
                        title="🔄 Data Refresh Initiated",
                        description=f"Historical data refresh started for server **{server_name}**",
                        color=0x00FF00,
                        timestamp=datetime.now(timezone.utc)
                    )

                    embed.add_field(
                        name="Duration",
                        value="This process may take several minutes",
                        inline=True
                    )

                    embed.add_field(
                        name="Data Updated",
                        value="• Player statistics\n• Kill/death records\n• Historical trends",
                        inline=True
                    )

                    embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

                    await ctx.followup.send(embed=embed)

                except Exception as e:
                    logger.error(f"Failed to refresh data: {e}")
                    await ctx.followup.send("Failed to start data refresh. Please try again later.")
            else:
                await ctx.followup.send("Historical parser is not available!")

        except Exception as e:
            logger.error(f"Failed to refresh parser data: {e}")
            await ctx.respond("Failed to initiate data refresh.", ephemeral=True)

    @parser.command(name="stats", description="Show parser statistics")
    async def parser_stats(self, ctx: discord.ApplicationContext):
        """Display parser performance statistics"""
        try:

            pass
            guild_id = ctx.guild.id

            embed = discord.Embed(
                title="Parser Statistics",
                description="Performance metrics for data parsers",
                color=0x9B59B6,
                timestamp=datetime.now(timezone.utc)
            )

            # Get recent parsing stats from database - fixed database calls
            try:

                pass
                # Count recent killfeed entries (last 24 hours)
                recent_kills = await self.bot.db_manager.killfeed.count_documents({
                    'guild_id': guild_id,
                    'timestamp': {'$gte': datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
                })

                # Count total players tracked
                total_players = await self.bot.db_manager.pvp_data.count_documents({
                    'guild_id': guild_id
                })

                # Count linked players
                linked_players = await self.bot.db_manager.players.count_documents({
                    'guild_id': guild_id
                })

                embed.add_field(
                    name="Today's Activity",
                    value=f"• Kills Parsed: **{recent_kills}**\n• Players Tracked: **{total_players}**\n• Linked Users: **{linked_players}**",
                    inline=True
                )

                # Parser uptime
                uptime_status = " Operational" if self.bot.scheduler.running else " Down"
                embed.add_field(
                    name="System Health",
                    value=f"• Parser Status: **{uptime_status}**\n• Database: ** Connected**\n• Scheduler: ** Active**",
                    inline=True
                )

            except Exception as e:
                logger.error(f"Failed to get parser stats from database: {e}")
                embed.add_field(
                    name="Statistics",
                    value="Unable to retrieve detailed statistics",
                    inline=False
                )

            main_file = discord.File("./assets/main.png", filename="main.png")


            embed.set_thumbnail(url="attachment://main.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed, file=main_file)

        except Exception as e:
            logger.error(f"Failed to show parser stats: {e}")
            await ctx.respond("Failed to retrieve parser statistics.", ephemeral=True)

    
            # Get parser instance
            if not hasattr(self.bot, 'unified_parser'):
                embed = discord.Embed(
                    title="Parser Not Available",
                    description="The unified log parser is not initialized.",
                    color=0xFF0000
                )
                await ctx.followup.send(embed=embed)
                return

            parser = self.bot.unified_parser

            # Test with sample log data
            sample_logs = [
                "[2024.05.30-09.18.36:173] LogSFPS: Mission GA_Airport_mis_01_SFPSACMission switched to READY",
                "[2024.05.30-09.18.37:174] LogNet: Join request: /Game/Maps/world_1/World_1?eosid=|abc123def456?Name=TestPlayer",
                "[2024.05.30-09.18.38:175] LogOnline: Warning: Player |abc123def456 successfully registered!",
                "[2024.05.30-09.18.39:176] LogSFPS: Mission GA_Military_02_Mis1 switched to IN_PROGRESS",
                "[2024.05.30-09.18.40:177] UChannel::Close: Sending CloseBunch UniqueId: EOS:|abc123def456"
            ]

            test_content = "\n".join(sample_logs[:lines])

            # Parse the test content
            embeds = await parser.parse_log_content(test_content, str(ctx.guild_id), "test_server")

            # Get parser status
            status = parser.get_parser_status()

            # Create response embed
            embed = discord.Embed(
                title="🧪 Log Parser Test Results",
                description=f"Tested with {lines} sample log lines",
                color=0x00AA00
            )

            embed.add_field(
                name="Test Data",
                value=f"```\n{test_content[:500]}{'...' if len(test_content) > 500 else ''}\n```",
                inline=False
            )

            embed.add_field(
                name="Results",
                value=f"**Events Parsed:** {len(embeds)}\n**Parser Status:** Working",
                inline=False
            )

            embed.add_field(
                name="Parser State", 
                value=f"**Active Sessions:** {status['active_sessions']}\n**SFTP Connections:** {status['sftp_connections']}\n**Tracked Servers:** {status['total_tracked_servers']}",
                inline=False
            )

            await ctx.followup.send(embed=embed)

            # Send any generated embeds
            if embeds:
                for event_embed in embeds[:3]:  # Limit to first 3 to avoid spam
                    await ctx.followup.send(embed=event_embed)

                if len(embeds) > 3:
                    await ctx.followup.send(f"... and {len(embeds) - 3} more events")

        except Exception as e:
            logger.error(f"Test log parser error: {e}")
            embed = discord.Embed(
                title="Test Failed",
                description=f"Error testing parser: {str(e)}",
                color=0xFF0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="parser_status", description="Check the status of all parsers")
    @commands.has_permissions(administrator=True)
    async def parser_status(self, ctx: discord.ApplicationContext):
        """Check parser status and player tracking"""
        try:

            pass
            embed = discord.Embed(
                title="Parser Status Report",
                color=0x0099FF
            )

            # Check unified parser
            if hasattr(self.bot, 'unified_parser'):
                parser = self.bot.unified_parser
                status = parser.get_parser_status()

                embed.add_field(
                    name="🔄 Unified Log Parser",
                    value=f"**Status:** Active\n**Active Sessions:** {status['active_sessions']}\n**Tracked Servers:** {status['total_tracked_servers']}\n**SFTP Connections:** {status['sftp_connections']}\n**Connection Status:** {status['connection_status']}",
                    inline=False
                )

                if status['active_players_by_guild']:
                    players_info = "\n".join([f"Guild {guild}: {count} players" for guild, count in status['active_players_by_guild'].items()])
                    embed.add_field(
                        name="👥 Active Players",
                        value=players_info,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🔄 Unified Log Parser",
                    value="Not initialized",
                    inline=False
                )

            # Check killfeed parser
            if hasattr(self.bot, 'killfeed_parser'):
                embed.add_field(
                    name="💀 Killfeed Parser",
                    value="Active",
                    inline=True
                )
            else:
                embed.add_field(
                    name="💀 Killfeed Parser",
                    value="Not initialized",
                    inline=True
                )

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Parser status error: {e}")
            embed = discord.Embed(
                title="Status Check Failed",
                description=f"Error checking parser status: {str(e)}",
                color=0xFF0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="refresh_playercount", description="Reset player counts and trigger immediate cold start")
    @commands.has_permissions(administrator=True)
    async def refresh_playercount(self, ctx: discord.ApplicationContext):
        """Reset player counts and trigger immediate cold start"""
        try:

            pass
            await ctx.defer()

            if not hasattr(self.bot, 'unified_log_parser') or not self.bot.unified_log_parser:
                embed = discord.Embed(
                    title="Parser Not Available",
                    description="The unified log parser is not initialized.",
                    color=0xFF0000
                )
                await ctx.followup.send(embed=embed)
                return

            parser = self.bot.unified_log_parser
            guild_id = ctx.guild.id
            
            # Reset file states (forces cold start)
            if hasattr(parser, 'reset_parser_state'):
                parser.reset_parser_state()
            else:
                # Manual reset if method doesn't exist
                parser.file_states.clear()
                parser.player_sessions.clear()
                parser.player_lifecycle.clear()
                parser.last_log_position.clear()
                if hasattr(parser, 'log_file_hashes'):
                    parser.log_file_hashes.clear()
                if hasattr(parser, 'server_status'):
                    parser.server_status.clear()
            
            # Update voice channels to reflect reset counts (0 players)
            await parser.update_voice_channel(guild_id)

            # Trigger immediate cold start
            try:

                pass
                await parser.run_log_parser()
                
                embed = discord.Embed(
                    title="🔄 Player Count Refresh Complete",
                    description="Player counts have been reset and cold start parsing completed.",
                    color=0x00AA00
                )
                
                embed.add_field(
                    name="Actions Completed",
                    value="• Reset all tracking states\n• Updated voice channel counts\n• Ran cold start parsing\n• Processed current log data",
                    inline=False
                )
                
                embed.add_field(
                    name="Next Scheduled Run",
                    value="Will be a hot start processing only new events",
                    inline=False
                )
                
            except Exception as parse_error:
                logger.error(f"Cold start parsing failed: {parse_error}")
                embed = discord.Embed(
                    title="Partial Success",
                    description="States were reset but cold start parsing failed.",
                    color=0xFFAA00
                )
                
                embed.add_field(
                    name="Completed",
                    value="• Reset all tracking states\n• Updated voice channel counts",
                    inline=False
                )
                
                embed.add_field(
                    name="Failed",
                    value="• Cold start parsing failed\n• Check logs for details",
                    inline=False
                )

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Refresh playercount error: {e}")
            embed = discord.Embed(
                title="Refresh Failed",
                description=f"Error refreshing player count: {str(e)}",
                color=0xFF0000
            )
            await ctx.followup.send(embed=embed)

def setup(bot):
    bot.add_cog(Parsers(bot))