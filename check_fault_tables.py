#!/usr/bin/env python3
"""Quick check: show sample rows from fault tables to verify sensor_type is being stored correctly."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_ziolKjb53ZPY@ep-shiny-sound-apnhvmu6-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)

FAULT_TABLES = [
    'motor_bearing_failure','motor_electrical_fault','motor_overheating',
    'motor_shaft_misalignment','motor_stall','motor_vibration_anomaly',
    'motor_winding_failure','pump_cavitation','pump_impeller_damage',
    'pump_seal_leakage','custom_fault',
]

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 70)
print("FAULT TABLE ROW COUNTS + sensor_type DISTRIBUTION")
print("=" * 70)

for table in FAULT_TABLES:
    cur.execute(f"SELECT COUNT(*) AS total FROM {table};")
    total = cur.fetchone()['total']

    if total == 0:
        print(f"  {table:<35} rows=0  (empty)")
        continue

    cur.execute(f"""
        SELECT sensor_type, COUNT(*) AS cnt
        FROM {table}
        GROUP BY sensor_type
        ORDER BY sensor_type;
    """)
    breakdown = cur.fetchall()
    breakdown_str = ', '.join(f"{r['sensor_type']}:{r['cnt']}" for r in breakdown)
    print(f"  {table:<35} rows={total:<4} breakdown=[{breakdown_str}]")

cur.close()
conn.close()
print("\nDone.")
