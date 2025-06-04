"""
The diff contains changes that remove emojis and use EmbedFactory for faction embeds, updating title and description for premium feature check.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import discord
from discord.ext import commands
from bot.utils.embed_factory import EmbedFactory

logger = logging.getLogger(__name__)

class Factions(discord.Cog):
    """
    FACTIONS (PREMIUM)
    - /faction create, /invite, /join, /stats, etc.
    - Guild-isolated
    - Stats combine linked users
    """

    def __init__(self, bot):
        self.bot = bot

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
            logger.error(f"Premium access check failed: {e}")
            return False

    async def check_premium_server(self, guild_id: int) -> bool:
        """Check if guild has premium access for faction features"""
        try:

            pass
            # Factions is guild-wide premium feature - check if guild has any premium access
            return await self.bot.db_manager.has_premium_access(guild_id)
        except Exception as e:
            logger.error(f"Premium check failed for factions: {e}")
            return False

    async def get_user_faction(self, guild_id: int, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get the faction a user belongs to"""
        return await self.bot.db_manager.factions.find_one({
            'guild_id': guild_id,
            'members': discord_id
        })

    async def generate_faction_stats(self, guild_id: int, member_ids: List[int]) -> Dict[str, Any]:
        """Generate combined stats for faction members using correct data structure"""
        try:

            pass
            total_kills = 0
            total_deaths = 0
            total_distance = 0.0

            for member_id in member_ids:
                # Get linked player names for this Discord user
                user_link = await self.bot.db_manager.user_links.find_one({
                    'guild_id': guild_id,
                    'discord_id': member_id
                })

                if user_link:
                    player_names = user_link.get('player_names', [])

                    # Get stats from pvp_data for each linked player name
                    for player_name in player_names:
                        cursor = self.bot.db_manager.pvp_data.find({
                            'guild_id': guild_id,
                            'player_name': player_name
                        })

                        async for player_stats in cursor:
                            total_kills += player_stats.get('kills', 0)
                            total_deaths += player_stats.get('deaths', 0)
                            total_distance += player_stats.get('total_distance', 0.0)

            # Calculate K/D ratio
            kdr = total_kills / total_deaths if total_deaths > 0 else total_kills

            return {
                'total_kills': total_kills,
                'total_deaths': total_deaths,
                'total_distance': total_distance,
                'kdr': kdr
            }
        except Exception as e:
            logger.error(f"Failed to generate faction stats: {e}")
            return {
                'total_kills': 0,
                'total_deaths': 0,
                'total_distance': 0.0,
                'kdr': 0.0
            }

    async def autocomplete_faction_name(self, ctx: discord.AutocompleteContext):
        """Autocomplete callback for faction names"""
        try:

            pass
            guild_id = ctx.interaction.guild_id

            # Get all factions for this guild
            cursor = self.bot.db_manager.factions.find({'guild_id': guild_id}).sort('faction_name', 1)
            factions = await cursor.to_list(length=25)  # Limit to 25 for autocomplete

            # Return faction names for autocomplete
            return [
                discord.OptionChoice(
                    name=faction['faction_name'],
                    value=faction['faction_name']
                )
                for faction in factions
            ]

        except Exception as e:
            logger.error(f"Autocomplete error: {e}")
            return [discord.OptionChoice(name="Error loading factions", value="none")]

    async def calculate_faction_stats(self, guild_id: int, faction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate combined stats for all faction members"""
        try:

            pass
            combined_stats = {
                'total_kills': 0,
                'total_deaths': 0,
                'total_suicides': 0,
                'total_kdr': 0.0,
                'member_count': len(faction_data['members']),
                'best_streak': 0,
                'total_distance': 0.0
            }

            # Get stats for all members
            for member_id in faction_data['members']:
                # Get member's linked characters
                player_data = await self.bot.db_manager.get_linked_player(guild_id or 0, member_id)
                if not player_data:
                    continue

                # Get stats for each character across all servers
                for character in player_data['linked_characters']:
                    cursor = self.bot.db_manager.pvp_data.find({
                        'guild_id': guild_id,
                        'player_name': character
                    })

                    async for server_stats in cursor:
                        combined_stats['total_kills'] += server_stats.get('kills', 0)
                        combined_stats['total_deaths'] += server_stats.get('deaths', 0)
                        combined_stats['total_suicides'] += server_stats.get('suicides', 0)
                        combined_stats['total_distance'] += server_stats.get('total_distance', 0.0)

                        if server_stats and server_stats.get('longest_streak', 0) > combined_stats['best_streak']:
                            combined_stats['best_streak'] = server_stats.get('longest_streak', 0)

            # Calculate faction KDR safely
            if combined_stats['total_deaths'] > 0:
                combined_stats['total_kdr'] = combined_stats['total_kills'] / combined_stats['total_deaths']
            else:
                combined_stats['total_kdr'] = float(combined_stats['total_kills'])

            return combined_stats

        except Exception as e:
            logger.error(f"Failed to calculate faction stats: {e}")
            return {
                'kills': 0,
                'deaths': 0,
                'kdr': 0.0,
                'assists': 0,
                'captures': 0,
                'game_time': 0
            }

    faction = discord.SlashCommandGroup("faction", "Faction management commands")

    @faction.command(name="create", description="Create a new faction")
    async def faction_create(self, ctx: discord.ApplicationContext, name: str, tag: str = ""):
        """Create a new faction"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Validate faction name
            name = name.strip()
            if not name:
                await ctx.respond("Faction name cannot be empty!", ephemeral=True)
                return

            if len(name) > 32:
                await ctx.respond("Faction name too long! Maximum 32 characters.", ephemeral=True)
                return

            # Validate tag
            if tag:
                tag = tag.strip().upper()
                if len(tag) > 6:
                    await ctx.respond("Faction tag too long! Maximum 6 characters.", ephemeral=True)
                    return

            # Check if user is already in a faction
            existing_faction = await self.get_user_faction(guild_id or 0, discord_id)
            if existing_faction:
                await ctx.respond(
                    f"You are already a member of **{existing_faction['faction_name']}**!",
                    ephemeral=True
                )
                return

            # Check if faction name already exists
            existing_name = await self.bot.db_manager.factions.find_one({
                'guild_id': guild_id,
                'faction_name': name
            })

            if existing_name:
                await ctx.respond(f"Faction name **{name}** is already taken!", ephemeral=True)
                return

            # Check if tag already exists
            if tag:
                existing_tag = await self.bot.db_manager.factions.find_one({
                    'guild_id': guild_id,
                    'faction_tag': tag
                })

                if existing_tag:
                    await ctx.respond(f"Faction tag **[{tag}]** is already taken!", ephemeral=True)
                    return

            # Create faction with consistent timezone handling
            current_time = datetime.now(timezone.utc)
            faction_doc = {
                'guild_id': guild_id,
                'faction_name': name,
                'faction_tag': tag,
                'leader_id': discord_id,
                'members': [discord_id],
                'officers': [],
                'created_at': current_time,
                'last_updated': current_time,
                'description': None,
                'invite_only': False,
                'max_members': 20
            }

            await self.bot.db_manager.factions.insert_one(faction_doc)

            # Create success embed
            # Create faction created embed
            embed, file_attachment = await EmbedFactory.build_faction_created_embed({
                'faction_name': name,
                'leader': ctx.user.display_name,
                'faction_tag': tag,
                'member_count': 1,
                'max_members': 10
            })

            await ctx.respond(embed=embed, file=file_attachment)

        except Exception as e:
            logger.error(f"Failed to create faction: {e}")
            await ctx.respond("Failed to create faction.", ephemeral=True)

    @faction.command(name="invite", description="Invite a user to your faction")
    async def faction_invite(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Invite a user to join your faction"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Check if inviter is in a faction and has permission
            inviter_faction = await self.get_user_faction(guild_id or 0, discord_id)
            if not inviter_faction:
                await ctx.respond("You are not a member of any faction!", ephemeral=True)
                return

            # Check permissions (leader or officer)
            if (discord_id != inviter_faction['leader_id'] and 
                discord_id not in inviter_faction.get('officers', [])):
                await ctx.respond("Only faction leaders and officers can invite members!", ephemeral=True)
                return

            # Check if target user is already in a faction
            target_faction = await self.get_user_faction(guild_id or 0, user.id)
            if target_faction:
                await ctx.respond(
                    f"{user.mention} is already a member of **{target_faction['faction_name']}**!",
                    ephemeral=True
                )
                return

            # Check if faction is full
            if len(inviter_faction['members']) >= inviter_faction.get('max_members', 20):
                await ctx.respond("Your faction is at maximum capacity!", ephemeral=True)
                return

            # Send invitation embed
            embed = discord.Embed(
                title="🏛️ Faction Invitation",
                description=f"{user.mention}, you've been invited to join **{inviter_faction['faction_name']}**!",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="👑 Invited by",
                value=ctx.user.mention,
                inline=True
            )

            if inviter_faction and inviter_faction.get('faction_tag'):
                embed.add_field(
                    name="🏷️ Tag",
                    value=f"[{inviter_faction['faction_tag']}]",
                    inline=True
                )

            embed.add_field(
                name="👥 Current Members",
                value=f"{len(inviter_faction['members'])}/{inviter_faction.get('max_members', 20)}",
                inline=True
            )

            if inviter_faction and inviter_faction.get('description'):
                embed.add_field(
                    name="Description",
                    value=inviter_faction['description'],
                    inline=False
                )

            embed.add_field(
                name="Action Required",
                value="Use `/faction join` to accept this invitation!",
                inline=False
            )

            faction_file = discord.File("./assets/Faction.png", filename="Faction.png")
            embed.set_thumbnail(url="attachment://Faction.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed, file=faction_file)

        except Exception as e:
            logger.error(f"Failed to send faction invite: {e}")
            await ctx.respond("Failed to send faction invite.", ephemeral=True)

    @faction.command(name="join", description="Join a faction")
    @discord.option(
        name="faction_name",
        description="Name of the faction to join",
        autocomplete=autocomplete_faction_name
    )
    async def faction_join(self, ctx: discord.ApplicationContext, faction_name: str):
        """Join a faction by name"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Check if user is already in a faction
            existing_faction = await self.get_user_faction(guild_id or 0, discord_id)
            if existing_faction:
                await ctx.respond(
                    f"You are already a member of **{existing_faction['faction_name']}**!",
                    ephemeral=True
                )
                return

            # Find the faction
            faction = await self.bot.db_manager.factions.find_one({
                'guild_id': guild_id,
                'faction_name': faction_name.strip()
            })

            if not faction:
                await ctx.respond(f"Faction **{faction_name}** not found!", ephemeral=True)
                return

            # Check if faction is full
            if len(faction['members']) >= faction.get('max_members', 20):
                await ctx.respond("This faction is at maximum capacity!", ephemeral=True)
                return

            # Check if faction is invite-only
            if faction and faction.get('invite_only', False):
                await ctx.respond("This faction is invite-only! Ask a member to invite you.", ephemeral=True)
                return

            # Add user to faction
            await self.bot.db_manager.factions.update_one(
                {'_id': faction['_id']},
                {'$addToSet': {'members': discord_id}}
            )

            # Create success embed
            embed = discord.Embed(
                title="🎉 Joined Faction",
                description=f"Welcome to **{faction['faction_name']}**!",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc)
            )

            if faction and faction.get('faction_tag'):
                embed.add_field(
                    name="🏷️ Your Tag",
                    value=f"[{faction['faction_tag']}]",
                    inline=True
                )

            embed.add_field(
                name="👥 Members",
                value=f"{len(faction['members']) + 1}/{faction.get('max_members', 20)}",
                inline=True
            )

            # Get leader info
            leader = await self.bot.fetch_user(faction['leader_id'])
            embed.add_field(
                name="👑 Leader",
                value=leader.mention if leader else "Unknown",
                inline=True
            )

            faction_file = discord.File("./assets/Faction.png", filename="Faction.png")
            embed.set_thumbnail(url="attachment://Faction.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed, file=faction_file)

        except Exception as e:
            logger.error(f"Failed to join faction: {e}")
            await ctx.respond("Failed to join faction.", ephemeral=True)

    @faction.command(name="leave", description="Leave your current faction")
    async def faction_leave(self, ctx: discord.ApplicationContext):
        """Leave your current faction"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Check if user is in a faction
            faction = await self.get_user_faction(guild_id or 0, discord_id)
            if not faction:
                await ctx.respond("You are not a member of any faction!", ephemeral=True)
                return

            # Check if user is the leader
            if discord_id == faction['leader_id']:
                if len(faction['members']) > 1:
                    await ctx.respond(
                        "As the leader, you must transfer leadership or disband the faction before leaving!",
                        ephemeral=True
                    )
                    return
                else:
                    # Last member, delete faction
                    await self.bot.db_manager.factions.delete_one({'_id': faction['_id']})

                    embed = discord.Embed(
                        title="🏛️ Faction Disbanded",
                        description=f"**{faction['faction_name']}** has been disbanded.",
                        color=0xFF6B6B,
                        timestamp=datetime.now(timezone.utc)
                    )
                    embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

                    await ctx.respond(embed=embed)
                    return

            # Remove user from faction
            await self.bot.db_manager.factions.update_one(
                {'_id': faction['_id']},
                {
                    '$pull': {'members': discord_id, 'officers': discord_id}
                }
            )

            # Create leave embed
            embed = discord.Embed(
                title="👋 Left Faction",
                description=f"You have left **{faction['faction_name']}**.",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed)

        except Exception as e:
            logger.error(f"Failed to leave faction: {e}")
            await ctx.respond("Failed to leave faction.", ephemeral=True)

    @faction.command(name="info", description="View faction information")
    @discord.option(
        name="faction_name",
        description="Name of the faction to view (leave empty for your own faction)",
        required=False,
        autocomplete=autocomplete_faction_name
    )
    async def faction_info(self, ctx: discord.ApplicationContext, faction_name: str = ""):
        """View detailed information about a faction"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Determine which faction to show
            if faction_name:
                faction = await self.bot.db_manager.factions.find_one({
                    'guild_id': guild_id,
                    'faction_name': faction_name.strip()
                })
                if not faction:
                    await ctx.respond(f"Faction **{faction_name}** not found!", ephemeral=True)
                    return
            else:
                faction = await self.get_user_faction(guild_id or 0, discord_id)
                if not faction:
                    await ctx.respond("You are not a member of any faction! Specify a faction name to view.", ephemeral=True)
                    return

            await ctx.defer()

            # Calculate faction stats
            stats = await self.calculate_faction_stats(guild_id or 0, faction)

            # Create info embed
            embed = discord.Embed(
                title=f"🏛️ {faction['faction_name']}",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc)
            )

            if faction and faction.get('faction_tag'):
                embed.description = f"Tag: **[{faction['faction_tag']}]**"

            # Get leader info
            try:

                pass
                leader = await self.bot.fetch_user(faction['leader_id'])
                leader_name = leader.mention
            except:
                leader_name = "Unknown"

            embed.add_field(
                name="👑 Leadership",
                value=f"**Leader:** {leader_name}\n**Officers:** {len(faction.get('officers', []))}",
                inline=True
            )

            embed.add_field(
                name="👥 Members",
                value=f"{len(faction['members'])}/{faction.get('max_members', 20)}",
                inline=True
            )

            # Handle faction creation date safely
            created_at = faction.get('created_at')
            if created_at and isinstance(created_at, datetime):
                try:

                    pass
                    # Ensure timezone-aware datetime
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    embed.add_field(
                        name="📅 Founded",
                        value=f"<t:{int(created_at.timestamp())}:D>",
                        inline=True
                    )
                except (ValueError, OSError):
                    embed.add_field(
                        name="📅 Founded",
                        value="Unknown",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="📅 Founded",
                    value="Unknown",
                    inline=True
                )

            # Stats
            embed.add_field(
                name="Combat Stats",
                value=f"**Kills:** {stats['total_kills']:,}\n"
                      f"**Deaths:** {stats['total_deaths']:,}\n"
                      f"**K/D Ratio:** {stats['total_kdr']:.2f}",
                inline=True
            )

            embed.add_field(
                name="Records",
                value=f"**Best Streak:** {stats['best_streak']:,}\n"
                      f"**Total Distance:** {stats['total_distance']:,.1f}m",
                inline=True
            )

            # Settings
            settings_text = []
            if faction and faction.get('invite_only', False):
                settings_text.append("Invite Only")
            else:
                settings_text.append("🌐 Open Recruitment")

            embed.add_field(
                name="⚙️ Settings",
                value="\n".join(settings_text) if settings_text else "Default",
                inline=True
            )

            if faction and faction.get('description'):
                embed.add_field(
                    name="Description",
                    value=faction['description'],
                    inline=False
                )

            faction_file = discord.File("./assets/Faction.png", filename="Faction.png")
            embed.set_thumbnail(url="attachment://Faction.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.followup.send(embed=embed, file=faction_file)

        except Exception as e:
            logger.error(f"Failed to show faction info: {e}")
            await ctx.respond("Failed to retrieve faction information.", ephemeral=True)

    @faction.command(name="stats", description="View your faction's detailed statistics")
    @discord.option(
        name="faction_name",
        description="Name of the faction to view stats for (leave empty for your own faction)",
        required=False,
        autocomplete=autocomplete_faction_name
    )
    async def faction_stats(self, ctx: discord.ApplicationContext, faction_name: str = ""):
        """View detailed faction statistics"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            discord_id = ctx.user.id

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Determine which faction to show stats for
            if faction_name:
                faction = await self.bot.db_manager.factions.find_one({
                    'guild_id': guild_id,
                    'faction_name': faction_name.strip()
                })
                if not faction:
                    await ctx.respond(f"Faction **{faction_name}** not found!", ephemeral=True)
                    return
            else:
                faction = await self.get_user_faction(guild_id or 0, discord_id)
                if not faction:
                    await ctx.respond("You are not a member of any faction! Specify a faction name to view.", ephemeral=True)
                    return

            # Calculate faction stats
            stats = await self.calculate_faction_stats(guild_id or 0, faction)

            # Create stats embed
            embed = discord.Embed(
                title=f"{faction['faction_name']} Statistics",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc)
            )

            if faction and faction.get('faction_tag'):
                embed.description = f"Tag: **[{faction['faction_tag']}]**"

            # Combat Statistics
            embed.add_field(
                name="Combat Performance",
                value=f"**Total Kills:** {stats['total_kills']:,}\n"
                      f"**Total Deaths:** {stats['total_deaths']:,}\n"
                      f"**Total Suicides:** {stats['total_suicides']:,}\n"
                      f"**K/D Ratio:** {stats['total_kdr']:.2f}",
                inline=True
            )

            # Performance Metrics
            embed.add_field(
                name="Performance Metrics",
                value=f"**Best Kill Streak:** {stats['best_streak']:,}\n"
                      f"**Total Distance:** {stats['total_distance']:,.1f}m\n"
                      f"**Avg KDR per Member:** {stats['total_kdr'] / max(stats['member_count'], 1):.2f}\n"
                      f"**Kills per Member:** {stats['total_kills'] / max(stats['member_count'], 1):.1f}",
                inline=True
            )

            # Faction Info
            embed.add_field(
                name="👥 Faction Details",
                value=f"**Active Members:** {stats['member_count']}\n"
                      f"**Total Capacity:** {faction.get('max_members', 20)}\n"
                      f"**Officers:** {len(faction.get('officers', []))}\n"
                      f"**Recruitment:** {'Invite Only' if faction and faction.get('invite_only', False) else '🌐 Open'}",
                inline=True
            )

            faction_file = discord.File("./assets/Faction.png", filename="Faction.png")
            embed.set_thumbnail(url="attachment://Faction.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.followup.send(embed=embed, file=faction_file)

        except Exception as e:
            logger.error(f"Failed to show faction stats: {e}")
            await ctx.respond("Failed to retrieve faction statistics.", ephemeral=True)

    @faction.command(name="list", description="List all factions in this server")
    async def faction_list(self, ctx: discord.ApplicationContext):
        """List all factions in the guild"""
        try:

            pass
            guild_id = ctx.guild.id if ctx.guild else 0

            # Check premium access
            if not await self.check_premium_server(guild_id):
                embed = discord.Embed(
                    title="Access Restricted",
                    description="Faction system requires premium subscription!",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

            # Get all factions
            cursor = self.bot.db_manager.factions.find({'guild_id': guild_id}).sort('faction_name', 1)
            factions = await cursor.to_list(length=50)

            if not factions:
                embed = discord.Embed(
                    title="🏛️ Factions",
                    description="No factions found! Use `/faction create` to start one.",
                    color=0x808080,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="Powered by Discord.gg/EmeraldServers")
                await ctx.respond(embed=embed)
                return

            # Create faction list embed
            embed = discord.Embed(
                title="🏛️ Server Factions",
                description=f"**{len(factions)}** factions found",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc)
            )

            faction_list = []
            for faction in factions[:15]:  # Show top 15
                name = faction['faction_name']
                tag = f"[{faction['faction_tag']}] " if faction and faction.get('faction_tag') else ""
                member_count = len(faction['members'])
                max_members = faction.get('max_members', 20)

                status = "" if faction and faction.get('invite_only', False) else "🌐"

                faction_list.append(
                    f"**{tag}{name}** {status}\n"
                    f"└ {member_count}/{max_members} members"
                )

            embed.add_field(
                name="Faction List",
                value="\n".join(faction_list),
                inline=False
            )

            if len(factions) > 15:
                embed.add_field(
                    name="Note",
                    value=f"Showing 15 of {len(factions)} factions",
                    inline=False
                )

            embed.add_field(
                name="🔑 Legend",
                value="🌐 Open Recruitment • Invite Only",
                inline=False
            )

            faction_file = discord.File("./assets/Faction.png", filename="Faction.png")
            embed.set_thumbnail(url="attachment://Faction.png")
            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await ctx.respond(embed=embed, file=faction_file)

        except Exception as e:
            logger.error(f"Failed to list factions: {e}")
            await ctx.respond("Failed to retrieve faction list.", ephemeral=True)

def setup(bot):
    bot.add_cog(Factions(bot))