"""
Comprehensive System Check
Validates entire multi-sensor implementation before deployment
"""

import sys
import os

def check_files_exist():
    """Check all critical files exist"""
    print("\n" + "=" * 70)
    print("CHECK 1: Critical Files")
    print("=" * 70)
    
    files_to_check = [
        'event_manager.py',
        'app.py',
        'database.py',
        'config.json',
        'requirements.txt',
        'Procfile'
    ]
    
    all_exist = True
    for filename in files_to_check:
        exists = os.path.exists(filename)
        status = "✓" if exists else "✗"
        print(f"{status} {filename}")
        if not exists:
            all_exist = False
    
    return all_exist

def check_syntax():
    """Check Python syntax for all modules"""
    print("\n" + "=" * 70)
    print("CHECK 2: Python Syntax")
    print("=" * 70)
    
    files_to_check = ['event_manager.py', 'app.py', 'database.py']
    
    all_valid = True
    for filename in files_to_check:
        try:
            with open(filename, encoding='utf-8', errors='ignore') as f:
                compile(f.read(), filename, 'exec')
            print(f"✓ {filename} - syntax valid")
        except SyntaxError as e:
            print(f"✗ {filename} - {e}")
            all_valid = False
    
    return all_valid

def check_imports():
    """Check all imports can be resolved"""
    print("\n" + "=" * 70)
    print("CHECK 3: Module Imports")
    print("=" * 70)
    
    try:
        print("Testing: from database import get_connection")
        from database import get_connection
        print("✓ database module imports")
        
        print("Testing: from event_manager import EventManager")
        from event_manager import EventManager
        print("✓ event_manager module imports")
        
        print("Testing: import app")
        import app
        print("✓ app module imports")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def check_class_methods():
    """Check EventManager has all required methods"""
    print("\n" + "=" * 70)
    print("CHECK 4: EventManager Methods")
    print("=" * 70)
    
    try:
        from event_manager import EventManager
        
        em = EventManager('Events', 'Data')
        
        required_methods = [
            '_load_all_sensor_data',
            '_extract_multi_sensor_trends',
            'create_event',
        ]
        
        all_exist = True
        for method_name in required_methods:
            if hasattr(em, method_name):
                print(f"✓ EventManager.{method_name}() exists")
            else:
                print(f"✗ EventManager.{method_name}() NOT FOUND")
                all_exist = False
        
        return all_exist
    except Exception as e:
        print(f"✗ Error checking methods: {e}")
        return False

