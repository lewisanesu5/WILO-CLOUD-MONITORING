#!/usr/bin/env python3
"""
Test script to verify event creation from history creates folders and CSVs
"""
import requests
import os
import json
from pathlib import Path
import sys

# Fix encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Backend URL
API_URL = "https://wilo-cloud-monitoring.onrender.com"

def test_event_creation():
    """Test creating an event and verify folders/CSVs are created"""
    
    fault_name = "Motor Stall"
    
    print(f"\n{'='*70}")
    print(f"Testing Event Creation: {fault_name}")
    print(f"{'='*70}\n")
    
    # Test 1: Create event via API
    print(f"[*] Creating event for: {fault_name}")
    print(f"    POST to: {API_URL}/api/create-event-from-history")
    
    try:
        response = requests.post(
            f"{API_URL}/api/create-event-from-history",
            json={"fault_name": fault_name},
            timeout=30
        )
        
        print(f"    Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"    [SUCCESS]\n")
            print(f"Response Data:")
            print(json.dumps(data, indent=4))
            
            if data.get('success'):
                print(f"\n[*] Event Details:")
                print(f"    - Fault Name: {data.get('fault_name')}")
                print(f"    - Data Directory: {data.get('data_dir')}")
                print(f"    - Event Directory: {data.get('event_dir')}")
                print(f"    - Files Created: {len(data.get('files_created', []))}")
                print(f"    - Deviation Points: {data.get('deviation_points')}")
                print(f"    - Intervals Extracted: {data.get('intervals_extracted')}")
                
                # Check if CSV data is in response
                if 'csv_data' in data:
                    print(f"\n[*] CSV DATA IN RESPONSE: YES")
                    print(f"    Sensors with CSV data: {list(data['csv_data'].keys())}")
                    for sensor, csv_content in data['csv_data'].items():
                        lines = csv_content.count('\n')
                        print(f"    - {sensor}: {lines} lines")
                else:
                    print(f"\n[*] CSV DATA IN RESPONSE: NO")
                
                print(f"\n[*] Created Files:")
                for file in data.get('files_created', []):
                    print(f"    - {file}")
                
                return True
            else:
                print(f"    [FAILED] API returned success=false")
                print(f"    Error: {data.get('error')}")
                return False
        else:
            print(f"    [FAILED] Status {response.status_code}")
            print(f"    Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"    [FAILED] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_event_creation()
    print(f"\n{'='*70}")
    print(f"Test Result: {'[PASSED]' if success else '[FAILED]'}")
    print(f"{'='*70}\n")
