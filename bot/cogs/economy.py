import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="balance", description="Check your account balance")
    async def balance(self, ctx: discord.ApplicationContext):
        """Check user's account balance"""
        await ctx.defer()

        try:
            if not ctx.guild:
                await ctx.followup.send("❌ This command must be used in a server", ephemeral=True)
                return

            user_id = ctx.user.id
            guild_id = ctx.guild.id

            # Basic balance check - implement your database logic here
            balance = 1000  # Default balance

            embed = discord.Embed(
                title="💰 Account Balance",
                description=f"Your current balance: **{balance:,}** credits",
                color=0x00ff00
            )

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in balance command: {e}")
            await ctx.followup.send("❌ Failed to check balance", ephemeral=True)

    @discord.slash_command(name="pay", description="Send credits to another user")
    async def pay(self, ctx: discord.ApplicationContext, user: discord.Member, amount: int):
        """Send credits to another user"""
        await ctx.defer()

        try:
            if not ctx.guild:
                await ctx.followup.send("❌ This command must be used in a server", ephemeral=True)
                return

            if amount <= 0:
                await ctx.followup.send("❌ Amount must be positive", ephemeral=True)
                return

            if user.id == ctx.user.id:
                await ctx.followup.send("❌ You cannot send credits to yourself", ephemeral=True)
                return

            # Basic payment logic - implement your database operations here
            embed = discord.Embed(
                title="✅ Payment Sent",
                description=f"Successfully sent **{amount:,}** credits to {user.mention}",
                color=0x00ff00
            )

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in pay command: {e}")
            await ctx.followup.send("❌ Failed to send payment", ephemeral=True)

    @discord.slash_command(name="credits", description="Show top users by credits")
    async def credits(self, ctx: discord.ApplicationContext):
        """Show credit leaderboard"""
        await ctx.defer()

        try:
            if not ctx.guild:
                await ctx.followup.send("❌ This command must be used in a server", ephemeral=True)
                return

            embed = discord.Embed(
                title="🏆 Credit Leaderboard",
                description="Top users by credits",
                color=0xffd700
            )

            # Basic leaderboard - implement your database logic here
            embed.add_field(
                name="📊 Leaderboard",
                value="No data available",
                inline=False
            )

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in credits command: {e}")
            await ctx.followup.send("❌ Failed to show leaderboard", ephemeral=True)

def setup(bot):
    bot.add_cog(Economy(bot))