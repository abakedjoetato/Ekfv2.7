"""
Investigate Rate Limit Sources - Find what's causing Discord message flooding
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, '.')

async def investigate_rate_limits():
    """Investigate sources of Discord rate limiting"""
    print("INVESTIGATING DISCORD RATE LIMIT SOURCES")
    print("=" * 50)
    
    try:
        # Import modules
        from bot.models.database import DatabaseManager
        import motor.motor_asyncio
        
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        await mongo_client.admin.command('ping')
        
        db_manager = DatabaseManager(mongo_client)
        
        # Check recent message activity
        guild_id = 1219706687980568769
        
        print("1. CHECKING DATABASE FOR MESSAGE PATTERNS")
        print("-" * 40)
        
        # Check for rapid event generation
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        
        # Look for parser state changes indicating frequent processing
        parser_states = await db_manager.parser_states.find({
            'guild_id': guild_id
        }).to_list(length=10)
        
        print(f"Parser states found: {len(parser_states)}")
        for state in parser_states:
            print(f"  Server: {state.get('server_name', 'Unknown')}")
            print(f"  Last position: {state.get('last_position', 0)}")
            print(f"  Last line: {state.get('last_line', 0)}")
            print(f"  Last updated: {state.get('last_updated', 'Unknown')}")
            print()
        
        print("2. ANALYZING LOG PARSER ACTIVITY")
        print("-" * 40)
        
        # Check if there are rapid log parsing cycles
        import re
        import subprocess
        
        # Get recent log entries about message sending
        try:
            result = subprocess.run(
                ["tail", "-n", "200", "bot.log"], 
                capture_output=True, 
                text=True
            )
            
            log_lines = result.stdout.split('\n')
            
            # Count message-related activities
            embed_sends = 0
            channel_lookups = 0
            mission_events = 0
            
            for line in log_lines:
                if "embed" in line.lower() and "sent" in line.lower():
                    embed_sends += 1
                if "channel lookup" in line.lower():
                    channel_lookups += 1
                if "mission" in line.lower() and "ready" in line.lower():
                    mission_events += 1
            
            print(f"Recent activity in logs:")
            print(f"  Embed sends: {embed_sends}")
            print(f"  Channel lookups: {channel_lookups}")
            print(f"  Mission events: {mission_events}")
            
            # Look for rapid succession events
            mission_times = []
            for line in log_lines:
                if "Mission" in line and "ready" in line:
                    # Extract timestamp
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        try:
                            timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                            mission_times.append(timestamp)
                        except:
                            pass
            
            # Check for rapid mission events (potential flooding)
            if len(mission_times) > 1:
                mission_times.sort()
                rapid_events = 0
                for i in range(1, len(mission_times)):
                    time_diff = (mission_times[i] - mission_times[i-1]).total_seconds()
                    if time_diff < 5:  # Less than 5 seconds between events
                        rapid_events += 1
                
                print(f"  Rapid mission events (< 5s apart): {rapid_events}")
                if rapid_events > 3:
                    print("  ⚠️ WARNING: High frequency mission events detected!")
            
        except Exception as e:
            print(f"Error analyzing logs: {e}")
        
        print("\n3. CHECKING SCHEDULER FREQUENCY")
        print("-" * 40)
        
        # The issue might be in scheduler intervals
        print("Current parser intervals:")
        print("  Unified log parser: 180 seconds (3 minutes)")
        print("  Killfeed parser: 300 seconds (5 minutes)")
        
        # Check if parsers are running too frequently
        print("\n4. EXAMINING CHANNEL ROUTING")
        print("-" * 40)
        
        # Check channel configuration
        guild_doc = await db_manager.get_guild(guild_id)
        if guild_doc:
            channels = guild_doc.get('channels', {})
            print(f"Configured channels: {len(channels)}")
            
            # Check for multiple channels configured for same event type
            event_types = {}
            for channel_id, config in channels.items():
                event_type = config.get('type', 'unknown')
                if event_type not in event_types:
                    event_types[event_type] = []
                event_types[event_type].append(channel_id)
            
            for event_type, channel_list in event_types.items():
                print(f"  {event_type}: {len(channel_list)} channels")
                if len(channel_list) > 1:
                    print(f"    ⚠️ Multiple channels for {event_type}: {channel_list}")
        
        print("\n5. POTENTIAL RATE LIMIT SOURCES")
        print("-" * 40)
        
        potential_issues = []
        
        if embed_sends > 20:
            potential_issues.append("High embed sending frequency")
        
        if mission_events > 10:
            potential_issues.append("Excessive mission event generation")
        
        if channel_lookups > 50:
            potential_issues.append("Excessive channel lookup calls")
        
        # Check for duplicate event sending
        if any(len(channels) > 1 for channels in event_types.values()):
            potential_issues.append("Multiple channels configured for same event type")
        
        if not potential_issues:
            potential_issues.append("Rate limiting may be from external factors")
        
        print("Identified issues:")
        for issue in potential_issues:
            print(f"  • {issue}")
        
        print("\n6. RECOMMENDATIONS")
        print("-" * 40)
        
        recommendations = []
        
        if embed_sends > 20:
            recommendations.append("Implement message rate limiting/queuing")
        
        if mission_events > 10:
            recommendations.append("Add cooldown between mission event sends")
        
        if any(len(channels) > 1 for channels in event_types.values()):
            recommendations.append("Consolidate duplicate channel configurations")
        
        recommendations.append("Add Discord API rate limit handling")
        recommendations.append("Implement message batching for multiple events")
        
        print("Recommended fixes:")
        for rec in recommendations:
            print(f"  • {rec}")
        
        return potential_issues, recommendations
        
    except Exception as e:
        print(f"Error in rate limit investigation: {e}")
        import traceback
        traceback.print_exc()
        return [], []

if __name__ == "__main__":
    asyncio.run(investigate_rate_limits())