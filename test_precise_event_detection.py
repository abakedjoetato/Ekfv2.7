#!/usr/bin/env python3
"""
Test Precise Event Detection - Verify all SFPS event patterns work correctly
"""
import asyncio
import os
import sys

# Add the bot directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor

async def test_precise_event_detection():
    """Test precise event detection patterns against real log samples"""
    
    # Initialize processor
    guild_id = 1315008007830650941
    processor = ScalableUnifiedProcessor(guild_id)
    
    # Test airdrop patterns
    airdrop_samples = [
        "[2025.06.03-11.53.57:725][315]LogSFPS: Airdrop spawned at X=12345.0 Y=67890.0",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Air drop event at coordinates X=9876.5 Y=5432.1",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Supply drop landed at X=1111.1 Y=2222.2 Z=333.3"
    ]
    
    # Test helicrash patterns
    helicrash_samples = [
        "[2025.06.03-11.53.57:725][315]LogSFPS: Helicopter crashed at X=4444.4 Y=5555.5",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Heli crash site spawned X=7777.7 Y=8888.8",
        "[2025.06.03-11.53.57:725][315]LogSFPS: HeliCrash event at location X=9999.9 Y=1010.1"
    ]
    
    # Test mission patterns
    mission_samples = [
        "[2025.06.03-11.53.57:725][315]LogSFPS: Mission status changed to READY at X=1234.5 Y=6789.0",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Mission event: Type=Elimination Status=READY Location=X=5678.9 Y=9012.3",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Mission objective activated X=2468.1 Y=1357.9"
    ]
    
    # Test trader patterns
    trader_samples = [
        "[2025.06.03-11.53.57:725][315]LogSFPS: Trader post available at X=1111.2 Y=3333.4",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Trading zone active X=5555.6 Y=7777.8",
        "[2025.06.03-11.53.57:725][315]LogSFPS: Merchant location X=9999.0 Y=1111.1"
    ]
    
    test_cases = [
        ("Airdrop", airdrop_samples),
        ("Helicrash", helicrash_samples), 
        ("Mission", mission_samples),
        ("Trader", trader_samples)
    ]
    
    print("🔍 Testing Precise Event Detection Patterns")
    print("=" * 50)
    
    for event_type, samples in test_cases:
        print(f"\n📋 Testing {event_type} Events:")
        print("-" * 30)
        
        for i, sample in enumerate(samples, 1):
            result = processor._classify_log_entry(sample)
            if result:
                entry_type, player_name, data = result
                print(f"  Sample {i}: ✅ Detected as '{entry_type}'")
                if data and 'x_coordinate' in data:
                    print(f"    📍 Coordinates: X={data['x_coordinate']}, Y={data['y_coordinate']}")
                else:
                    print(f"    📄 Data: {data}")
            else:
                print(f"  Sample {i}: ❌ Not detected")
    
    print("\n" + "=" * 50)
    print("✅ Precise Event Detection Test Complete")

if __name__ == "__main__":
    asyncio.run(test_precise_event_detection())