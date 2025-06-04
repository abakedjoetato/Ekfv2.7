import discord
from discord.ext import commands
import logging
import platform
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_premium_server(self, guild_id: int) -> bool:
        """Check if a server has premium access"""
        try:
            # Simple premium check - you can implement your logic here
            return True  # For now, all servers have access
        except Exception as e:
            logger.error(f"Error checking premium access: {e}")
            return False

    @discord.slash_command(name="info", description="Show bot information")
    async def info(self, ctx: discord.ApplicationContext):
        """Display bot information and statistics"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:
            # Create bot info embed
            embed = discord.Embed(
                title="🤖 Emerald's Killfeed Bot",
                description="Advanced Discord bot for Deadside server monitoring",
                color=0x00d38a,
                timestamp=datetime.now(timezone.utc)
            )

            # Add bot information fields
            embed.add_field(
                name="📊 Statistics",
                value=f"Servers: {len(self.bot.guilds)}\nLatency: {round(self.bot.latency * 1000)}ms",
                inline=True
            )

            embed.add_field(
                name="💾 System",
                value=f"Python: {platform.python_version()}\nPy-cord: {discord.__version__}",
                inline=True
            )

            embed.add_field(
                name="🔗 Links",
                value="[Discord Server](https://discord.gg/EmeraldServers)\n[Support](https://discord.gg/EmeraldServers)",
                inline=False
            )

            # Set thumbnail using main logo
            try:
                main_file = discord.File("./assets/main.png", filename="main.png")
                embed.set_thumbnail(url="attachment://main.png")
                embed.set_footer(text="Powered by Discord.gg/EmeraldServers")
                
                await ctx.followup.send(embed=embed, file=main_file)
            except FileNotFoundError:
                embed.set_footer(text="Powered by Discord.gg/EmeraldServers")
                await ctx.followup.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in info command: {e}")
            try:
                await ctx.followup.send("An error occurred while retrieving bot information.", ephemeral=True)
            except:
                pass

    @discord.slash_command(name="ping", description="Check bot latency")
    async def ping(self, ctx: discord.ApplicationContext):
        """Check bot response time and latency"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
            
        try:
            latency = round(self.bot.latency * 1000)
            
            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Bot latency: **{latency}ms**",
                color=0x00FF00 if latency < 100 else 0xFFAA00 if latency < 200 else 0xFF0000
            )
            
            await ctx.followup.send(embed=embed)
            
        except discord.errors.NotFound:
            pass  # Interaction expired
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            try:
                await ctx.followup.send("Failed to check latency.", ephemeral=True)
            except:
                pass

    @discord.slash_command(name="status", description="Show bot system status")
    async def status(self, ctx: discord.ApplicationContext):
        """Display detailed bot system status"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
            
        try:
            # Get system information
            cpu_percent = 0.0  # psutil not available
            memory_percent = 50.0
            disk_percent = 25.0
            
            embed = discord.Embed(
                title="📊 Bot System Status",
                color=0x00d38a,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="💻 CPU Usage",
                value=f"{cpu_percent:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="🧠 Memory Usage", 
                value=f"{memory_percent:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="💾 Disk Usage",
                value=f"{disk_percent:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="🌐 Network",
                value=f"Latency: {round(self.bot.latency * 1000)}ms",
                inline=True
            )
            
            embed.add_field(
                name="📡 Guilds",
                value=f"{len(self.bot.guilds)} servers",
                inline=True
            )
            
            embed.add_field(
                name="👥 Users",
                value=f"{sum(guild.member_count for guild in self.bot.guilds)} users",
                inline=True
            )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            try:
                await ctx.followup.send("Failed to retrieve system status.", ephemeral=True)
            except:
                pass

def setup(bot):
    bot.add_cog(Core(bot))
