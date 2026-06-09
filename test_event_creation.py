#!/usr/bin/env python
"""Test the new event creation from historical data endpoint"""
import requests
import json

BASE_URL = 'http://localhost:5001'

def test_event_creation_endpoint():
    print("Testing /api/create-event-from-history endpoint...")
    print("-" * 60)
    
    # Test with Motor Stall
    fault_name = "Motor Stall"
    payload = {
        'fault_name': fault_name
    }
    
    print(f"\n1. POST to /api/create-event-from-history")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/create-event-from-history',
            json=payload,
            timeout=30
        )
        
        print(f"\n2. Response Status: {response.status_code}")
        response_data = response.json()
        print(f"   Response Data:")
        for key, value in response_data.items():
            if key == 'files_created':
                print(f"     {key}:")
                for f in value:
                    print(f"       - {f}")
            else:
                print(f"     {key}: {value}")
        
        if response.status_code in [200, 201]:
            print("\n✓ SUCCESS: Event CSV files created")
            
            # Display created files
            if 'files_created' in response_data:
                print(f"\nCreated {len(response_data['files_created'])} files:")
                for filepath in response_data['files_created']:
                    print(f"  - {filepath}")
            
            return True
        else:
            print(f"\n✗ FAILED: Status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Backend not running on port 5001")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_event_creation_endpoint()
    exit(0 if success else 1)
