#!/usr/bin/env python3
"""
Migration: Add sensor_type column to all fault event tables in Neon.
Option A implementation -- keeps one table per fault, adds sensor identity column.
"""
import sys
import os
import psycopg2
from dotenv import load_dotenv

# Force UTF-8 output so unicode chars don't crash on Windows
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_ziolKjb53ZPY@ep-shiny-sound-apnhvmu6-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)

FAULT_TABLES = [
    'motor_bearing_failure',
    'motor_electrical_fault',
    'motor_overheating',
    'motor_shaft_misalignment',
    'motor_stall',
    'motor_vibration_anomaly',
    'motor_winding_failure',
    'pump_cavitation',
    'pump_impeller_damage',
    'pump_seal_leakage',
    'custom_fault',
]

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False

cur = conn.cursor()

print("=" * 60)
print("ADDING sensor_type COLUMN TO FAULT TABLES")
print("=" * 60)

for table in FAULT_TABLES:
    try:
        # Check if table exists first
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            );
        """, (table,))
        exists = cur.fetchone()[0]

        if not exists:
            print(f"  SKIP {table} -- table does not exist yet in Neon")
            continue

        # Check if column already exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'sensor_type'
            );
        """, (table,))
        col_exists = cur.fetchone()[0]

        if col_exists:
            print(f"  SKIP {table} -- sensor_type column already exists")
            continue

        cur.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN sensor_type VARCHAR(20)
                NOT NULL DEFAULT 'acceleration'
                CHECK (sensor_type IN ('acceleration', 'current', 'audio'));
        """)
        conn.commit()
        print(f"  OK   {table}")

    except Exception as e:
        conn.rollback()
        print(f"  ERR  {table} -- {e}")

cur.close()
conn.close()
print("\nDone.")