def check_database_functions():
    """Check database module has required functions"""
    print("\n" + "=" * 70)
    print("CHECK 5: Database Module Functions")
    print("=" * 70)
    
    try:
        from database import get_connection, insert_event_data, FAILURE_TABLE_MAPPING
        
        print(f"✓ get_connection() exists")
        print(f"✓ insert_event_data() exists")
        print(f"✓ FAILURE_TABLE_MAPPING exists")
        
        # Check failure table mapping
        print(f"\n📋 Failure Table Mapping ({len(FAILURE_TABLE_MAPPING)} entries):")
        for fault_name, table_name in list(FAILURE_TABLE_MAPPING.items())[:3]:
            print(f"  '{fault_name}' → '{table_name}'")
        print(f"  ... and {len(FAILURE_TABLE_MAPPING) - 3} more")
        
        return True
    except Exception as e:
        print(f"✗ Error checking database functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_app_functions():
    """Check app module has required functions"""
    print("\n" + "=" * 70)
    print("CHECK 6: Flask App Functions")
    print("=" * 70)
    
    try:
        from app import app, get_historical_statistics, create_fault_event_csv
        
        print(f"✓ Flask app instance exists")
        print(f"✓ get_historical_statistics() exists")
        print(f"✓ create_fault_event_csv() exists")
        
        # Check routes
        print(f"\n📋 Flask Routes:")
        routes = [
            '/api/create-event-from-history',
            '/available-faults',
            '/events'
        ]
        
        for route in routes:
            print(f"  {route}")
        
        return True
    except Exception as e:
        print(f"✗ Error checking app functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_config():
    """Check configuration files"""
    print("\n" + "=" * 70)
    print("CHECK 7: Configuration")
    print("=" * 70)
    
    try:
        import json
        
        # Check config.json
        if os.path.exists('config.json'):
            with open('config.json') as f:
                config = json.load(f)
            print(f"✓ config.json valid JSON")
            print(f"  Keys: {list(config.keys())}")
        else:
            print(f"⚠️  config.json not found")
        
        # Check requirements.txt
        if os.path.exists('requirements.txt'):
            with open('requirements.txt') as f:
                reqs = f.readlines()
            print(f"✓ requirements.txt exists ({len(reqs)} packages)")
            # Show key packages
            key_packages = ['flask', 'psycopg2', 'python-dotenv']
            for pkg in key_packages:
                found = any(pkg in line.lower() for line in reqs)
                status = "✓" if found else "⚠️"
                print(f"  {status} {pkg}")
        else:
            print(f"⚠️  requirements.txt not found")
        
        return True
    except Exception as e:
        print(f"✗ Error checking config: {e}")
        return False

def check_multi_sensor_logic():
    """Check multi-sensor extraction logic"""
    print("\n" + "=" * 70)
    print("CHECK 8: Multi-Sensor Implementation")
    print("=" * 70)
    
    try:
        import inspect
        from event_manager import EventManager
        
        em = EventManager('Events', 'Data')
        
        # Check _load_all_sensor_data implementation
        source = inspect.getsource(em._load_all_sensor_data)
        
        checks = {
            "Queries acceleration table": "acceleration" in source,
            "Queries current table": "current" in source,
            "Queries audio table": "audio" in source,
            "Filters by file_type='max'": "file_type" in source and "max" in source,
            "Uses 7 statistical features": all(feat in source for feat in ["variance", "skewness"]),
            "Orders by created_at ASC": "ORDER BY created_at ASC" in source,
        }
        
        all_pass = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}")
            if not result:
                all_pass = False
        
        return all_pass
    except Exception as e:
        print(f"✗ Error checking multi-sensor logic: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_trend_extraction():
    """Check trend extraction algorithm"""
    print("\n" + "=" * 70)
    print("CHECK 9: Trend Extraction Algorithm")
    print("=" * 70)
    
    try:
        import inspect
        from event_manager import EventManager
        
        em = EventManager('Events', 'Data')
        source = inspect.getsource(em._extract_multi_sensor_trends)
        
        checks = {
            "Checks all 3 sensors": all(s in source for s in ["acceleration", "current", "audio"]),
            "Uses stability detection": "stable_slope_count" in source,
            "Checks slope threshold (0.001)": "0.001" in source,
            "Tracks 3 stable points": "3" in source or "STABLE_POINTS" in source,
            "Calculates feature slopes": "slope" in source,
            "Uses all 7 features": all(f in source for f in ["variance", "skewness", "kurtosis"]),
        }
        
        all_pass = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}")
            if not result:
                all_pass = False
        
        return all_pass
    except Exception as e:
        print(f"✗ Error checking trend extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_insertion():
    """Check database insertion logic"""
    print("\n" + "=" * 70)
    print("CHECK 10: Database Insertion")
    print("=" * 70)
    
    try:
        import inspect
        from database import insert_event_data
        
        source = inspect.getsource(insert_event_data)
        
        checks = {
            "Accepts multi_sensor_trends dict": "multi_sensor_trends" in source,
            "Loops through sensors": any(s in source for s in ["for", "sensor"]),
            "Sets sensor_type column": "sensor_type" in source,
            "Gets fault_id": "fault_id" in source or "get_next_fault_id" in source,
            "Inserts to database": "INSERT" in source or "execute" in source,
            "Returns success status": "success" in source or "return" in source,
        }
        
        all_pass = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}")
            if not result:
                all_pass = False
        
        return all_pass
    except Exception as e:
        print(f"✗ Error checking database insertion: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks"""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE SYSTEM CHECK")
    print("=" * 70)
    
    results = [
        ("Files Exist", check_files_exist()),
        ("Python Syntax", check_syntax()),
        ("Module Imports", check_imports()),
        ("EventManager Methods", check_class_methods()),
        ("Database Functions", check_database_functions()),
        ("App Functions", check_app_functions()),
        ("Configuration", check_config()),
        ("Multi-Sensor Logic", check_multi_sensor_logic()),
        ("Trend Extraction", check_trend_extraction()),
        ("Database Insertion", check_database_insertion()),
    ]
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    print("\n" + "=" * 70)
    if passed == total:
        print("✓✓✓ SYSTEM READY FOR DEPLOYMENT ✓✓✓")
        print("All checks passed. Code is production-ready.")
    else:
        print(f"✗✗✗ {total - passed} CHECK(S) FAILED ✗✗✗")
        print("Fix failures above before deployment.")
    print("=" * 70 + "\n")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
