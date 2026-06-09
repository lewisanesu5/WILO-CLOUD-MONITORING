#!/usr/bin/env python
"""Simple test to verify CSV saving on fault completion"""
import requests
import time
import os
import json

BASE_URL = 'http://localhost:5001'
FAULT_NAME = 'Motor Stall'

def test_csv_saving():
    print(f"Testing CSV saving for {FAULT_NAME}...")
    print("-" * 60)
    
    # Start the fault simulation
    print("\n1. Starting Motor Stall simulation...")
    start_response = requests.post(f'{BASE_URL}/simulate-event', 
                                   json={'event_name': FAULT_NAME})
    print(f"   Start response: {start_response.status_code}")
    if start_response.status_code != 200:
        print(f"   Error: {start_response.text}")
        return False
    
    # Wait for simulation to complete (max 3 minutes)
    print("\n2. Polling for completion (this may take 2-3 minutes)...")
    max_polls = 18  # 3 minutes max
    poll_count = 0
    failure_detected = False
    
    while poll_count < max_polls:
        time.sleep(10)  # Poll every 10 seconds
        poll_count += 1
        
        try:
            state_response = requests.get(f'{BASE_URL}/api/fault-state/{FAULT_NAME}')
            state_data = state_response.json()
            
            interval = state_data.get('interval_count', 0)
            failure = state_data.get('system_failure_state', False)
            print(f"   Poll #{poll_count}: Interval {interval}, Failure: {failure}")
            
            if failure:
                failure_detected = True
                print(f"   SUCCESS: Failure detected at interval {interval}")
                break
                
        except Exception as e:
            print(f"   Error polling: {e}")
            continue
    
    if not failure_detected:
        print("   ERROR: Simulation did not complete within timeout")
        return False
    
    # Give API a moment to save the CSV
    print("\n3. Waiting for CSV to be saved...")
    time.sleep(2)
    
    # Check if CSV file was created
    print("\n4. Checking for created CSV files...")
    data_dir = f'd:\\Wilo\\WILO-CLOUD-MONITORING\\Data\\{FAULT_NAME}'
    
    if not os.path.exists(data_dir):
        print(f"   ERROR: Data directory not created: {data_dir}")
        return False
    
    print(f"   Data directory exists: {data_dir}")
    
    files = os.listdir(data_dir)
    if not files:
        print(f"   ERROR: No files in data directory")
        return False
    
    print(f"   Files found: {len(files)}")
    for filename in files:
        filepath = os.path.join(data_dir, filename)
        size = os.path.getsize(filepath)
        print(f"   - {filename} ({size} bytes)")
        
        # Show first few lines of CSV
        if filename.endswith('.csv'):
            print(f"     First 3 lines:")
            with open(filepath, 'r') as f:
                for i, line in enumerate(f):
                    if i < 3:
                        print(f"     {line.rstrip()}")
                    else:
                        break
    
    print("\n" + "=" * 60)
    print("SUCCESS: CSV file saved successfully!")
    return True

if __name__ == '__main__':
    try:
        success = test_csv_saving()
        exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
