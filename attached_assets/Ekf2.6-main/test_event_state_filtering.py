"""
Test Event State Filtering - Verify that events only output once per occurrence
Test missions (READY only), airdrops (Flying only), helicrashes/traders (spawn only)
"""

import asyncio
import re
from datetime import datetime
from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor


async def test_event_state_filtering():
    """Test that event state filtering works correctly"""
    print("=== Testing Event State Filtering System ===\n")
    
    # Mock bot for testing
    class MockBot:
        def __init__(self):
            pass
    
    bot = MockBot()
    processor = ScalableUnifiedProcessor(bot)
    
    # Test log lines for different event states (matching actual regex patterns)
    test_lines = [
        # Mission events - should only output READY state (mission_start)
        "[2025-06-04 12:00:00] LogSFPS: Mission GA_Bunker_Raid_5 switched to READY",
        "[2025-06-04 12:05:00] LogSFPS: Mission GA_Bunker_Raid_5 switched to WAITING",
        "[2025-06-04 12:10:00] LogSFPS: Mission GA_Military_Base_4 switched to READY",
        "[2025-06-04 12:15:00] LogSFPS: Mission GA_Small_Outpost_2 switched to READY",  # Level 2 - should be filtered
        
        # Airdrop events - should only output Flying state
        "[2025-06-04 13:00:00] LogSFPS: AirDrop switched to Flying",
        "[2025-06-04 13:05:00] LogSFPS: AirDrop switched to Dropping",
        "[2025-06-04 13:10:00] LogSFPS: AirDrop switched to Dead",
        "[2025-06-04 13:15:00] LogSFPS: AirDrop switched to Flying",
        
        # Helicrash events - should only output ready/spawn state
        "[2025-06-04 14:00:00] LogSFPS: Helicopter crash site switched to READY",
        "[2025-06-04 14:05:00] LogSFPS: Helicopter site crash occurred",
        
        # Trader events - should only output arrival state
        "[2025-06-04 15:00:00] LogSFPS: Trader convoy arrived at checkpoint",
        "[2025-06-04 15:30:00] LogSFPS: Trader convoy departure initiated",
        
        # Vehicle events - should output all (no state filtering)
        "[2025-06-04 16:00:00] LogSFPS: [ASFPSGameMode::NewVehicle_Add] Add vehicle Pickup_01 Total 15",
        "[2025-06-04 16:05:00] LogSFPS: [ASFPSGameMode::DelVehicle] Remove vehicle Total 14"
    ]
    
    print("Processing test log lines...\n")
    
    valid_events = []
    filtered_events = []
    
    for line in test_lines:
        result = processor.parse_log_line(line)
        
        if result is None:
            filtered_events.append(line)
            print(f"❌ FILTERED: {line.split('] ')[1] if '] ' in line else line}")
        else:
            valid_events.append(result)
            event_type = result.get('event_type', 'unknown')
            print(f"✅ PASSED: {event_type} - {line.split('] ')[1] if '] ' in line else line}")
    
    print(f"\n=== Results Summary ===")
    print(f"✅ Valid events (will generate embeds): {len(valid_events)}")
    print(f"❌ Filtered events (blocked): {len(filtered_events)}")
    
    print(f"\n=== Event Details ===")
    for event in valid_events:
        event_type = event.get('event_type', 'unknown')
        if 'mission_name' in event:
            print(f"Mission: {event['mission_name']} (Level {event['mission_level']}) - State: {event['mission_state']}")
        elif 'airdrop_state' in event:
            print(f"Airdrop: State {event['airdrop_state']} - Priority: {event['event_priority']}")
        elif 'helicrash_state' in event:
            print(f"Helicrash: State {event['helicrash_state']} - Priority: {event['event_priority']}")
        elif 'trader_state' in event:
            print(f"Trader: State {event['trader_state']} - Priority: {event['event_priority']}")
        elif 'vehicle_action' in event:
            print(f"Vehicle: {event['vehicle_action']} - Count: {event['vehicle_count']}")
    
    print(f"\n=== Filtering Verification ===")
    print("✅ Missions: Only READY state (level 3+) should pass")
    print("✅ Airdrops: Only Flying state should pass")
    print("✅ Helicrashes: Only READY/spawn state should pass")
    print("✅ Traders: Only arrival state should pass")
    print("✅ Vehicles: All states should pass (no filtering)")
    
    # Verify filtering rules
    mission_events = [e for e in valid_events if 'mission_name' in e]
    airdrop_events = [e for e in valid_events if 'airdrop_state' in e]
    helicrash_events = [e for e in valid_events if 'helicrash_state' in e]
    trader_events = [e for e in valid_events if 'trader_state' in e]
    vehicle_events = [e for e in valid_events if 'vehicle_action' in e]
    
    print(f"\n=== Final Counts ===")
    print(f"Mission events passed: {len(mission_events)} (should be 2 - level 3+ only)")
    print(f"Airdrop events passed: {len(airdrop_events)} (should be 2 - Flying only)")
    print(f"Helicrash events passed: {len(helicrash_events)} (should be 1 - READY only)")
    print(f"Trader events passed: {len(trader_events)} (should be 1 - arrival only)")
    print(f"Vehicle events passed: {len(vehicle_events)} (should be 2 - all pass)")
    
    # Verification
    expected_total = 2 + 2 + 1 + 1 + 2  # 8 total events should pass
    if len(valid_events) == expected_total:
        print(f"\n🎉 SUCCESS: Event state filtering working correctly!")
        print(f"   Expected {expected_total} events to pass, got {len(valid_events)}")
    else:
        print(f"\n⚠️  WARNING: Expected {expected_total} events to pass, got {len(valid_events)}")


if __name__ == "__main__":
    asyncio.run(test_event_state_filtering())