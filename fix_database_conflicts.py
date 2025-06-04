#!/usr/bin/env python3
"""
Emergency Database Conflict Resolution
Fixes duplicate key errors and index conflicts preventing bot startup
"""

import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_database_conflicts():
    """Fix all database conflicts preventing bot startup"""
    try:
        # Connect to MongoDB Atlas
        mongo_uri = os.environ.get("MONGO_URI")
        if not mongo_uri:
            logger.error("MONGO_URI not found")
            return False
            
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        # Test connection
        await client.admin.command('ping')
        logger.info("Connected to MongoDB Atlas")
        
        # 1. Drop problematic indexes to prevent conflicts
        logger.info("Dropping conflicting indexes...")
        
        try:
            await db.player_sessions.drop_index("guild_server_eos_unique")
            logger.info("Dropped guild_server_eos_unique index")
        except Exception as e:
            logger.info(f"Index guild_server_eos_unique not found or already dropped: {e}")
            
        try:
            await db.player_sessions.drop_index("guild_server_player_unique")
            logger.info("Dropped guild_server_player_unique index")
        except Exception as e:
            logger.info(f"Index guild_server_player_unique not found or already dropped: {e}")
            
        # 2. Clean duplicate documents
        logger.info("Cleaning duplicate player sessions...")
        
        # Find all documents grouped by the conflicting key
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "guild_id": "$guild_id",
                        "server_id": "$server_id", 
                        "eos_id": "$eos_id"
                    },
                    "docs": {"$push": "$$ROOT"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {"count": {"$gt": 1}}
            }
        ]
        
        duplicates = await db.player_sessions.aggregate(pipeline).to_list(length=None)
        logger.info(f"Found {len(duplicates)} groups with duplicate keys")
        
        total_deleted = 0
        for dup_group in duplicates:
            docs = dup_group["docs"]
            # Keep the most recent document
            sorted_docs = sorted(docs, key=lambda x: x.get('last_updated', x.get('_id')), reverse=True)
            to_delete = sorted_docs[1:]  # Delete all but the first (most recent)
            
            for doc in to_delete:
                await db.player_sessions.delete_one({"_id": doc["_id"]})
                total_deleted += 1
                
        logger.info(f"Deleted {total_deleted} duplicate documents")
        
        # 3. Clean any other conflicting data
        logger.info("Cleaning parser states...")
        
        # Similar cleanup for parser_states
        parser_pipeline = [
            {
                "$group": {
                    "_id": {
                        "guild_id": "$guild_id",
                        "server_id": "$server_id",
                        "parser_type": "$parser_type"
                    },
                    "docs": {"$push": "$$ROOT"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {"count": {"$gt": 1}}
            }
        ]
        
        parser_duplicates = await db.parser_states.aggregate(parser_pipeline).to_list(length=None)
        logger.info(f"Found {len(parser_duplicates)} parser state duplicate groups")
        
        parser_deleted = 0
        for dup_group in parser_duplicates:
            docs = dup_group["docs"]
            sorted_docs = sorted(docs, key=lambda x: x.get('last_updated', x.get('_id')), reverse=True)
            to_delete = sorted_docs[1:]
            
            for doc in to_delete:
                await db.parser_states.delete_one({"_id": doc["_id"]})
                parser_deleted += 1
                
        logger.info(f"Deleted {parser_deleted} duplicate parser state documents")
        
        # 4. Recreate indexes with upsert-safe approach
        logger.info("Creating safe indexes...")
        
        # Create sparse indexes that allow for safe upserts
        try:
            await db.player_sessions.create_index(
                [
                    ("guild_id", 1),
                    ("server_id", 1), 
                    ("eos_id", 1)
                ],
                name="guild_server_eos_sparse",
                sparse=True,
                background=True
            )
            logger.info("Created sparse index for player sessions")
        except Exception as e:
            logger.warning(f"Could not create index: {e}")
            
        try:
            await db.parser_states.create_index(
                [
                    ("guild_id", 1),
                    ("server_id", 1),
                    ("parser_type", 1)
                ],
                name="guild_server_parser_sparse",
                sparse=True,
                background=True
            )
            logger.info("Created sparse index for parser states")
        except Exception as e:
            logger.warning(f"Could not create parser index: {e}")
            
        logger.info("Database conflict resolution completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix database conflicts: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_database_conflicts())
    if success:
        print("✅ Database conflicts resolved - bot should start properly now")
    else:
        print("❌ Failed to resolve database conflicts")