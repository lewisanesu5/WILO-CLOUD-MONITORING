#!/usr/bin/env python3
import time
import requests

print('[TEST] Waiting 70 seconds for more intervals...')
time.sleep(70)

print('\n[TEST] Checking fault state...')
try:
    resp = requests.get('http://localhost:5001/api/fault-state/Motor%20Stall', timeout=5)
    data = resp.json()
    print(f'Intervals: {data.get("interval_count", 0)}')
    print(f'Failure State: {data.get("system_failure_state")}')
    print(f'Is Generating: {data.get("is_generating")}')
    print(f'Failure Interval: {data.get("failure_interval")}')
except Exception as e:
    print(f'Error: {e}')
