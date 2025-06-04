import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Linking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="link", description="Link your Discord account to a character")
    async def link(self, ctx: discord.ApplicationContext, character_name: str):
        """Link Discord account to game character"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            user_id = ctx.user.id
            
            # Clean character name
            character_name = character_name.strip()
            if not character_name:
                await ctx.followup.send("Please provide a valid character name!", ephemeral=True)
                return
            
            # Basic linking logic - you can implement database operations here
            embed = discord.Embed(
                title="✅ Character Linked",
                description=f"Successfully linked **{character_name}** to your Discord account",
                color=0x00ff00
            )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in link command: {e}")
            await ctx.followup.send("❌ Failed to link character", ephemeral=True)

    @discord.slash_command(name="unlink", description="Unlink your Discord account")
    async def unlink(self, ctx: discord.ApplicationContext):
        """Unlink Discord account from game character"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="✅ Character Unlinked",
                description="Successfully unlinked your Discord account",
                color=0x00ff00
            )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in unlink command: {e}")
            await ctx.followup.send("❌ Failed to unlink character", ephemeral=True)

    @discord.slash_command(name="whoami", description="Check your linked character")
    async def whoami(self, ctx: discord.ApplicationContext):
        """Check linked character information"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Linked Character",
                description="No character currently linked",
                color=0x0099ff
            )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in whoami command: {e}")
            await ctx.followup.send("❌ Failed to check linked character", ephemeral=True)

def setup(bot):
    bot.add_cog(Linking(bot))
