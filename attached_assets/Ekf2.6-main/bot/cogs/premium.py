import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_premium_server(self, guild_id: int) -> bool:
        """Check if a server has premium access"""
        try:
            # Simple premium check - implement your logic here
            return True  # For now, all servers have access
        except Exception as e:
            logger.error(f"Error checking premium access: {e}")
            return False

    @discord.slash_command(name="premium", description="Check premium status")
    async def premium(self, ctx: discord.ApplicationContext):
        """Check premium status for current server"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            
            # Check premium status
            is_premium = await self.check_premium_server(guild_id)
            
            if is_premium:
                embed = discord.Embed(
                    title="✨ Premium Active",
                    description="This server has premium access to all features",
                    color=0xffd700
                )
            else:
                embed = discord.Embed(
                    title="📦 Standard Access",
                    description="This server has standard access. Upgrade to premium for additional features",
                    color=0x666666
                )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in premium command: {e}")
            await ctx.followup.send("❌ Failed to check premium status", ephemeral=True)

    @discord.slash_command(name="upgrade", description="Information about premium upgrade")
    async def upgrade(self, ctx: discord.ApplicationContext):
        """Show premium upgrade information"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:
            embed = discord.Embed(
                title="✨ Premium Upgrade",
                description="Contact server administrators for premium upgrade information",
                color=0xffd700
            )
            
            embed.add_field(
                name="Premium Features",
                value="• Advanced statistics\n• Priority support\n• Custom configurations",
                inline=False
            )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in upgrade command: {e}")
            await ctx.followup.send("❌ Failed to show upgrade information", ephemeral=True)

def setup(bot):
    bot.add_cog(Premium(bot))
