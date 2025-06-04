"""
Emerald's Killfeed - Admin Channel Configuration (REFACTORED - PHASE 4)
Discord channel configuration for server events and notifications
Uses py-cord 2.6.1 syntax with proper error handling
"""

import discord
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class AdminChannels(discord.Cog):
    """Admin channel configuration for event notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("AdminChannels cog initialized")

    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access"""
        try:

            pass
            premium_data = await self.bot.db_manager.premium_guilds.find_one({"guild_id": guild_id})
            return premium_data is not None and premium_data.get("active", False)
        except Exception as e:
            logger.error(f"Error checking premium access: {e}")
            return False

    @discord.slash_command(name="setup_killfeed", description="Configure killfeed channel")
    @discord.default_permissions(administrator=True)
    async def setup_killfeed(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Setup killfeed channel for death notifications"""
        # Immediate defer to prevent Discord timeout
        await ctx.defer()
        
        try:

        
            pass
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            
            # Update channel configuration
            try:

                pass
                await asyncio.wait_for(
                    self.bot.db_manager.channel_configs.update_one(
                        {"guild_id": guild_id},
                        {
                            "$set": {
                                "killfeed_channel_id": channel.id,
                                "last_updated": discord.utils.utcnow()
                            }
                        },
                        upsert=True
                    ),
                    timeout=3.0
                )
                
                embed = discord.Embed(
                    title="✅ Killfeed Channel Configured",
                    description=f"Killfeed notifications will now be sent to {channel.mention}",
                    color=0x00ff00
                )
                await ctx.followup.send(embed=embed)
                
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⚠️ Configuration Failed",
                    description="Database timeout. Please try again.",
                    color=0xFFAA00
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in setup_killfeed command: {e}")
            try:

                pass
                await ctx.followup.send("An error occurred while configuring killfeed channel.", ephemeral=True)
            except:
                pass

    @discord.slash_command(name="setup_events", description="Configure event notifications channel")
    @discord.default_permissions(administrator=True)
    async def setup_events(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        """Setup events channel for mission/helicrash notifications"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:

        
            pass
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            
            # Update channel configuration
            try:

                pass
                await asyncio.wait_for(
                    self.bot.db_manager.channel_configs.update_one(
                        {"guild_id": guild_id},
                        {
                            "$set": {
                                "events_channel_id": channel.id,
                                "last_updated": discord.utils.utcnow()
                            }
                        },
                        upsert=True
                    ),
                    timeout=3.0
                )
                
                embed = discord.Embed(
                    title="✅ Events Channel Configured",
                    description=f"Event notifications will now be sent to {channel.mention}",
                    color=0x00ff00
                )
                await ctx.followup.send(embed=embed)
                
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⚠️ Configuration Failed",
                    description="Database timeout. Please try again.",
                    color=0xFFAA00
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in setup_events command: {e}")
            try:

                pass
                await ctx.followup.send("An error occurred while configuring events channel.", ephemeral=True)
            except:
                pass

    @discord.slash_command(name="setchannel", description="Set channel for specific event types")
    @discord.default_permissions(administrator=True)
    async def setchannel(
        self, 
        ctx: discord.ApplicationContext,
        channel_type: discord.Option(
            str,
            description="Type of channel to set",
            choices=["killfeed", "events", "missions", "helicrash", "airdrop", "trader", "connections", "bounties", "leaderboard", "voice_counter"]
        ),
        channel: discord.Option(discord.abc.GuildChannel, description="Channel to set (text or voice)"),
        server: discord.Option(str, description="Server name (default: 'default')", default="default")
    ):
        """Set channel for specific event types"""
        await ctx.defer()
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            
            # Validate channel type for voice_counter
            if channel_type == "voice_counter" and not isinstance(channel, discord.VoiceChannel):
                embed = discord.Embed(
                    title="❌ Invalid Channel Type",
                    description="Voice counter requires a voice channel. Please select a voice channel.",
                    color=0xFF0000
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            # Update server_channels configuration
            update_field = f"server_channels.{server}.{channel_type}"
            
            await asyncio.wait_for(
                self.bot.db_manager.guild_configs.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            update_field: channel.id,
                            f"server_channels.{server}.{channel_type}_enabled": True,
                            f"server_channels.{server}.{channel_type}_updated": discord.utils.utcnow()
                        }
                    },
                    upsert=True
                ),
                timeout=5.0
            )
            
            embed = discord.Embed(
                title="✅ Channel Configured",
                description=f"{channel_type.title()} notifications for server '{server}' will be sent to {channel.mention}",
                color=0x00ff00
            )
            await ctx.followup.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⚠️ Configuration Failed",
                description="Database timeout. Please try again.",
                color=0xFFAA00
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in setchannel command: {e}")
            await ctx.followup.send("An error occurred while configuring the channel.", ephemeral=True)

    @discord.slash_command(name="view_config", description="View current channel configuration")
    @discord.default_permissions(administrator=True)
    async def view_config(self, ctx: discord.ApplicationContext):
        """View current channel configuration"""
        await ctx.defer()
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            
            # Get guild configuration
            guild_config = await asyncio.wait_for(
                self.bot.db_manager.get_guild(guild_id),
                timeout=3.0
            )
            
            embed = discord.Embed(
                title="🔧 Channel Configuration",
                color=0x00d38a
            )
            
            if guild_config and guild_config.get('server_channels'):
                server_channels = guild_config['server_channels']
                
                for server_name, channels in server_channels.items():
                    server_info = []
                    
                    for channel_type, channel_id in channels.items():
                        if channel_type.endswith('_enabled') or channel_type.endswith('_updated'):
                            continue
                            
                        if isinstance(channel_id, int):
                            discord_channel = ctx.guild.get_channel(channel_id)
                            if discord_channel:
                                server_info.append(f"{channel_type}: {discord_channel.mention}")
                            else:
                                server_info.append(f"{channel_type}: Invalid channel (ID: {channel_id})")
                    
                    if server_info:
                        embed.add_field(
                            name=f"Server: {server_name}",
                            value="\n".join(server_info),
                            inline=False
                        )
            else:
                embed.description = "No channels have been configured yet."
                
            await ctx.followup.send(embed=embed, ephemeral=True)
                
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⚠️ Database Timeout",
                description="Database is currently slow. Please try again.",
                color=0xFFAA00
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in view_config command: {e}")
            await ctx.followup.send("An error occurred while retrieving configuration.", ephemeral=True)

def setup(bot):
    """Load the AdminChannels cog"""
    bot.add_cog(AdminChannels(bot))
    logger.info("AdminChannels cog loaded")
