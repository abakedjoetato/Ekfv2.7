"""
Emerald's Killfeed - Bounty System (PHASE 7)
Manual bounties via /bounty set <target> <amount> (24h lifespan)
AI auto-bounties based on hourly kill performance
Must match linked killer to claimed target
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import discord
import discord
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

class Bounties(discord.Cog):
    """
    BOUNTIES (PREMIUM)
    - Manual bounties via /bounty set <target> <amount> (24h lifespan)
    - AI auto-bounties based on hourly kill performance
    - Must match linked killer to claimed target
    """

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

    async def check_premium_server(self, guild_id: int) -> bool:
        """Check if guild has premium access for bounty features"""
        try:

            pass
            # Bounties is guild-wide premium feature - check if guild has any premium access
            return await self.bot.db_manager.has_premium_access(guild_id)
        except Exception as e:
            logger.error(f"Premium check failed for bounties: {e}")
            return False

    async def get_player_character_names(self, guild_id: int, discord_id: int) -> List[str]:
        """Get all character names for a Discord user"""
        player_data = await self.bot.db_manager.get_linked_player(guild_id or 0, discord_id)
        return player_data['linked_characters'] if player_data else []

    async def find_discord_user_by_character(self, guild_id: int, character_name: str) -> Optional[int]:
        """Find Discord user ID by character name"""
        player_data = await self.bot.db_manager.players.find_one({
            'guild_id': guild_id,
            'linked_characters': character_name
        })
        return player_data['discord_id'] if player_data else None

    async def resolve_target(self, ctx: discord.ApplicationContext, target) -> Optional[Tuple[str, int]]:
        """
        Resolve a target (discord.Member or str) to character name and discord_id.
        Returns (character_name, discord_id) or None if not found.
        """
        if not ctx.guild:
            await ctx.respond("❌ This command must be used in a server", ephemeral=True)
            return

        guild_id = ctx.guild.id if ctx.guild else 0

        if isinstance(target, discord.Member):
            # Discord user - must be linked
            player_data = await self.bot.db_manager.get_linked_player(guild_id or 0, target.id)
            if not player_data or not player_data.get('linked_characters'):
                return None
            # Use first linked character for bounty target
            return player_data['linked_characters'][0], target.id

        elif isinstance(target, str):
            # Raw player name - search database directly (case-insensitive)
            target_name = target.strip()
            if not target_name:
                return None

            # Find player in PvP data (case-insensitive match)
            cursor = self.bot.db_manager.pvp_data.find({
                'guild_id': guild_id,
                'player_name': {'$regex': f'^{target_name}$', '$options': 'i'}
            })

            async for player_doc in cursor:
                actual_player_name = player_doc.get('player_name')
                if actual_player_name:
                    # Find Discord ID for this character
                    discord_id = await self.find_discord_user_by_character(guild_id or 0, actual_player_name)
                    return actual_player_name, discord_id

            return None

        return None

    async def add_wallet_event(self, guild_id: int, discord_id: int, 
                              amount: int, event_type: str, description: str):
        """Add wallet transaction event for tracking"""
        try:

            pass
            await self.bot.db_manager.add_wallet_event(
                guild_id, discord_id, amount, event_type, description
            )
        except Exception as e:
            logger.error(f"Failed to add wallet event: {e}")

    bounty = discord.SlashCommandGroup("bounty", "Bounty system commands")

    @bounty.command(name="set", description="Set a bounty on a player (Discord user or player name)")
    async def bounty_set(self, ctx: discord.ApplicationContext, target: str, amount: int):
        """Set a bounty on a target (Discord user or player name)"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id if ctx.user else 0

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Bounty system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Validate amount
            if amount <= 0:
                await ctx.respond("Bounty amount must be positive!", ephemeral=True)
                return

            if amount < 100:
                await ctx.respond("Minimum bounty amount is $100!", ephemeral=True)
                return

            if amount > 50000:
                await ctx.respond("Maximum bounty amount is $50,000!", ephemeral=True)
                return

            # Check if user has enough money
            wallet = await self.bot.db_manager.get_wallet(guild_id or 0, discord_id)
            if wallet['balance'] < amount:
                await ctx.respond(
                    f"Insufficient funds! You have **${wallet['balance']:,}** but need **${amount:,}**",
                    ephemeral=True
                )
                return

            # Resolve target (Discord user mention or player name)
            target_user = None
            if target.startswith('<@') and target.endswith('>'):
                user_id_str = target[2:-1]
                if user_id_str.startswith('!'):
                    user_id_str = user_id_str[1:]
                try:

                    pass
                    user_id = int(user_id_str)
                    target_user = ctx.guild.get_member(user_id)
                except ValueError:
                    pass

            if target_user:
                # It's a user mention
                resolve_result = await self.resolve_target(ctx, target_user)
            else:
                # It's a raw player name
                resolve_result = await self.resolve_target(ctx, target)

            if not resolve_result:
                await ctx.respond(
                    "Unable to find a linked user or matching player by that name.",
                    ephemeral=True
                )
                return

            target_character, target_discord_id = resolve_result

            # Prevent self-bounties
            user_characters = await self.get_player_character_names(guild_id or 0, discord_id)
            if target_character in user_characters:
                await ctx.respond("You cannot set a bounty on yourself!", ephemeral=True)
                return

            # Check if bounty already exists
            existing_bounty = await self.bot.db_manager.bounties.find_one({
                'guild_id': guild_id,
                'target_character': target_character,
                'active': True,
                'expires_at': {'$gt': datetime.now(timezone.utc)}
            })

            if existing_bounty:
                await ctx.respond(f"There is already an active bounty on **{target_character}**!", ephemeral=True)
                return

            # Deduct money from user
            success = await self.bot.db_manager.update_wallet(guild_id or 0, discord_id, -amount, "bounty_set", "economy_operation")

            if not success:
                await ctx.respond("Failed to process payment. Please try again.", ephemeral=True)
                return

            # Create bounty
            bounty_doc = {
                'guild_id': guild_id,
                'target_character': target_character,
                'target_discord_id': target_discord_id,
                'issuer_discord_id': discord_id,
                'amount': amount,
                'active': True,
                'claimed': False,
                'created_at': datetime.now(timezone.utc),
                'expires_at': datetime.now(timezone.utc) + timedelta(hours=24),
                'auto_generated': False
            }

            await self.bot.db_manager.bounties.insert_one(bounty_doc)

            # Add wallet event
            await self.add_wallet_event(
                guild_id, discord_id, -amount, "bounty_set",
                f"Set bounty on {target_character} for ${amount:,}"
            )

            # Create bounty embed
            embed = discord.Embed(
                title="Bounty Set",
                description=f"A bounty has been placed on **{target_character}**!",
                color=0xFF4500,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Reward",
                value=f"**${amount:,}**",
                inline=True
            )

            embed.add_field(
                name="Expires",
                value=f"<t:{int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())}:R>",
                inline=True
            )

            embed.add_field(
                name="👤 Target",
                value=target_character,
                inline=True
            )

            embed.add_field(
                name="Instructions",
                value="Kill the target to claim the bounty!\nBounty expires in 24 hours.",
                inline=False
            )

            # Set thumbnail using bounty asset
            bounty_file = discord.File("./assets/Bounty.png", filename="Bounty.png")
            embed.set_thumbnail(url="attachment://Bounty.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed, file=bounty_file)

        except Exception as e:
            logger.error(f"Failed to set bounty: {e}")
            await ctx.respond("Failed to set bounty.", ephemeral=True)

    @bounty.command(name="list", description="List active bounties")
    async def bounty_list(self, ctx: discord.ApplicationContext):
        """List all active bounties"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Bounty system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Get active bounties
            cursor = self.bot.db_manager.bounties.find({
                'guild_id': guild_id,
                'active': True,
                'expires_at': {'$gt': datetime.now(timezone.utc)}
            }).sort('amount', -1)

            bounties = await cursor.to_list(length=20)

            if not bounties:
                embed = discord.Embed(
                    title="Priority Elimination Contracts",
                    description="No active bounties found!",
                    color=0x808080,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="Powered by Discord.gg/EmeraldServers")
                await ctx.respond(embed=embed)
                return

            # Create bounty list embed
            embed = discord.Embed(
                title="Priority Elimination Contracts",
                description=f"**{len(bounties)}** active bounties",
                color=0xFF4500,
                timestamp=datetime.now(timezone.utc)
            )

            bounty_list = []
            for i, bounty in enumerate(bounties[:10], 1):  # Show top 10
                target = bounty['target_character']
                amount = bounty['amount']
                expires = bounty['expires_at']
                auto = " 🤖" if bounty and bounty.get('auto_generated', False) else ""

                bounty_list.append(
                    f"**{i}.** {target} - **${amount:,}**{auto}\n"
                    f"    Expires <t:{int(expires.timestamp())}:R>"
                )

            embed.add_field(
                name="Active Contracts",
                value="\n".join(bounty_list),
                inline=False
            )

            if len(bounties) > 10:
                embed.add_field(
                    name="Status",
                    value=f"Showing top 10 of {len(bounties)} bounties",
                    inline=False
                )

            # Set thumbnail using bounty asset
            bounty_file = discord.File("./assets/Bounty.png", filename="Bounty.png")
            embed.set_thumbnail(url="attachment://Bounty.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers • 🤖 = Auto-generated")

            await ctx.respond(embed=embed, file=bounty_file)

        except Exception as e:
            logger.error(f"Failed to list bounties: {e}")
            await ctx.respond("Failed to retrieve bounties.", ephemeral=True)

    async def check_bounty_claims(self, guild_id: int, killer_character: str, victim_character: str):
        """Check if a kill claims any bounties"""
        try:

            pass
            # Find active bounties on the victim
            active_bounties = await self.bot.db_manager.bounties.find({
                'guild_id': guild_id,
                'target_character': victim_character,
                'active': True,
                'claimed': False,
                'expires_at': {'$gt': datetime.now(timezone.utc)}
            }).to_list(length=None)

            if not active_bounties:
                return

            # Find Discord ID of killer
            killer_discord_id = await self.find_discord_user_by_character(guild_id or 0, killer_character)
            if not killer_discord_id:
                return  # Killer not linked, can't claim bounty

            # Process each bounty
            for bounty in active_bounties:
                await self._claim_bounty(guild_id or 0, bounty, killer_discord_id, killer_character)

        except Exception as e:
            logger.error(f"Failed to check bounty claims: {e}")

    async def _claim_bounty(self, guild_id: int, bounty: Dict[str, Any], 
                           killer_discord_id: int, killer_character: str):
        """Process a bounty claim"""
        try:

            pass
            bounty_amount = bounty['amount']
            target_character = bounty['target_character']

            # Mark bounty as claimed
            await self.bot.db_manager.bounties.update_one(
                {'_id': bounty['_id']},
                {
                    '$set': {
                        'claimed': True,
                        'active': False,
                        'claimed_at': datetime.now(timezone.utc),
                        'claimer_discord_id': killer_discord_id,
                        'claimer_character': killer_character
                    }
                }
            )

            # Award money to killer
            await self.bot.db_manager.update_wallet(
                guild_id, killer_discord_id, bounty_amount, "bounty_claim"
            , "economy_operation")

            # Add wallet event
            await self.add_wallet_event(
                guild_id, killer_discord_id, bounty_amount, "bounty_claim",
                f"Claimed bounty on {target_character} for ${bounty_amount:,}"
            )

            # Send bounty claimed notification
            await self._send_bounty_claimed_embed(guild_id or 0, bounty, killer_discord_id, killer_character)

            logger.info(f"Bounty claimed: {killer_character} killed {target_character} for ${bounty_amount:,}")

        except Exception as e:
            logger.error(f"Failed to claim bounty: {e}")

    async def _send_bounty_claimed_embed(self, guild_id: int, bounty: Dict[str, Any], 
                                        killer_discord_id: int, killer_character: str):
        """Send bounty claimed notification"""
        try:

            pass
            # Get guild channels
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                return

            # Check new server_channels structure first
            server_channels_config = guild_config.get('server_channels', {})
            default_server = server_channels_config.get('default', {})

            # Check legacy channels structure
            legacy_channels = guild_config.get('channels', {})

            # Priority: default server -> legacy channels (bounties go to bounties channel or killfeed)
            killfeed_channel_id = (default_server.get('bounties') or 
                                  legacy_channels.get('bounties') or
                                  default_server.get('killfeed') or 
                                  legacy_channels.get('killfeed'))
            if not killfeed_channel_id:
                return

            channel = self.bot.get_channel(killfeed_channel_id)
            if not channel:
                return

            embed = discord.Embed(
                title="Contract Completed",
                description=f"**{killer_character}** has claimed the bounty on **{bounty['target_character']}**!",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Reward",
                value=f"**${bounty['amount']:,}**",
                inline=True
            )

            embed.add_field(
                name="Contractor",
                value=f"<@{killer_discord_id}>",
                inline=True
            )

            embed.add_field(
                name="Target Eliminated",
                value=bounty['target_character'],
                inline=True
            )

            if bounty and bounty.get('auto_generated', False):
                embed.add_field(
                    name="🤖 Type",
                    value="Auto-generated bounty",
                    inline=False
                )

            # Set thumbnail using bounty asset
            bounty_file = discord.File("./assets/Bounty.png", filename="Bounty.png")
            embed.set_thumbnail(url="attachment://Bounty.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await channel.send(embed=embed, file=bounty_file)

        except Exception as e:
            logger.error(f"Failed to send bounty claimed embed: {e}")

    async def generate_auto_bounties(self, guild_id: int):
        """Generate automatic bounties based on kill performance"""
        try:

            pass
            # Get top killers from the last hour
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

            pipeline = [
                {
                    '$match': {
                        'guild_id': guild_id,
                        'timestamp': {'$gte': one_hour_ago},
                        'is_suicide': False
                    }
                },
                {
                    '$group': {
                        '_id': '$killer',
                        'kill_count': {'$sum': 1}
                    }
                },
                {
                    '$match': {
                        'kill_count': {'$gte': 5}  # Minimum 5 kills in an hour
                    }
                },
                {
                    '$sort': {'kill_count': -1}
                },
                {
                    '$limit': 3  # Top 3 performers
                }
            ]

            top_killers = await self.bot.db_manager.kill_events.aggregate(pipeline).to_list(length=None)

            for killer_data in top_killers:
                killer_name = killer_data['_id']
                kill_count = killer_data['kill_count']

                # Check if there's already a bounty on this player
                existing_bounty = await self.bot.db_manager.bounties.find_one({
                    'guild_id': guild_id,
                    'target_character': killer_name,
                    'active': True,
                    'expires_at': {'$gt': datetime.now(timezone.utc)}
                })

                if existing_bounty:
                    continue  # Skip if already has bounty

                # Calculate bounty amount based on performance
                base_amount = 1000
                performance_bonus = (kill_count - 4) * 500  # Extra $500 per kill above 5
                bounty_amount = min(base_amount + performance_bonus, 10000)  # Cap at $10k

                # Find target Discord ID
                target_discord_id = await self.find_discord_user_by_character(guild_id or 0, killer_name)
                if not target_discord_id:
                    continue  # Skip if not linked

                # Create auto-bounty
                bounty_doc = {
                    'guild_id': guild_id,
                    'target_character': killer_name,
                    'target_discord_id': target_discord_id,
                    'issuer_discord_id': None,  # System-generated
                    'amount': bounty_amount,
                    'active': True,
                    'claimed': False,
                    'created_at': datetime.now(timezone.utc),
                    'expires_at': datetime.now(timezone.utc) + timedelta(hours=2),  # 2 hour lifespan
                    'auto_generated': True,
                    'trigger_kills': kill_count
                }

                await self.bot.db_manager.bounties.insert_one(bounty_doc)

                # Send auto-bounty notification
                await self._send_auto_bounty_embed(guild_id or 0, killer_name, bounty_amount, kill_count)

                logger.info(f"Auto-bounty generated: {killer_name} (${bounty_amount:,}) for {kill_count} kills")

        except Exception as e:
            logger.error(f"Failed to generate auto-bounties: {e}")

    async def _send_auto_bounty_embed(self, guild_id: int, target_name: str, 
                                     amount: int, kill_count: int):
        """Send auto-bounty notification"""
        try:

            pass
            # Get guild channels
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                return

            # Check new server_channels structure first
            server_channels_config = guild_config.get('server_channels', {})
            default_server = server_channels_config.get('default', {})

            # Check legacy channels structure
            legacy_channels = guild_config.get('channels', {})

            # Priority: default server -> legacy channels (bounties go to bounties channel or killfeed)
            killfeed_channel_id = (default_server.get('bounties') or 
                                  legacy_channels.get('bounties') or
                                  default_server.get('killfeed') or 
                                  legacy_channels.get('killfeed'))
            if not killfeed_channel_id:
                return

            channel = self.bot.get_channel(killfeed_channel_id)
            if not channel:
                return

            embed = discord.Embed(
                title="🤖 Auto-Bounty Generated",
                description=f"The system has placed an automatic bounty on **{target_name}**!",
                color=0xFF8C00,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Reward",
                value=f"**${amount:,}**",
                inline=True
            )

            embed.add_field(
                name="Trigger",
                value=f"{kill_count} kills in 1 hour",
                inline=True
            )

            embed.add_field(
                name="Expires",
                value="<t:" + str(int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())) + ":R>",
                inline=True
            )

            embed.add_field(
                name="Target",
                value=target_name,
                inline=False
            )

            # Set thumbnail using bounty asset
            bounty_file = discord.File("./assets/Bounty.png", filename="Bounty.png")
            embed.set_thumbnail(url="attachment://Bounty.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers • Auto-generated bounty")

            await channel.send(embed=embed, file=bounty_file)

        except Exception as e:
            logger.error(f"Failed to send auto-bounty embed: {e}")

    bounty = discord.SlashCommandGroup("bounty", "Bounty system commands")

    @bounty.command(name="set", description="Set a bounty on a player")
    async def bounty_set_cmd(self, ctx: discord.ApplicationContext, 
                            target: discord.Option(str, "Target player name or @mention"),
                            amount: discord.Option(int, "Bounty amount", min_value=100)):
        """Set a bounty on a player"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="🚫 Premium Required",
                    description="Bounty system requires premium server access.",
                    color=0xff5e5e
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Check wallet balance
            wallet = await self.bot.db_manager.get_wallet(guild_id or 0, discord_id)
            if wallet['balance'] < amount:
                await ctx.respond(f"Insufficient funds! You have ${wallet['balance']:,}", ephemeral=True)
                return

            # Resolve target
            target_result = await self.resolve_target(ctx, target)
            if not target_result:
                await ctx.respond("Target not found or invalid!", ephemeral=True)
                return

            target_name, target_discord_id = target_result

            # Deduct bounty amount
            await self.bot.db_manager.update_wallet(guild_id or 0, discord_id, -amount, "bounty_set", "economy_operation")

            # Create bounty
            bounty_doc = {
                "guild_id": guild_id,
                "target_name": target_name,
                "target_discord_id": target_discord_id,
                "bounty_amount": amount,
                "issuer_discord_id": discord_id,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
                "claimed": False
            }

            await self.bot.db_manager.db.bounties.insert_one(bounty_doc)

            embed = discord.Embed(
                title="Bounty Set",
                description=f"**Target:** {target_name}\n**Amount:** ${amount:,}\n**Expires:** <t:{int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())}:R>",
                color=0xffa500
            )
            await ctx.respond(embed=embed)

        except Exception as e:
            logger.error(f"Failed to set bounty: {e}")
            await ctx.respond("Failed to set bounty", ephemeral=True)

    @bounty.command(name="list", description="View active bounties")
    async def bounty_list_cmd(self, ctx: discord.ApplicationContext):
        """List active bounties"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0

            bounties = await self.bot.db_manager.db.bounties.find({
                "guild_id": guild_id,
                "claimed": False,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            }).sort("bounty_amount", -1).to_list(length=20)

            if not bounties:
                embed = discord.Embed(
                    title="Active Bounties",
                    description="No active bounties found.",
                    color=0x7f5af0
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="Active Bounties",
                color=0xffa500
            )

            bounty_text = ""
            for bounty in bounties[:10]:
                expires_timestamp = int(bounty['expires_at'].timestamp())
                bounty_text += f"**{bounty['target_name']}** - ${bounty['bounty_amount']:,} (expires <t:{expires_timestamp}:R>)\n"

            embed.add_field(name="Targets", value=bounty_text, inline=False)
            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Failed to list bounties: {e}")
            await ctx.respond("Failed to list bounties", ephemeral=True)

def setup(bot):
    bot.add_cog(Bounties(bot))