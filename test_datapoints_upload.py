#!/usr/bin/env python3
"""
Test script to generate mock sensor data, upload it to the server,
and verify that raw datapoints are saved correctly in Neon database.
"""

import os
import time
import requests
import json
import numpy as np

# Config
SERVER_URL = "https://wilo-cloud-monitoring.onrender.com"
API_KEY = "sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b"  # Key for sensor-001
TEST_DIR = "./test_sensor_data"

def check_server():
    try:
        resp = requests.get(f"{SERVER_URL}/health", timeout=3)
        return resp.status_code == 200
    except:
        return False

def generate_mock_csvs():
    os.makedirs(TEST_DIR, exist_ok=True)
    
    # 2 seconds of data at 700Hz = 1400 points
    t = np.linspace(0, 2, 1400)
    
    # Mock data for acceleration
    # Max file has larger amplitude + noise
    max_vals = 1.5 * np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 0.2, 1400)
    # Min file has smaller amplitude
    min_vals = 0.5 * np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 0.1, 1400)
    
    # Use current time in ms
    base_time = int(time.time() * 1000)
    timestamps = [base_time + int(x * 1000) for x in t]
    
    max_path = os.path.join(TEST_DIR, "max_acceleration.csv")
    with open(max_path, "w") as f:
        f.write("timestamp,value\n")
        for ts, val in zip(timestamps, max_vals):
            f.write(f"{ts},{val}\n")
            
    min_path = os.path.join(TEST_DIR, "min_acceleration.csv")
    with open(min_path, "w") as f:
        f.write("timestamp,value\n")
        for ts, val in zip(timestamps, min_vals):
            f.write(f"{ts},{val}\n")
            
    return max_path, min_path

def run_test():
    print("=" * 60)
    print("DATAPOINTS UPLOAD VERIFICATION TEST")
    print("=" * 60)
    
    if not check_server():
        print(f"[FAIL] Server is not running at {SERVER_URL}!")
        print("Please start the backend (e.g., run 'python app.py') before running this test.")
        return False
        
    print("[OK] Server is reachable")
    
    # 1. Get initial diagnostic table counts
    print("\n1. Fetching current database status...")
    try:
        resp = requests.get(f"{SERVER_URL}/api/db-diagnostic", timeout=5)
        if resp.status_code != 200:
            print(f"[FAIL] Failed to query db-diagnostic: {resp.status_code}")
            return False
        diag_before = resp.json()
        counts_before = diag_before.get("sensor_record_counts", {})
        print("Initial Datapoint Counts:")
        for t in ['acceleration_datapoints', 'current_datapoints', 'audio_datapoints']:
            print(f"  - {t}: {counts_before.get(t, 0)}")
    except Exception as e:
        print(f"[FAIL] Exception querying db-diagnostic: {e}")
        return False
        
    # 2. Generate files
    print("\n2. Generating mock sensor data files...")
    max_file, min_file = generate_mock_csvs()
    print(f"  Generated: {max_file}")
    print(f"  Generated: {min_file}")
    
    # 3. Upload files
    print(f"\n3. Uploading acceleration files to {SERVER_URL}/api/upload...")
    headers = {"X-API-Key": API_KEY}
    files = [
        ("files", (os.path.basename(max_file), open(max_file, "rb"), "text/csv")),
        ("files", (os.path.basename(min_file), open(min_file, "rb"), "text/csv"))
    ]
    
    try:
        resp = requests.post(f"{SERVER_URL}/api/upload", headers=headers, files=files, timeout=10)
        
        # Close file handles
        for f in files:
            f[1][1].close()
            
        if resp.status_code != 201:
            print(f"[FAIL] Upload failed with status {resp.status_code}!")
            print(f"Response: {resp.text}")
            return False
            
        upload_result = resp.json()
        print("[OK] Upload response indicates success!")
        print(f"  Message: {upload_result.get('message')}")
        print(f"  Database records saved count: {upload_result.get('database_records_saved')}")
    except Exception as e:
        print(f"[FAIL] Exception during upload: {e}")
        return False
        
    # Wait a moment for db write processing to fully complete
    time.sleep(1.5)
    
    # 4. Check diagnostic endpoint again
    print("\n4. Verifying database state post-upload...")
    try:
        resp = requests.get(f"{SERVER_URL}/api/db-diagnostic", timeout=5)
        if resp.status_code != 200:
            print(f"[FAIL] Failed to query db-diagnostic: {resp.status_code}")
            return False
        diag_after = resp.json()
        counts_after = diag_after.get("sensor_record_counts", {})
        
        print("Updated Datapoint Counts:")
        success = True
        for t in ['acceleration_datapoints', 'current_datapoints', 'audio_datapoints']:
            before = counts_before.get(t, 0)
            after = counts_after.get(t, 0)
            diff = after - before if isinstance(after, int) and isinstance(before, int) else 0
            print(f"  - {t}: {before} -> {after} (diff: +{diff})")
            if t == 'acceleration_datapoints':
                # We expect 3 records (max, min, combined) to be added
                if diff == 3:
                    print(f"    [OK] SUCCESS: Exactly 3 records (max, min, combined) were inserted into {t}!")
                else:
                    print(f"    [FAIL] ERROR: Expected +3 records for {t}, but got +{diff}")
                    success = False
                    
        if success:
            print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY! Datapoints are properly reflecting in the database.")
            # Clean up files
            try:
                os.remove(max_file)
                os.remove(min_file)
                os.rmdir(TEST_DIR)
            except:
                pass
            return True
        else:
            print("\n[FAIL] SOME VERIFICATIONS FAILED.")
            return False
    except Exception as e:
        print(f"[FAIL] Exception checking post-upload status: {e}")
        return False

if __name__ == "__main__":
    import sys
    sys.exit(0 if run_test() else 1)
