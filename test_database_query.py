"""
Test database queries to verify data availability
"""

import sys
import os
from database import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_raw_database_queries():
    """Test raw SQL queries to each sensor table"""
    print("=" * 60)
    print("TEST 1: Raw Database Queries")
    print("=" * 60)
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        sensors = ['acceleration', 'current', 'audio']
        
        for sensor in sensors:
            print(f"\n🔍 Querying {sensor} table...")
            
            # First, check total count
            count_query = f"SELECT COUNT(*) FROM {sensor}"
            cur.execute(count_query)
            total_count = cur.fetchone()[0]
            print(f"  Total rows in {sensor}: {total_count}")
            
            # Check count by file_type
            file_type_query = f"SELECT file_type, COUNT(*) FROM {sensor} GROUP BY file_type"
            cur.execute(file_type_query)
            file_type_counts = cur.fetchall()
            print(f"  Rows by file_type:")
            for ft, count in file_type_counts:
                print(f"    {ft}: {count}")
            
            # Get sample data
            sample_query = f"""
                SELECT created_at, mean, x_max, standard_deviation, file_type
                FROM {sensor}
                WHERE file_type = 'max'
                ORDER BY created_at DESC
                LIMIT 3
            """
            cur.execute(sample_query)
            samples = cur.fetchall()
            
            if samples:
                print(f"  Latest 3 'max' records:")
                for row in samples:
                    print(f"    created_at: {row[0]}, mean: {row[1]}, max: {row[2]}, std_dev: {row[3]}, file_type: {row[4]}")
            else:
                print(f"  ⚠️  No 'max' records found!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_event_manager_loading():
    """Test _load_all_sensor_data() from event_manager"""
    print("\n" + "=" * 60)
    print("TEST 2: EventManager._load_all_sensor_data()")
    print("=" * 60)
    
    try:
        from event_manager import EventManager
        
        em = EventManager('Events', 'Data')
        print("\n🔍 Loading sensor data...")
        data = em._load_all_sensor_data()
        
        for sensor_type in ['acceleration', 'current', 'audio']:
            count = len(data.get(sensor_type, []))
            print(f"  {sensor_type}: {count} records loaded")
            
            if count > 0:
                first = data[sensor_type][0]
                print(f"    First record timestamp: {first.get('timestamp')}")
                print(f"    Features present: {len(first)} fields")
        
        total = sum(len(data.get(s, [])) for s in ['acceleration', 'current', 'audio'])
        print(f"\n✓ Total records loaded: {total}")
        return total > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_historical_statistics():
    """Test get_historical_statistics() from app"""
    print("\n" + "=" * 60)
    print("TEST 3: app.get_historical_statistics()")
    print("=" * 60)
    
    try:
        from app import get_historical_statistics
        
        print("\n🔍 Loading historical statistics...")
        data = get_historical_statistics(limit=100)
        
        for sensor_type in ['acceleration', 'current', 'audio']:
            count = len(data.get(sensor_type, []))
            print(f"  {sensor_type}: {count} records")
            
            if count > 0:
                first = data[sensor_type][0]
                print(f"    First record timestamp: {first.get('timestamp')}")
                print(f"    Features: mean={first.get('mean')}, max={first.get('max')}, std_dev={first.get('std_dev')}")
        
        total = sum(len(data.get(s, [])) for s in ['acceleration', 'current', 'audio'])
        print(f"\n✓ Total records loaded: {total}")
        return total > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("DATABASE QUERY VERIFICATION TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    results.append(("Raw SQL Queries", test_raw_database_queries()))
    results.append(("EventManager Loading", test_event_manager_loading()))
    results.append(("Historical Statistics", test_get_historical_statistics()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Data is available and queryable")
    else:
        print("✗ SOME TESTS FAILED - Data loading issue detected")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
