
"""
Emerald's Killfeed - Database Models and Architecture
Implements PHASE 1 data architecture requirements with bulletproof error handling
"""

import logging
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager implementing PHASE 1 architecture with comprehensive error handling:
    - All PvP data stored per game server
    - Linking, wallet, factions stored per guild
    - Players linked to one account spanning all servers in guild
    - Premium tracked per game server, not user or guild
    """

    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.client = mongo_client
        self.db: AsyncIOMotorDatabase = mongo_client.emerald_killfeed
        
        # Collections
        self.guild_configs = self.db.guild_configs
        self.guilds = self.guild_configs  # Point to same collection
        self.pvp_data = self.db.pvp_data
        self.players = self.db.players
        self.economy = self.db.economy
        self.bounties = self.db.bounties
        self.factions = self.db.factions
        self.premium = self.db.premium
        self.server_premium_status = self.db.server_premium_status
        self.kill_events = self.db.kill_events
        self.parser_states = self.db.parser_states
        self.shared_parser_states = self.db.shared_parser_states
        self.player_sessions = self.db.player_sessions
        self.leaderboard_messages = self.db.leaderboard_messages
        self.bot_config = self.db.bot_config
        self.premium_limits = self.db.premium_limits
        self.wallet_events = self.db.wallet_events
    
    @property
    def admin(self):
        """Access to admin database operations"""
        return self.client.admin

    async def initialize_database(self):
        """Initialize database with proper setup"""
        await self.initialize_indexes()

    async def initialize_indexes(self):
        """Create optimized database indexes with bulletproof conflict resolution"""
        try:
            logger.info("Starting comprehensive database initialization...")
            
            # STEP 1: Aggressive cleanup of ALL conflicts before ANY index creation
            await self._bulletproof_database_cleanup()

            # STEP 2: Drop and recreate problematic indexes to ensure clean state
            await self._reset_problematic_indexes()

            # STEP 3: Create all indexes with proper error handling
            await self._create_all_indexes_safely()

            logger.info("Database initialization completed successfully")

        except Exception as e:
            logger.error(f"Critical database initialization failure: {e}")
            import traceback
            logger.error(f"Initialization traceback: {traceback.format_exc()}")
            raise

    async def _bulletproof_database_cleanup(self):
        """Comprehensive cleanup that handles ALL types of conflicts"""
        try:
            logger.info("PHASE 1: Aggressive database cleanup starting...")
            
            # 1. Complete parser_states cleanup
            logger.info("Cleaning parser_states collection...")
            
            # Find ALL documents and group by logical key
            all_parser_docs = await self.parser_states.find({}).to_list(length=None)
            logger.info(f"Found {len(all_parser_docs)} parser_states documents")
            
            # Group by logical compound key regardless of data types
            logical_groups = {}
            for doc in all_parser_docs:
                try:
                    # Normalize key components
                    guild_id = int(doc.get('guild_id', ''))
                    server_id = str(doc.get('server_id', ''))
                    parser_type = str(doc.get('parser_type', 'log_parser'))
                    
                    logical_key = f"{guild_id}_{server_id}_{parser_type}"
                    
                    if logical_key not in logical_groups:
                        logical_groups[logical_key] = []
                    logical_groups[logical_key].append(doc)
                except Exception as doc_error:
                    logger.warning(f"Error processing parser doc: {doc_error}")
                    # Mark for deletion
                    try:
                        await self.parser_states.delete_one({"_id": doc["_id"]})
                    except:
                        pass

            # Keep only the most recent document in each logical group
            total_cleaned = 0
            for logical_key, docs in logical_groups.items():
                if len(docs) > 1:
                    # Sort by last_updated or _id, keep newest
                    try:
                        sorted_docs = sorted(docs, 
                            key=lambda x: x.get('last_updated', x.get('_id', datetime.min)), 
                            reverse=True
                        )
                        to_keep = sorted_docs[0]
                        to_delete = sorted_docs[1:]
                        
                        delete_ids = [doc["_id"] for doc in to_delete]
                        result = await self.parser_states.delete_many({"_id": {"$in": delete_ids}})
                        total_cleaned += result.deleted_count
                        
                        logger.debug(f"Cleaned {result.deleted_count} duplicates for {logical_key}")
                    except Exception as cleanup_error:
                        logger.error(f"Error cleaning logical group {logical_key}: {cleanup_error}")
                        # If cleanup fails, delete ALL docs in this group and let them recreate
                        try:
                            all_ids = [doc["_id"] for doc in docs]
                            await self.parser_states.delete_many({"_id": {"$in": all_ids}})
                            total_cleaned += len(docs)
                        except:
                            pass

            if total_cleaned > 0:
                logger.info(f"Cleaned {total_cleaned} duplicate parser_states documents")

            # 2. Complete player_sessions cleanup
            logger.info("Cleaning player_sessions collection...")
            
            all_session_docs = await self.player_sessions.find({}).to_list(length=None)
            logger.info(f"Found {len(all_session_docs)} player_sessions documents")
            
            session_groups = {}
            for doc in all_session_docs:
                try:
                    guild_id = int(doc.get('guild_id', ''))
                    server_id = str(doc.get('server_id', ''))
                    player_id = str(doc.get('player_id', ''))
                    
                    logical_key = f"{guild_id}_{server_id}_{player_id}"
                    
                    if logical_key not in session_groups:
                        session_groups[logical_key] = []
                    session_groups[logical_key].append(doc)
                except Exception as doc_error:
                    logger.warning(f"Error processing session doc: {doc_error}")
                    try:
                        await self.player_sessions.delete_one({"_id": doc["_id"]})
                    except:
                        pass

            session_cleaned = 0
            for logical_key, docs in session_groups.items():
                if len(docs) > 1:
                    try:
                        sorted_docs = sorted(docs, 
                            key=lambda x: x.get('last_updated', x.get('_id', datetime.min)), 
                            reverse=True
                        )
                        to_delete = sorted_docs[1:]
                        
                        delete_ids = [doc["_id"] for doc in to_delete]
                        result = await self.player_sessions.delete_many({"_id": {"$in": delete_ids}})
                        session_cleaned += result.deleted_count
                    except Exception as cleanup_error:
                        logger.error(f"Error cleaning session group {logical_key}: {cleanup_error}")
                        try:
                            all_ids = [doc["_id"] for doc in docs]
                            await self.player_sessions.delete_many({"_id": {"$in": all_ids}})
                            session_cleaned += len(docs)
                        except:
                            pass

            if session_cleaned > 0:
                logger.info(f"Cleaned {session_cleaned} duplicate player_sessions documents")

            # 3. Normalize data types in remaining documents
            logger.info("Normalizing data types...")
            
            # Fix parser_states types
            await self.parser_states.update_many(
                {"guild_id": {"$type": "string"}},
                [{"$set": {"guild_id": {"$toLong": "$guild_id"}}}]
            )
            
            await self.player_sessions.update_many(
                {"guild_id": {"$type": "string"}},
                [{"$set": {"guild_id": {"$toLong": "$guild_id"}}}]
            )

            # 4. Remove any malformed documents
            malformed_count = 0
            
            # Remove parser_states with missing required fields
            result = await self.parser_states.delete_many({
                "$or": [
                    {"guild_id": {"$exists": False}},
                    {"server_id": {"$exists": False}},
                    {"server_id": {"$in": [None, ""]}},
                    {"guild_id": {"$in": [None, ""]}},
                    {"guild_id": {"$type": "string", "$eq": ""}},
                    {"server_id": {"$type": "string", "$eq": ""}}
                ]
            })
            malformed_count += result.deleted_count

            # Remove player_sessions with missing required fields
            result = await self.player_sessions.delete_many({
                "$or": [
                    {"guild_id": {"$exists": False}},
                    {"server_id": {"$exists": False}},
                    {"player_id": {"$exists": False}},
                    {"guild_id": {"$in": [None, ""]}},
                    {"server_id": {"$in": [None, ""]}},
                    {"player_id": {"$in": [None, ""]}}
                ]
            })
            malformed_count += result.deleted_count

            if malformed_count > 0:
                logger.info(f"Removed {malformed_count} malformed documents")

            logger.info("PHASE 1: Database cleanup completed")
            
            # Reset unified log parser states and force all players offline on bot restart
            try:
                # Reset parser states to force cold start with new regex patterns
                reset_result = await self.parser_states.update_many(
                    {'parser_type': 'unified'},  # Use 'unified' for the new parser
                    {'$unset': {'last_timestamp': ''}}  # Reset timestamp to force cold start
                )
                logger.info(f"Reset {reset_result.modified_count} unified log parser states for cold start with new regex patterns")
                
                # Force all player sessions to offline on bot startup (cold start)
                player_reset_result = await self.player_sessions.update_many(
                    {"state": {"$in": ["online", "queued"]}},
                    {
                        "$set": {
                            "state": "offline",
                            "last_updated": datetime.now(timezone.utc)
                        }
                    }
                )
                logger.info(f"Cold start: Reset {player_reset_result.modified_count} player sessions to offline state")
                
            except Exception as e:
                logger.warning(f"Cold start reset failed: {e}")

        except Exception as e:
            logger.error(f"Bulletproof cleanup failed: {e}")
            import traceback
            logger.error(f"Cleanup traceback: {traceback.format_exc()}")

    async def _reset_problematic_indexes(self):
        """Drop and recreate indexes that are causing conflicts"""
        try:
            logger.info("PHASE 2: Resetting problematic indexes...")
            
            # Drop parser_states indexes
            try:
                await self.parser_states.drop_indexes()
                logger.info("Dropped all parser_states indexes")
            except Exception as e:
                logger.debug(f"Index drop for parser_states: {e}")

            # Drop player_sessions indexes
            try:
                await self.player_sessions.drop_indexes()
                logger.info("Dropped all player_sessions indexes")
            except Exception as e:
                logger.debug(f"Index drop for player_sessions: {e}")

            logger.info("PHASE 2: Index reset completed")

        except Exception as e:
            logger.error(f"Index reset failed: {e}")

    async def _create_all_indexes_safely(self):
        """Create all indexes with comprehensive error handling"""
        try:
            logger.info("PHASE 3: Creating indexes safely...")
            
            # Guild indexes
            try:
                await self.guilds.create_index("guild_id", unique=True)
                logger.debug("Guild index created")
            except Exception as e:
                logger.warning(f"Guild index creation: {e}")

            # Player indexes (guild-scoped)
            try:
                await self.players.create_index([("guild_id", 1), ("discord_id", 1)], unique=True)
                await self.players.create_index([("guild_id", 1), ("linked_characters", 1)])
                logger.debug("Player indexes created")
            except Exception as e:
                logger.warning(f"Player index creation: {e}")

            # PvP data indexes (server-scoped)
            try:
                await self.pvp_data.create_index([("guild_id", 1), ("server_id", 1), ("player_name", 1)], unique=True)
                await self.pvp_data.create_index([("guild_id", 1), ("server_id", 1), ("kills", -1)])
                await self.pvp_data.create_index([("guild_id", 1), ("server_id", 1), ("kdr", -1)])
                logger.debug("PvP data indexes created")
            except Exception as e:
                logger.warning(f"PvP data index creation: {e}")

            # Kill events indexes (server-scoped)
            try:
                await self.kill_events.create_index([("guild_id", 1), ("server_id", 1), ("timestamp", -1)])
                await self.kill_events.create_index([("guild_id", 1), ("server_id", 1), ("killer", 1)])
                await self.kill_events.create_index([("guild_id", 1), ("server_id", 1), ("victim", 1)])
                logger.debug("Kill events indexes created")
            except Exception as e:
                logger.warning(f"Kill events index creation: {e}")

            # Economy indexes (guild-scoped)
            try:
                await self.economy.create_index([("guild_id", 1), ("discord_id", 1)], unique=True)
                logger.debug("Economy indexes created")
            except Exception as e:
                logger.warning(f"Economy index creation: {e}")

            # Faction indexes (guild-scoped)
            try:
                await self.factions.create_index([("guild_id", 1), ("faction_name", 1)], unique=True)
                logger.debug("Faction indexes created")
            except Exception as e:
                logger.warning(f"Faction index creation: {e}")

            # Premium indexes (server-scoped)
            try:
                await self.premium.create_index([("guild_id", 1), ("server_id", 1)], unique=True)
                await self.premium.create_index("expires_at")
                logger.debug("Premium indexes created")
            except Exception as e:
                logger.warning(f"Premium index creation: {e}")

            # Bounty indexes (guild-scoped)
            try:
                await self.bounties.create_index([("guild_id", 1), ("target_player", 1)])
                await self.bounties.create_index("expires_at")
                logger.debug("Bounty indexes created")
            except Exception as e:
                logger.warning(f"Bounty index creation: {e}")

            # Parser states indexes - BULLETPROOF creation
            try:
                # Wait a moment to ensure collection is ready
                await asyncio.sleep(0.1)
                
                await self.parser_states.create_index([
                    ("guild_id", 1), 
                    ("server_id", 1), 
                    ("parser_type", 1)
                ], unique=True, background=True)
                logger.info("Parser states compound index created successfully")
            except Exception as e:
                logger.error(f"Parser states index creation failed: {e}")
                # Try without unique constraint as fallback
                try:
                    await self.parser_states.create_index([
                        ("guild_id", 1), 
                        ("server_id", 1), 
                        ("parser_type", 1)
                    ], background=True)
                    logger.warning("Parser states index created without unique constraint")
                except Exception as e2:
                    logger.error(f"Parser states fallback index failed: {e2}")

            # Additional parser_states indexes
            try:
                await self.parser_states.create_index([("parser_type", 1)])
                await self.parser_states.create_index([("last_updated", -1)])
                logger.debug("Additional parser states indexes created")
            except Exception as e:
                logger.warning(f"Additional parser states indexes: {e}")

            # Player sessions indexes - EOS ID based for accurate tracking
            try:
                await asyncio.sleep(0.1)
                
                await self.player_sessions.create_index([
                    ("guild_id", 1), 
                    ("server_id", 1), 
                    ("eos_id", 1)
                ], unique=True, background=True, name="guild_server_eos_unique")
                logger.info("Player sessions EOS ID compound index created successfully")
            except Exception as e:
                logger.error(f"Player sessions EOS ID index creation failed: {e}")
                try:
                    await self.player_sessions.create_index([
                        ("guild_id", 1), 
                        ("server_id", 1), 
                        ("eos_id", 1)
                    ], background=True, name="guild_server_eos_fallback")
                    logger.warning("Player sessions EOS ID index created without unique constraint")
                except Exception as e2:
                    logger.error(f"Player sessions EOS ID fallback index failed: {e2}")

            # Additional player_sessions indexes
            try:
                await self.player_sessions.create_index([("guild_id", 1), ("status", 1)])
                await self.player_sessions.create_index([("last_updated", -1)])
                logger.debug("Additional player sessions indexes created")
            except Exception as e:
                logger.warning(f"Additional player sessions indexes: {e}")

            logger.info("PHASE 3: Index creation completed")

        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            import traceback
            logger.error(f"Index creation traceback: {traceback.format_exc()}")

    # GUILD MANAGEMENT
    async def create_guild(self, guild_id: int, guild_name: str) -> Dict[str, Any]:
        """Create guild configuration"""
        guild_doc = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "created_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "servers": [],  # List of connected game servers
            "channels": {
                "killfeed": None,
                "leaderboard": None,
                "logs": None
            },
            "settings": {
                "prefix": "!",
                "timezone": "UTC"
            }
        }

        await self.guilds.insert_one(guild_doc)
        logger.info(f"Created guild: {guild_name} ({guild_id})")
        return guild_doc

    async def get_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get guild configuration"""
        try:
            return await self.guilds.find_one({"guild_id": guild_id})
        except Exception as e:
            logger.error(f"Failed to get guild {guild_id}: {e}")
            return None

    async def add_server_to_guild(self, guild_id: int, server_config: Dict[str, Any]) -> bool:
        """Add game server to guild"""
        try:
            # First ensure the guild document exists
            guild_doc = await self.guilds.find_one({"guild_id": guild_id})
            if not guild_doc:
                # Create new guild document with proper structure
                new_guild = {
                    "guild_id": guild_id,
                    "servers": [server_config],
                    "channels": {},
                    "premium_enabled": False,
                    "features_enabled": [],
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                insert_result = await self.guilds.insert_one(new_guild)
                logger.info(f"Created new guild document for {guild_id} with server {server_config.get('_id')}")
                return insert_result.inserted_id is not None
            else:
                # Guild exists, add server to existing document
                result = await self.guilds.update_one(
                    {"guild_id": guild_id},
                    {
                        "$addToSet": {"servers": server_config},
                        "$set": {"updated_at": datetime.now(timezone.utc)}
                    }
                )
                logger.info(f"Added server {server_config.get('_id')} to existing guild {guild_id}")
                return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to add server to guild {guild_id}: {e}")
            return False

    async def remove_server_from_guild(self, guild_id: int, server_id: str) -> bool:
        """Remove game server from guild"""
        try:
            # Ensure server_id is string
            server_id = str(server_id)

            # Try removing by _id first (new format)
            result = await self.guilds.update_one(
                {"guild_id": int(guild_id)},
                {"$pull": {"servers": {"_id": server_id}}}
            )

            # If no match, try removing by server_id (old format)
            if result.modified_count == 0:
                result = await self.guilds.update_one(
                    {"guild_id": int(guild_id)},
                    {"$pull": {"servers": {"server_id": server_id}}}
                )

            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to remove server from guild {guild_id}: {e}")
            return False

    # PLAYER LINKING (Guild-scoped)
    async def find_player_in_pvp_data(self, guild_id: int, character_name: str) -> Optional[str]:
        """Find player in PvP data with case-insensitive search, returns actual player name if found"""
        try:
            # Search for player with case-insensitive regex that handles spaces
            # Remove extra spaces and normalize the search term
            normalized_search = ' '.join(character_name.strip().split())

            # Create case-insensitive regex pattern
            escaped_search = normalized_search.replace(' ', r'\s+')
            pattern = f"^{escaped_search}$"

            player_doc = await self.pvp_data.find_one({
                "guild_id": guild_id,
                "player_name": {"$regex": pattern, "$options": "i"}
            })

            if player_doc:
                return player_doc["player_name"]  # Return the actual player name from database

            return None

        except Exception as e:
            logger.error(f"Failed to find player in PvP data: {e}")
            return None

    async def link_player(self, guild_id: int, discord_id: int, character_name: str) -> bool:
        """Link Discord user to character (guild-scoped) with enhanced security"""
        try:
            # Comprehensive input validation and sanitization
            if not isinstance(guild_id, int) or guild_id <= 0:
                logger.error(f"Invalid guild_id: {guild_id}")
                return False

            if not isinstance(discord_id, int) or discord_id <= 0:
                logger.error(f"Invalid discord_id: {discord_id}")
                return False

            if not isinstance(character_name, str) or not character_name.strip():
                logger.error(f"Invalid character_name: {character_name}")
                return False

            # Reject numeric-only names (like "17.0")
            if character_name.strip().replace('.', '').replace('-', '').isdigit():
                logger.error(f"Invalid character_name: {character_name} (numeric-only names not allowed)")
                return False

            # Enhanced sanitization to prevent injection
            import re
            # Remove any potential MongoDB operators or special characters
            character_name = re.sub(r'[\$\{\}]', '', character_name)
            character_name = re.sub(r'[^\w\s\-_\[\]().]', '', character_name.strip())

            if len(character_name) < 2 or len(character_name) > 50:
                logger.error(f"Character name length invalid: {character_name}")
                return False

            # Check if player already exists
            existing_player = await self.players.find_one({
                "guild_id": guild_id, 
                "discord_id": discord_id
            })

            if existing_player:
                # Player exists, just add the character if not already linked
                if character_name not in existing_player.get('linked_characters', []):
                    await self.players.update_one(
                        {"guild_id": guild_id, "discord_id": discord_id},
                        {"$addToSet": {"linked_characters": character_name}}
                    )
            else:
                # New player, create document
                player_doc = {
                    "guild_id": guild_id,
                    "discord_id": discord_id,
                    "linked_characters": [character_name],
                    "primary_character": character_name,
                    "linked_at": datetime.now(timezone.utc)
                }
                await self.players.insert_one(player_doc)

            logger.info(f"Linked player {character_name} to Discord {discord_id} in guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to link player: {e}")
            return False

    async def get_linked_player(self, guild_id: int, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get linked player data"""
        try:
            player_doc = await self.players.find_one({
                'guild_id': guild_id,
                'discord_id': discord_id
            })

            if player_doc:
                # Ensure we return a proper dict, not a tuple
                if isinstance(player_doc, dict):
                    # Validate required fields
                    if 'linked_characters' not in player_doc or not player_doc['linked_characters']:
                        logger.error(f"Player doc missing linked_characters: {player_doc}")
                        # Try to repair by deleting corrupt document
                        try:
                            await self.players.delete_one({
                                'guild_id': guild_id,
                                'discord_id': discord_id
                            })
                            logger.info(f"Deleted corrupt player document for guild {guild_id}, discord {discord_id}")
                        except Exception as cleanup_error:
                            logger.error(f"Failed to cleanup corrupt player document: {cleanup_error}")
                        return None

                    if 'primary_character' not in player_doc:
                        # Set primary_character if missing and update document
                        primary_char = player_doc['linked_characters'][0]
                        player_doc['primary_character'] = primary_char
                        try:
                            await self.players.update_one(
                                {'guild_id': guild_id, 'discord_id': discord_id},
                                {'$set': {'primary_character': primary_char}}
                            )
                            logger.info(f"Set missing primary_character for guild {guild_id}, discord {discord_id}")
                        except Exception as update_error:
                            logger.error(f"Failed to set primary_character: {update_error}")

                    # Ensure linked_at field exists
                    if 'linked_at' not in player_doc:
                        player_doc['linked_at'] = datetime.now(timezone.utc)
                        try:
                            await self.players.update_one(
                                {'guild_id': guild_id, 'discord_id': discord_id},
                                {'$set': {'linked_at': player_doc['linked_at']}}
                            )
                        except Exception as update_error:
                            logger.error(f"Failed to set linked_at: {update_error}")

                    return player_doc
                else:
                    logger.error(f"Unexpected player_doc type: {type(player_doc)} - value: {player_doc}")
                    return None

            return None

        except Exception as e:
            logger.error(f"Failed to get linked player: {e}")
            raise  # Re-raise to allow calling code to handle appropriately

    # PVP DATA (Server-scoped)
    async def update_pvp_stats(self, guild_id: int, server_id: str, player_name: str, 
                              stats_update: Dict[str, Any]) -> bool:
        """Update PvP statistics for player on specific server"""
        try:
            # Input validation
            if not isinstance(guild_id, int) or guild_id <= 0:
                logger.error(f"Invalid guild_id: {guild_id}")
                return False

            if not isinstance(server_id, str) or not server_id.strip():
                logger.error(f"Invalid server_id: {server_id}")
                return False

            if not isinstance(player_name, str) or not player_name.strip():
                logger.debug(f"Skipping stats update for empty player name: '{player_name}'")
                return False

            if not isinstance(stats_update, dict) or not stats_update:
                logger.error(f"Invalid stats_update: {stats_update}")
                return False

            # Sanitize inputs
            server_id = str(server_id).strip()
            player_name = player_name.strip()

            # Validate numeric stats
            numeric_fields = {"kills", "deaths", "suicides", "longest_streak", "current_streak", "total_distance", "kdr"}
            for field, value in stats_update.items():
                if field in numeric_fields:
                    if not isinstance(value, (int, float)) or value < 0:
                        logger.error(f"Invalid numeric value for {field}: {value}")
                        return False
            # Define all possible stat fields that could be incremented
            incrementable_fields = {
                "kills", "deaths", "suicides", "longest_streak", "current_streak", "total_distance"
            }

            # Handle atomic increment operations
            if isinstance(stats_update, dict) and len(stats_update) == 1:
                # Simple single field update - use atomic increment
                field_name = list(stats_update.keys())[0]
                field_value = list(stats_update.values())[0]

                if field_name in incrementable_fields:
                    # Create safe defaults without any incrementable fields or timestamps
                    safe_defaults = {
                        "guild_id": guild_id,
                        "server_id": server_id,
                        "player_name": player_name,
                        "created_at": datetime.now(timezone.utc),
                        "kdr": 0.0,
                        "favorite_weapon": None,
                        "best_streak": 0,
                        "personal_best_distance": 0.0
                    }

                    # Only add non-incrementable stat defaults
                    for field in ["kills", "deaths", "suicides", "longest_streak", "current_streak", "total_distance"]:
                        if field != field_name:  # Don't set default for field we're incrementing
                            safe_defaults[field] = 0 if field != "total_distance" else 0.0

                    # Single atomic operation without conflicts
                    result = await self.pvp_data.update_one(
                        {
                            "guild_id": guild_id,
                            "server_id": server_id,
                            "player_name": player_name
                        },
                        {
                            "$inc": {field_name: field_value},
                            "$setOnInsert": safe_defaults,
                            "$currentDate": {"last_updated": True}
                        },
                        upsert=True
                    )

                    # Handle KDR calculation separately if needed
                    if field_name in ["kills", "deaths"] and result.acknowledged:
                        await self._update_kdr(guild_id, server_id, player_name)

                else:
                    # Non-incrementable field, use simple set
                    await self.pvp_data.update_one(
                        {
                            "guild_id": guild_id,
                            "server_id": server_id,
                            "player_name": player_name
                        },
                        {
                            "$set": stats_update,
                            "$currentDate": {"last_updated": True}
                        },
                        upsert=True
                    )
            else:
                # Complex update - get current doc first to avoid conflicts
                current_doc = await self.pvp_data.find_one({
                    "guild_id": guild_id,
                    "server_id": server_id,
                    "player_name": player_name
                })

                # Calculate KDR if kills or deaths are being updated
                if "kills" in stats_update or "deaths" in stats_update:
                    kills = stats_update.get("kills", current_doc.get("kills", 0) if current_doc else 0)
                    deaths = stats_update.get("deaths", current_doc.get("deaths", 0) if current_doc else 0)
                    stats_update["kdr"] = kills / max(deaths, 1) if deaths > 0 else float(kills)

                if not current_doc:
                    # Create new document
                    new_doc = {
                        "guild_id": guild_id,
                        "server_id": server_id,
                        "player_name": player_name,
                        "created_at": datetime.now(timezone.utc),
                        "last_updated": datetime.now(timezone.utc),
                        "kills": 0,
                        "deaths": 0,
                        "suicides": 0,
                        "kdr": 0.0,
                        "total_distance": 0.0,
                        "favorite_weapon": None,
                        "longest_streak": 0,
                        "current_streak": 0,
                        "personal_best_distance": 0.0,
                        **stats_update
                    }
                    await self.pvp_data.insert_one(new_doc)
                else:
                    # Update existing document
                    await self.pvp_data.update_one(
                        {"guild_id": guild_id, "server_id": server_id, "player_name": player_name},
                        {
                            "$set": {
                                **stats_update,
                                "last_updated": datetime.now(timezone.utc)
                            }
                        }
                    )

            logger.debug(f"Successfully updated PvP stats for {player_name} in server {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update PvP stats: {e}")
            return False

    async def _update_kdr(self, guild_id: int, server_id: str, player_name: str):
        """Helper method to update KDR calculation"""
        try:
            current_doc = await self.pvp_data.find_one({
                "guild_id": guild_id,
                "server_id": server_id,
                "player_name": player_name
            })

            if current_doc:
                kills = current_doc.get("kills", 0)
                deaths = current_doc.get("deaths", 0)
                kdr = kills / max(deaths, 1) if deaths > 0 else float(kills)

                await self.pvp_data.update_one(
                    {"guild_id": guild_id, "server_id": server_id, "player_name": player_name},
                    {"$set": {"kdr": kdr}}
                )
        except Exception as e:
            logger.error(f"Failed to update KDR: {e}")

    async def get_pvp_stats(self, guild_id: int, server_id: str, player_name: str) -> Optional[Dict[str, Any]]:
        """Get PvP statistics for player on specific server"""
        return await self.pvp_data.find_one({
            "guild_id": guild_id,
            "server_id": server_id,
            "player_name": player_name
        })

    async def get_guild_currency_name(self, guild_id: int) -> str:
        """Get custom currency name for guild or default"""
        try:
            guild_doc = await self.guilds.find_one({'guild_id': guild_id})
            return guild_doc.get('currency_name', 'Emeralds') if guild_doc else 'Emeralds'
        except Exception:
            return 'Emeralds'

    async def reset_player_streak(self, guild_id: int, server_id: str, player_name: str):
        """Reset a player's current streak to 0"""
        try:
            await self.pvp_data.update_one(
                {
                    "guild_id": guild_id,
                    "server_id": server_id,
                    "player_name": player_name
                },
                {
                    "$set": {"current_streak": 0}
                }
            )
        except Exception as e:
            logger.error(f"Failed to reset player streak: {e}")

    async def add_kill_event(self, guild_id: int, server_id: str, kill_data: Dict[str, Any]):
        """Add a kill event to the database with enhanced distance validation"""
        try:
            # PHASE 1 FIX: Ensure distance is properly validated before DB insertion
            distance = kill_data.get("distance", 0)
            if isinstance(distance, str):
                try:
                    distance = float(distance) if distance else 0.0
                except (ValueError, TypeError):
                    distance = 0.0
            elif not isinstance(distance, (int, float)):
                distance = 0.0

            # Ensure distance is within reasonable bounds
            distance = max(0.0, min(distance, 5000.0))

            kill_event = {
                "guild_id": guild_id,
                "server_id": server_id,
                "timestamp": kill_data.get("timestamp", datetime.now(timezone.utc)),
                "killer": kill_data.get("killer", ""),
                "killer_id": kill_data.get("killer_id", ""),
                "victim": kill_data.get("victim", ""),
                "victim_id": kill_data.get("victim_id", ""),
                "weapon": kill_data.get("weapon", ""),
                "distance": distance,  # Now properly validated numeric value
                "killer_platform": kill_data.get("killer_platform", ""),
                "victim_platform": kill_data.get("victim_platform", ""),
                "is_suicide": kill_data.get("is_suicide", False),
                "raw_line": kill_data.get("raw_line", "")
            }

            await self.kill_events.insert_one(kill_event)
            logger.debug(f"Added kill event: {kill_data['killer']} -> {kill_data['victim']} (distance: {distance}m)")
            
            # Update player stats for killer (if not suicide)
            if not kill_data.get('is_suicide', False):
                await self.increment_player_kill(
                    guild_id, 
                    server_id, 
                    kill_data.get('killer', ''), 
                    distance, 
                    kill_data.get('timestamp') or datetime.utcnow()
                )
            
            # Update victim death count
            await self.increment_player_death(
                guild_id, 
                server_id, 
                kill_data.get('victim', '')
            )

        except Exception as e:
            logger.error(f"Failed to add kill event: {e}")

    async def increment_player_kill(self, guild_id: int, server_id: str, player_name: str, distance: float = 0.0, event_timestamp: Optional[datetime] = None):
        """Increment player kill count and update streak/distance stats with chronological validation"""
        try:
            # Ensure consistent types
            guild_id = int(guild_id)
            server_id = str(server_id)
            player_name = str(player_name).strip()
            
            # PHASE 1 FIX: Ensure distance is properly validated and tracked
            if isinstance(distance, str):
                try:
                    # Handle empty strings and None values
                    distance = float(distance) if distance and distance.strip() else 0.0
                except (ValueError, TypeError):
                    distance = 0.0
            elif not isinstance(distance, (int, float)):
                distance = 0.0

            # Validate range and handle edge cases
            distance = max(0.0, min(float(distance), 5000.0))  # Validate range
            distance = round(distance, 1)  # Round for consistency

            # Chronological validation: Check if this event is newer than last processed
            if event_timestamp:
                try:
                    current_stats = await self.get_pvp_stats(guild_id, server_id, player_name)
                    if current_stats and current_stats.get('last_kill_timestamp'):
                        last_timestamp = current_stats['last_kill_timestamp']
                        if isinstance(last_timestamp, datetime) and event_timestamp < last_timestamp:
                            logger.debug(f"Skipping out-of-order kill event for {player_name}: {event_timestamp} < {last_timestamp}")
                            return
                except Exception as timestamp_error:
                    logger.debug(f"Timestamp validation failed, proceeding: {timestamp_error}")

            # Get current stats to calculate new longest distance and streak
            current_stats = await self.get_pvp_stats(guild_id, server_id, player_name)

            # Calculate new streak and longest distance
            current_streak = current_stats.get('current_streak', 0) if current_stats else 0
            new_streak = current_streak + 1
            longest_streak = max(current_stats.get('longest_streak', 0) if current_stats else 0, new_streak)
            personal_best_distance = max(current_stats.get('personal_best_distance', 0.0) if current_stats else 0.0, distance)

            # Use atomic increment for kills
            await self.update_pvp_stats(guild_id, server_id, player_name, {"kills": 1})

            # Add distance to total_distance (accumulated) if distance > 0
            if distance > 0:
                # Use atomic increment to accumulate total distance
                current_total = current_stats.get('total_distance', 0.0) if current_stats else 0.0
                new_total = current_total + distance
                await self.update_pvp_stats(guild_id, server_id, player_name, {"total_distance": new_total})

            # Update streak, personal best, and timestamp in single operation
            update_data = {
                "current_streak": new_streak,
                "longest_streak": longest_streak
            }

            # Only update personal best if this distance is actually better
            current_best = current_stats.get('personal_best_distance', 0.0) if current_stats else 0.0
            if distance > 0 and distance > current_best:
                update_data["personal_best_distance"] = distance

            # Update last kill timestamp for chronological tracking
            if event_timestamp:
                update_data["last_kill_timestamp"] = event_timestamp

            await self.update_pvp_stats(guild_id, server_id, player_name, update_data)

        except Exception as e:
            logger.error(f"Failed to increment player kill: {e}")

    async def increment_player_death(self, guild_id: int, server_id: str, player_name: str):
        """Increment player death count and reset streak"""
        try:
            await self.update_pvp_stats(
                guild_id, server_id, player_name,
                {"deaths": 1}
            )
            # Reset streak separately
            await self.reset_player_streak(guild_id, server_id, player_name)

        except Exception as e:
            logger.error(f"Failed to increment player death: {e}")

    async def find_player_by_character_name(self, guild_id: int, character_name: str) -> Optional[Dict]:
        """Find a player document by searching linked character names (case-insensitive, space-normalized)"""
        try:
            # Normalize the search term
            normalized_search = ' '.join(character_name.strip().split())

            # Create case-insensitive regex pattern
            escaped_search = normalized_search.replace(' ', r'\s+')
            pattern = f"^{escaped_search}$"

            player_doc = await self.pvp_data.find_one({
                "guild_id": guild_id,
                "player_name": {
                    "$regex": pattern,
                    "$options": "i"
                }
            })

            return player_doc

        except Exception as e:
            logger.error(f"Failed to find player by character name: {e}")
            return None

    async def get_recent_kills(self, guild_id: int, server_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent kill events for server"""
        cursor = self.kill_events.find(
            {"guild_id": guild_id, "server_id": server_id}
        ).sort("timestamp", -1).limit(limit)

        return await cursor.to_list(length=limit)

    # ECONOMY (Guild-scoped)
    async def get_wallet(self, guild_id: int, discord_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """Get user wallet (guild-scoped)"""
        wallet = await self.economy.find_one({"guild_id": guild_id, "discord_id": discord_id})

        if not wallet:
            wallet = {
                "guild_id": guild_id,
                "discord_id": discord_id,
                "balance": 0,
                "total_earned": 0,
                "total_spent": 0,
                "created_at": datetime.now(timezone.utc)
            }
            await self.economy.insert_one(wallet)

        return wallet

    async def update_wallet(self, guild_id: int, discord_id: int, amount: int, 
                           transaction_type: str) -> bool:
        """Update user wallet balance"""
        try:
            inc_updates = {"balance": amount}
            if amount > 0:
                inc_updates["total_earned"] = amount
            else:
                inc_updates["total_spent"] = abs(amount)

            update_query = {
                "$inc": inc_updates,
                "$set": {"last_updated": datetime.now(timezone.utc)}
            }

            result = await self.economy.update_one(
                {"guild_id": guild_id, "discord_id": discord_id},
                update_query,
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Failed to update wallet: {e}")
            return False

    async def add_wallet_event(self, guild_id: int, discord_id: int, amount: int, event_type: str, description: str) -> bool:
        """Add a wallet transaction event"""
        try:
            event_data = {
                "guild_id": guild_id,
                "discord_id": discord_id,
                "amount": amount,
                "event_type": event_type,
                "description": description,
                "timestamp": datetime.now(timezone.utc)
            }
            
            result = await self.db.wallet_events.insert_one(event_data)
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Failed to add wallet event: {e}")
            return False

    async def update_player_state(self, guild_id: int, player_id: str, state: str, server_name: str, timestamp: datetime, skip_voice_update: bool = False) -> bool:
        """Update player state and return if state actually changed - Enhanced with transaction safety"""
        try:
            # Check current state
            current_session = await self.player_sessions.find_one({
                "guild_id": guild_id,
                "player_id": player_id
            })
            
            # Determine if state actually changed
            current_state = current_session.get('state', 'offline') if current_session else 'offline'
            state_changed = current_state != state
            
            if state_changed:
                # Prepare complete session document with all required fields
                session_data = {
                    "guild_id": guild_id,
                    "player_id": player_id,
                    "state": state,
                    "server_name": server_name,
                    "last_updated": timestamp,
                    "player_name": f"Player{player_id[:8].upper()}",
                    "joined_at": timestamp.isoformat() if state == 'online' else current_session.get('joined_at') if current_session else None,
                    "platform": "Unknown"
                }
                
                # Use replace_one with upsert for atomic operation
                update_result = await self.player_sessions.replace_one(
                    {"guild_id": guild_id, "player_id": player_id},
                    session_data,
                    upsert=True
                )
                
                # Enhanced logging with verification
                if update_result.upserted_id:
                    logger.info(f"✓ Created session for {player_id[:8]}... -> {state} on {server_name}")
                    # Verify the insertion actually worked
                    verification = await self.player_sessions.find_one({"guild_id": guild_id, "player_id": player_id})
                    if verification:
                        logger.debug(f"✓ Verified session exists: {verification.get('state')} on {verification.get('server_name')}")
                    else:
                        logger.error(f"✗ Session verification failed for {player_id[:8]}...")
                elif update_result.modified_count > 0:
                    logger.info(f"✓ Updated session for {player_id[:8]}... -> {state} on {server_name}")
                else:
                    logger.warning(f"✗ Database operation returned no changes for {player_id[:8]}... -> {state}")
                    
                    # Force verification of current state
                    post_update_session = await self.player_sessions.find_one({"guild_id": guild_id, "player_id": player_id})
                    if post_update_session:
                        current_db_state = post_update_session.get('state')
                        logger.info(f"Post-update verification: {player_id[:8]}... is {current_db_state}")
                    else:
                        logger.error(f"Post-update verification: no session found for {player_id[:8]}...")
            
            return state_changed
            
        except Exception as e:
            logger.error(f"Failed to update player state for {player_id[:8]}...: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False

    async def get_active_player_count(self, guild_id: int, server_name: str) -> int:
        """Get count of active (online) players for a specific server with automatic cleanup"""
        try:
            # First, clean up stale sessions (older than 30 minutes should be considered disconnected)
            stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            stale_cleanup = await self.player_sessions.update_many(
                {
                    "guild_id": guild_id,
                    "server_name": server_name,
                    "state": "online",
                    "last_updated": {"$lt": stale_cutoff}
                },
                {
                    "$set": {
                        "state": "offline",
                        "last_updated": datetime.now(timezone.utc)
                    }
                }
            )
            
            if stale_cleanup.modified_count > 0:
                logger.info(f"Auto-cleaned {stale_cleanup.modified_count} stale online sessions for {server_name}")
            
            # Now count actual online players
            count = await self.player_sessions.count_documents({
                "guild_id": guild_id,
                "server_name": server_name,
                "state": "online"
            })
            return count
        except Exception as e:
            logger.error(f"Failed to get active player count for {server_name}: {e}")
            return 0

    # PREMIUM (Server-scoped)
    async def set_premium_status(self, guild_id: int, server_id: str, 
                                expires_at: Optional[datetime] = None) -> bool:
        """Set premium status for specific server"""
        try:
            # Ensure types are consistent
            guild_id = int(guild_id)
            server_id = str(server_id)

            # Ensure expires_at is timezone-aware if provided
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            premium_doc = {
                "guild_id": guild_id,
                "server_id": server_id,
                "active": expires_at is not None,
                "expires_at": expires_at,
                "updated_at": datetime.now(timezone.utc)
            }

            await self.premium.update_one(
                {"guild_id": guild_id, "server_id": server_id},
                {"$set": premium_doc},
                upsert=True
            )

            return True

        except Exception as e:
            logger.error(f"Failed to set premium status: {e}")
            return False

    async def is_premium_server(self, guild_id: int, server_id: str) -> bool:
        """Check if server has active premium - Updated to use new premium system"""
        try:
            # Use the new premium checking method
            return await self.is_server_premium(guild_id, server_id)
        except Exception as e:
            logger.error(f"Failed to check premium status: {e}")
            return False

    # LEADERBOARDS
    async def get_leaderboard(self, guild_id: int, server_id: str, stat: str = "kills", 
                             limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard for specific stat"""
        sort_order = -1 if stat in ["kills", "kdr", "longest_streak"] else 1

        cursor = self.pvp_data.find(
            {"guild_id": guild_id, "server_id": server_id}
        ).sort(stat, sort_order).limit(limit)

        return await cursor.to_list(length=limit)

    # LOG PARSER SUPPORT METHODS
    async def get_active_premium_servers(self) -> List[Dict[str, Any]]:
        """Get all active premium servers for log parser"""
        try:
            # Find all premium servers that are active and not expired
            current_time = datetime.now(timezone.utc)

            premium_servers = await self.premium.find({
                "active": True,
                "$or": [
                    {"expires_at": {"$gt": current_time}},
                    {"expires_at": None}
                ]
            }).to_list(length=None)

            # Get server names from guild configurations
            result = []
            for premium_doc in premium_servers:
                guild_id = premium_doc.get("guild_id")
                server_id = premium_doc.get("server_id")

                # Find the guild config to get server name
                guild_config = await self.guilds.find_one({"guild_id": guild_id})
                if guild_config:
                    servers = guild_config.get("servers", [])
                    for server in servers:
                        # Check both _id and server_id for backwards compatibility
                        if (str(server.get("_id")) == str(server_id) or 
                            str(server.get("server_id")) == str(server_id)):
                            result.append({
                                "server_id": server_id,
                                "server_name": server.get("name", f"Server {server_id}"),
                                "guild_id": guild_id,
                                "expires_at": premium_doc.get("expires_at")
                            })
                            break

            return result

        except Exception as e:
            logger.error(f"Failed to get active premium servers: {e}")
            return []

    async def get_recent_log_events(self, server_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent log events for a server"""
        try:
            cursor = self.kill_events.find(
                {"server_id": server_id}
            ).sort("timestamp", -1).limit(limit)

            return await cursor.to_list(length=limit)

        except Exception as e:
            logger.error(f"Failed to get recent log events: {e}")
            return []

    async def get_current_online_count(self, server_id: str) -> int:
        """Get current online player count for a server"""
        try:
            # This would typically come from a separate online players collection
            # For now, return a placeholder based on recent activity
            recent_events = await self.get_recent_log_events(server_id, 10)

            # Count unique players from recent events (last hour)
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_players = set()

            for event in recent_events:
                event_time = event.get("timestamp")
                if event_time and event_time > one_hour_ago:
                    if event and event.get("killer"):
                        recent_players.add(event.get("killer"))
                    if event and event.get("victim"):
                        recent_players.add(event.get("victim"))

            return len(recent_players)

        except Exception as e:
            logger.error(f"Failed to get current online count: {e}")
            return 0

    # PARSER STATE MANAGEMENT - BULLETPROOF WITH LOCKING
    async def get_parser_state(self, guild_id: int, server_id: str, parser_type: str = "log_parser") -> Dict[str, Any]:
        """Get parser state for a specific server"""
        try:
            state = await self.parser_states.find_one({
                "guild_id": guild_id,
                "server_id": server_id,
                "parser_type": parser_type
            })
            return state if state else {}
        except Exception as e:
            logger.error(f"Failed to get parser state: {e}")
            return {}

    async def save_parser_state(self, guild_id: int, server_id: str, parser_type: str, state_data: Dict[str, Any]):
        """Save parser state with bulletproof duplicate handling using replace strategy"""
        try:
            # Ensure types are consistent
            guild_id = int(guild_id)
            server_id = str(server_id).strip()
            
            if not server_id:
                logger.error(f"Invalid empty server_id for guild {guild_id}")
                return

            # Create lock key for this specific parser state
            lock_key = f"{guild_id}_{server_id}_{parser_type}"
            
            # Use a simple retry mechanism instead of complex locking
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Use replace_one with upsert for bulletproof handling
                    filter_doc = {
                        "guild_id": guild_id,
                        "server_id": server_id,
                        "parser_type": parser_type
                    }
                    
                    replacement_doc = {
                        "guild_id": guild_id,
                        "server_id": server_id,
                        "parser_type": parser_type,
                        "last_updated": datetime.now(timezone.utc),
                        **state_data
                    }
                    
                    result = await self.parser_states.replace_one(
                        filter_doc,
                        replacement_doc,
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        logger.debug(f"Created new parser state for {server_id}")
                    elif result.modified_count > 0:
                        logger.debug(f"Updated existing parser state for {server_id}")
                    else:
                        logger.debug(f"Parser state unchanged for {server_id}")
                    
                    return  # Success, exit retry loop
                    
                except Exception as e:
                    error_str = str(e)
                    if "E11000" in error_str and "duplicate key" in error_str and attempt < max_retries - 1:
                        logger.debug(f"Duplicate key on attempt {attempt + 1} for {server_id}, retrying...")
                        
                        # Try to clean up the conflict and retry
                        try:
                            # Delete any conflicting documents
                            await self.parser_states.delete_many({
                                "guild_id": guild_id,
                                "server_id": server_id,
                                "parser_type": parser_type
                            })
                            await asyncio.sleep(0.1)  # Brief delay before retry
                        except:
                            pass
                        continue
                    else:
                        raise e
                        
            logger.error(f"Failed to save parser state after {max_retries} attempts")
                        
        except Exception as e:
            logger.error(f"Failed to save parser state for {server_id}: {e}")

    async def get_all_parser_states(self, guild_id: int, parser_type: str = "log_parser") -> Dict[str, Dict[str, Any]]:
        """Get all parser states for a guild"""
        try:
            states = {}
            cursor = self.parser_states.find({
                "guild_id": guild_id,
                "parser_type": parser_type
            })
            async for state in cursor:
                server_id = state.get("server_id")
                if server_id:
                    states[server_id] = state
            return states
        except Exception as e:
            logger.error(f"Failed to get all parser states: {e}")
            return {}

    async def update_server_config(self, guild_id: int, server_id: str, config_updates: Dict[str, Any]) -> bool:
        """Update server configuration in guild document"""
        try:
            result = await self.guilds.update_one(
                {
                    "guild_id": guild_id,
                    "servers._id": server_id
                },
                {
                    "$set": {f"servers.$.{key}": value for key, value in config_updates.items()},
                    "$currentDate": {"last_updated": True}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update server config: {e}")
            return False

    # PLAYER SESSION PERSISTENCE - BULLETPROOF WITH REPLACE STRATEGY
    async def save_player_session(self, guild_id: int, server_id: str, player_id: str, session_data: Dict[str, Any]):
        """Save player session with bulletproof duplicate handling using replace strategy"""
        try:
            # Ensure consistent types
            guild_id = int(guild_id)
            server_id = str(server_id)
            player_id = str(player_id)

            session_doc = {
                "guild_id": guild_id,
                "server_id": server_id,
                "player_id": player_id,
                "last_updated": datetime.now(timezone.utc),
                **session_data
            }

            # Use replace_one with upsert for bulletproof handling
            filter_doc = {
                "guild_id": guild_id,
                "server_id": server_id,
                "player_id": player_id
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = await self.player_sessions.replace_one(
                        filter_doc,
                        session_doc,
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        logger.debug(f"Created new player session for {player_id}")
                    elif result.modified_count > 0:
                        logger.debug(f"Updated existing player session for {player_id}")
                    else:
                        logger.debug(f"Player session unchanged for {player_id}")
                    
                    return  # Success
                    
                except Exception as e:
                    error_str = str(e)
                    if "E11000" in error_str and "duplicate key" in error_str and attempt < max_retries - 1:
                        logger.debug(f"Session duplicate key on attempt {attempt + 1} for {player_id}, retrying...")
                        
                        # Clean up conflicts and retry
                        try:
                            await self.player_sessions.delete_many(filter_doc)
                            await asyncio.sleep(0.1)
                        except:
                            pass
                        continue
                    else:
                        raise e
                        
            logger.error(f"Failed to save player session after {max_retries} attempts")

        except Exception as e:
            logger.error(f"Failed to save player session for {player_id}: {e}")

    async def get_active_player_sessions(self, guild_id: int, server_id: str = "default") -> List[Dict[str, Any]]:
        """Get active player sessions for guild/server"""
        try:
            query = {"guild_id": guild_id, "status": "online"}
            if server_id:
                query["server_id"] = server_id

            cursor = self.player_sessions.find(query)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Failed to get active player sessions: {e}")
            return []



    async def remove_player_session(self, guild_id: int, server_id: str, player_id: str):
        """Remove player session from database"""
        try:
            # Ensure consistent types
            guild_id = int(guild_id)
            server_id = str(server_id)
            player_id = str(player_id)
            
            await self.player_sessions.delete_many({
                "guild_id": guild_id,
                "server_id": server_id,
                "player_id": player_id
            })
        except Exception as e:
            logger.error(f"Failed to remove player session: {e}")

    async def cleanup_stale_sessions(self, max_age_hours: int = 24):
        """Clean up old player sessions"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            result = await self.player_sessions.delete_many({
                "last_updated": {"$lt": cutoff}
            })
            logger.debug(f"Cleaned up {result.deleted_count} stale player sessions")
        except Exception as e:
            logger.error(f"Failed to cleanup stale sessions: {e}")

    async def cleanup_old_factions(self):
        """Remove factions with no members"""
        try:
            # Find factions with empty member lists
            empty_factions = await self.factions.find({
                '$or': [
                    {'members': {'$exists': False}},
                    {'members': {'$size': 0}}
                ]
            }).to_list(length=None)

            if empty_factions:
                faction_ids = [f['_id'] for f in empty_factions]
                result = await self.factions.delete_many({'_id': {'$in': faction_ids}})
                logger.info(f"Cleaned up {result.deleted_count} empty factions")

        except Exception as e:
            logger.error(f"Failed to cleanup old factions: {e}")

    # ===== PREMIUM MANAGEMENT METHODS =====
    
    async def set_home_guild(self, guild_id: int, set_by: int) -> bool:
        """Set the Home Guild for premium management"""
        try:
            await self.bot_config.replace_one(
                {"type": "home_guild"},
                {
                    "type": "home_guild",
                    "guild_id": guild_id,
                    "set_by": set_by,
                    "set_at": datetime.now(timezone.utc)
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set home guild: {e}")
            return False

    async def get_home_guild(self) -> Optional[int]:
        """Get the current Home Guild ID"""
        try:
            config = await self.bot_config.find_one({"type": "home_guild"})
            return config.get("guild_id") if config else None
        except Exception as e:
            logger.error(f"Failed to get home guild: {e}")
            return None

    async def add_premium_limit(self, guild_id: int, added_by: int, reason: Optional[str] = None) -> bool:
        """Add 1 to the premium server limit for a guild"""
        try:
            await self.premium_limits.update_one(
                {"guild_id": guild_id},
                {
                    "$inc": {"limit": 1},
                    "$push": {
                        "history": {
                            "action": "add",
                            "amount": 1,
                            "by": added_by,
                            "reason": reason or "No reason provided",
                            "timestamp": datetime.now(timezone.utc)
                        }
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add premium limit: {e}")
            return False

    async def remove_premium_limit(self, guild_id: int, removed_by: int, reason: Optional[str] = None) -> bool:
        """Remove 1 from the premium server limit for a guild"""
        try:
            # Get current limit
            current_doc = await self.premium_limits.find_one({"guild_id": guild_id})
            current_limit = current_doc.get("limit", 0) if current_doc else 0
            
            if current_limit <= 0:
                return False
            
            # Update limit
            await self.premium_limits.update_one(
                {"guild_id": guild_id},
                {
                    "$inc": {"limit": -1},
                    "$push": {
                        "history": {
                            "action": "remove",
                            "amount": 1,
                            "by": removed_by,
                            "reason": reason or "No reason provided",
                            "timestamp": datetime.now(timezone.utc)
                        }
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to remove premium limit: {e}")
            return False

    async def get_premium_limit(self, guild_id: int) -> int:
        """Get current premium server limit for guild"""
        try:
            doc = await self.premium_limits.find_one({"guild_id": guild_id})
            return doc.get("limit", 0) if doc else 0
        except Exception as e:
            logger.error(f"Failed to get premium limit: {e}")
            return 0

    async def count_premium_servers(self, guild_id: int) -> int:
        """Count active premium servers for guild"""
        try:
            count = await self.server_premium_status.count_documents({
                "guild_id": guild_id,
                "is_active": True,
                "$or": [
                    {"expires_at": {"$exists": False}},
                    {"expires_at": None},
                    {"expires_at": {"$gt": datetime.now(timezone.utc)}}
                ]
            })
            return count
        except Exception as e:
            logger.error(f"Failed to count premium servers: {e}")
            return 0

    async def activate_server_premium(self, guild_id: int, server_id: str, activated_by: int, reason: Optional[str] = None) -> bool:
        """Activate premium for a server"""
        try:
            await self.server_premium_status.replace_one(
                {"guild_id": guild_id, "server_id": server_id},
                {
                    "guild_id": guild_id,
                    "server_id": server_id,
                    "is_active": True,
                    "activated_by": activated_by,
                    "activated_at": datetime.now(timezone.utc),
                    "reason": reason or "No reason provided",
                    "expires_at": None  # No expiration for now
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to activate server premium: {e}")
            return False

    async def deactivate_server_premium(self, guild_id: int, server_id: str, deactivated_by: int, reason: Optional[str] = None) -> bool:
        """Deactivate premium for a server"""
        try:
            await self.server_premium_status.update_one(
                {"guild_id": guild_id, "server_id": server_id},
                {
                    "$set": {
                        "is_active": False,
                        "deactivated_by": deactivated_by,
                        "deactivated_at": datetime.now(timezone.utc),
                        "deactivation_reason": reason or "No reason provided"
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate server premium: {e}")
            return False

    async def is_server_premium(self, guild_id: int, server_id: str) -> bool:
        """Check if a specific server is premium"""
        try:
            doc = await self.server_premium_status.find_one({
                "guild_id": guild_id,
                "server_id": server_id,
                "is_active": True,
                "$or": [
                    {"expires_at": {"$exists": False}},
                    {"expires_at": None},
                    {"expires_at": {"$gt": datetime.now(timezone.utc)}}
                ]
            })
            return doc is not None
        except Exception as e:
            logger.error(f"Failed to check server premium status: {e}")
            return False

    async def has_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access (any server is premium)"""
        try:
            count = await self.count_premium_servers(guild_id)
            return count > 0
        except Exception as e:
            logger.error(f"Failed to check premium access: {e}")
            return False

    async def list_premium_servers(self, guild_id: int) -> List[Dict[str, Any]]:
        """List all premium servers for guild"""
        try:
            cursor = self.server_premium_status.find({
                "guild_id": guild_id,
                "is_active": True
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Failed to list premium servers: {e}")
            return []

    # Missing methods required by cogs
    async def check_premium_server(self, guild_id: int, server_id: str = "default") -> bool:
        """Check if a server has premium access - required by economy and other cogs"""
        return await self.is_server_premium(guild_id, server_id)

    async def get_user_wallet(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Get user wallet data - required by gambling cogs"""
        return await self.get_wallet(guild_id, user_id)

    async def get_user_balance(self, guild_id: int, user_id: int) -> int:
        """Get user balance - required by gambling cogs"""
        try:
            wallet = await self.get_wallet(guild_id, user_id)
            return wallet.get('balance', 0) if wallet else 0
        except Exception as e:
            logger.error(f"Error getting user balance: {e}")
            return 0

    async def get_all_servers_with_killfeed(self) -> List[Dict[str, Any]]:
        """Get all servers that have killfeed enabled - required by killfeed parser"""
        try:
            servers = []
            async for guild_doc in self.guilds.find({}):
                guild_servers = guild_doc.get('servers', [])
                guild_channels = guild_doc.get('channels', {})  # Default guild channels
                
                for server in guild_servers:
                    server_channels = server.get('channels', {})
                    
                    # Check if killfeed channel is configured (server-specific or guild default)
                    has_killfeed = (
                        (server_channels and server_channels.get('killfeed')) or  # Server-specific killfeed
                        (guild_channels and guild_channels.get('killfeed'))       # Guild default killfeed
                    )
                    
                    if has_killfeed:
                        # Use server-specific channels if available, otherwise fall back to guild defaults
                        effective_channels = server_channels.copy() if server_channels else {}
                        if guild_channels:
                            for channel_type, channel_id in guild_channels.items():
                                if channel_type not in effective_channels:
                                    effective_channels[channel_type] = channel_id
                        
                        servers.append({
                            'guild_id': guild_doc['guild_id'],
                            'server_id': server.get('server_id', server.get('_id', 'default')),
                            'name': server.get('name', 'Unknown Server'),
                            'host': server.get('host', ''),
                            'port': server.get('port', 8822),
                            'username': server.get('username', ''),
                            'password': server.get('password', ''),
                            'channels': effective_channels
                        })
            return servers
        except Exception as e:
            logger.error(f"Error getting servers with killfeed: {e}")
            return []
            
    async def get_all_servers(self) -> List[Dict[str, Any]]:
        """Get all configured servers regardless of killfeed status"""
        try:
            servers = []
            async for guild_doc in self.guilds.find({}):
                guild_servers = guild_doc.get('servers', [])
                
                for server in guild_servers:
                    servers.append({
                        'guild_id': guild_doc['guild_id'],
                        'server_id': server.get('server_id', server.get('_id', 'default')),
                        'name': server.get('name', 'Unknown Server'),
                        'host': server.get('host', ''),
                        'port': server.get('port', 8822),
                        'username': server.get('username', ''),
                        'password': server.get('password', ''),
                        'channels': server.get('channels', {})
                    })
            return servers
        except Exception as e:
            logger.error(f"Error getting all servers: {e}")
            return []

    async def get_servers_for_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all servers for a specific guild - required by /online and other commands"""
        try:
            guild_doc = await self.guilds.find_one({'guild_id': guild_id})
            if not guild_doc:
                return []
            
            servers = []
            guild_servers = guild_doc.get('servers', [])
            for server in guild_servers:
                servers.append({
                    'guild_id': guild_id,
                    'server_id': server.get('server_id', server.get('_id', 'default')),
                    'name': server.get('name', f"Server {server.get('server_id', 'Unknown')}"),
                    'host': server.get('host', ''),
                    'port': server.get('port', 8822),
                    'username': server.get('username', ''),
                    'password': server.get('password', ''),
                    'channels': server.get('channels', {}),
                    'is_premium': server.get('is_premium', False)
                })
            return servers
        except Exception as e:
            logger.error(f"Error getting servers for guild {guild_id}: {e}")
            return []
    
    async def get_player_name_from_session(self, guild_id: int, eosid: str) -> Optional[str]:
        """Get player name from session data based on EOSID"""
        try:
            session = await self.player_sessions.find_one({
                "guild_id": guild_id,
                "player_id": eosid
            })
            return session.get("player_name") if session else None
        except Exception as e:
            logger.error(f"Failed to get player name for EOSID {eosid}: {e}")
            return None
    

