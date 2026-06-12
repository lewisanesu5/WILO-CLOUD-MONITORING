"""
Test Multi-Sensor Trend Extraction Implementation
Validates that all components work together correctly
"""

import sys
from event_manager import EventManager
from database import get_connection
from datetime import datetime, timedelta

def test_database_connection():
    """Test database connectivity"""
    print("=" * 60)
    print("TEST 1: Database Connection")
    print("=" * 60)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Test query to acceleration table
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM acceleration 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        result = cursor.fetchone()
        count = result[0] if result else 0
        print(f"✓ Database connected")
        print(f"✓ Acceleration table has {count} rows (last 24 hours)")
        
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_load_sensor_data():
    """Test loading sensor data from database"""
    print("\n" + "=" * 60)
    print("TEST 2: Load Multi-Sensor Data")
    print("=" * 60)
    try:
        em = EventManager('Events', 'Data')
        data = em._load_all_sensor_data()
        
        if not data:
            print("✗ No sensor data loaded")
            return False
        
        # Check all 3 sensors
        sensors = ['acceleration', 'current', 'audio']
        all_present = True
        
        for sensor in sensors:
            if sensor in data and data[sensor]:
                points = len(data[sensor])
                first_point = data[sensor][0]
                features = list(first_point.keys())
                print(f"✓ {sensor.capitalize()}: {points} points loaded")
                print(f"  Features present: {len(features)} ({', '.join(sorted(features)[:5])}...)")
            else:
                print(f"✗ {sensor.capitalize()}: No data")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"✗ Data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extract_trends():
    """Test multi-sensor trend extraction"""
    print("\n" + "=" * 60)
    print("TEST 3: Extract Multi-Sensor Trends")
    print("=" * 60)
    try:
        em = EventManager('Events', 'Data')
        data = em._load_all_sensor_data()
        
        if not data or not data.get('acceleration'):
            print("✗ No data available for extraction")
            return False
        
        # Extract trends
        trends = em._extract_multi_sensor_trends(data)
        
        if not trends:
            print("✗ No trends extracted")
            return False
        
        sensors = ['acceleration', 'current', 'audio']
        all_extracted = True
        
        for sensor in sensors:
            if sensor in trends and trends[sensor]:
                points = len(trends[sensor])
                first_point = trends[sensor][0]
                has_slopes = 'mean_slope' in first_point
                print(f"✓ {sensor.capitalize()}: {points} trend points")
                print(f"  Slopes calculated: {has_slopes}")
            else:
                print(f"✗ {sensor.capitalize()}: No trends extracted")
                all_extracted = False
        
        return all_extracted
    except Exception as e:
        print(f"✗ Trend extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_create_event():
    """Test end-to-end event creation"""
    print("\n" + "=" * 60)
    print("TEST 4: Create Event (End-to-End)")
    print("=" * 60)
    try:
        em = EventManager('Events', 'Data')
        
        # Create a test event
        failure_time = datetime.now() - timedelta(hours=1)  # 1 hour ago
        failure_time_iso = failure_time.isoformat()
        
        result = em.create_event(
            event_name='Motor Stall',
            failure_time_iso=failure_time_iso,
            description='Test multi-sensor event'
        )
        
        if result.get('success'):
            print(f"✓ Event created successfully")
            print(f"  Event ID: {result.get('event_id')}")
            print(f"  Fault ID: {result.get('fault_id')}")
            print(f"  Total rows inserted: {result.get('total_rows_inserted')}")
            print(f"  Rows per sensor: {result.get('rows_per_sensor')}")
            return True
        else:
            print(f"✗ Event creation failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"✗ Event creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\nMULTI-SENSOR TREND EXTRACTION - IMPLEMENTATION TEST SUITE\n")
    
    results = []
    results.append(("Database Connection", test_database_connection()))
    results.append(("Load Sensor Data", test_load_sensor_data()))
    results.append(("Extract Trends", test_extract_trends()))
    results.append(("Create Event", test_create_event()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("=" * 60))
    if all_passed:
        print("✓ ALL TESTS PASSED - Implementation ready for deployment")
    else:
        print("✗ SOME TESTS FAILED - Review errors above")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
