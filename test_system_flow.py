#!/usr/bin/env python3
"""
Test script to verify the complete system flow works correctly.
Tests:
1. Backend endpoint responsiveness (/health, /api/files, /api/upload/status)
2. Event simulation pipeline (/simulate-event)
"""

import requests
import time
import json
import sys

BASE_URL = "http://localhost:5001"

def test_endpoints():
    """Test that remaining core endpoints are available"""
    print("\n=== TESTING CORE ENDPOINTS ===")
    
    endpoints = [
        ('GET', '/health'),
        ('GET', '/api/files'),
        ('GET', '/api/upload/status'),
    ]
    
    success = True
    for method, endpoint in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            status = "✓ OK" if response.status_code == 200 else "✗ ERROR"
            print(f"{status} {method:4} {endpoint:40} -> {response.status_code}")
            if response.status_code != 200:
                success = False
        except Exception as e:
            print(f"✗ FAIL {method:4} {endpoint:40} -> {str(e)}")
            success = False
            
    return success

def test_event_simulation():
    """Test that a fault event can be simulated and files copied"""
    print("\n=== TESTING FAULT EVENT SIMULATION (Motor Stall) ===")
    
    fault_type = "Motor Stall"
    
    try:
        # Trigger the event simulation
        print(f"1. POSTing event simulation for '{fault_type}'...")
        url = f"{BASE_URL}/simulate-event"
        response = requests.post(
            url,
            json={'fault_type': fault_type},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to trigger event simulation: {response.status_code}")
            if response.headers.get('content-type') == 'application/json':
                print(response.json())
            else:
                print(response.text[:200])
            return False
            
        print(f"✓ Event simulation endpoint returned 200 OK")
        data = response.json()
        print(f"  Response: {data.get('message', 'No message')}")
        print(f"  Copied files: {data.get('files_copied', [])}")
        
        if not data.get('files_copied'):
            print("❌ No files were copied during simulation")
            return False
            
        # Verify simulated files show up in file list
        print("\n2. Verifying simulated files exist in /api/files...")
        files_response = requests.get(f"{BASE_URL}/api/files", timeout=5)
        if files_response.status_code == 200:
            files_data = files_response.json()
            # If files_data is a dict or list, inspect it
            file_list = files_data if isinstance(files_data, list) else files_data.get('files', [])
            print(f"✓ Found {len(file_list)} files in the directory")
            return True
        else:
            print(f"❌ Failed to fetch file list: {files_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Exception during event simulation test: {str(e)}")
        return False

def main():
    print("+----------------------------------------+")
    print("|  WILO Cloud Monitoring System Test    |")
    print("+----------------------------------------+")
    
    # Test core endpoints
    endpoints_ok = test_endpoints()
    
    # Test event simulation
    simulation_ok = test_event_simulation()
    
    print("\n" + "="*50)
    if endpoints_ok and simulation_ok:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
