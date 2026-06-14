#!/usr/bin/env python3
"""
Diagnostic + Fix: Check all fault tables in Neon and ensure sensor_type column exists.
Creates missing tables and adds sensor_type where absent.
"""
import sys
import os
import psycopg2

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
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

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS {table} (
        {table}_id SERIAL PRIMARY KEY,
        fault_id INTEGER,
        sensor_type VARCHAR(20) NOT NULL DEFAULT 'acceleration'
            CHECK (sensor_type IN ('acceleration', 'current', 'audio')),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        x_min DOUBLE PRECISION,
        x_max DOUBLE PRECISION,
        mean DOUBLE PRECISION,
        standard_deviation DOUBLE PRECISION,
        range DOUBLE PRECISION,
        variance DOUBLE PRECISION,
        skewness DOUBLE PRECISION,
        kurtosis DOUBLE PRECISION,
        frequency1 DOUBLE PRECISION,
        frequency2 DOUBLE PRECISION,
        frequency3 DOUBLE PRECISION,
        frequency4 DOUBLE PRECISION,
        frequency5 DOUBLE PRECISION,
        amplitude1 DOUBLE PRECISION,
        amplitude2 DOUBLE PRECISION,
        amplitude3 DOUBLE PRECISION,
        amplitude4 DOUBLE PRECISION,
        amplitude5 DOUBLE PRECISION,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""

conn = psycopg2.connect(DATABASE_URL)

print("=" * 70)
print("FAULT TABLE AUDIT")
print("=" * 70)

for table in FAULT_TABLES:
    cur = conn.cursor()

    # 1. Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        );
    """, (table,))
    exists = cur.fetchone()[0]

    if not exists:
        # Create it with sensor_type
        try:
            cur.execute(CREATE_TABLE_SQL.format(table=table))
            conn.commit()
            print(f"  CREATED  {table}  (new, includes sensor_type)")
        except Exception as e:
            conn.rollback()
            print(f"  ERROR    {table}  create failed: {e}")
        cur.close()
        continue

    # 2. Table exists - check for sensor_type column
    cur.execute("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
    """, (table,))
    columns = cur.fetchall()
    col_names = [c[0] for c in columns]

    has_sensor_type = 'sensor_type' in col_names

    if has_sensor_type:
        print(f"  OK       {table}  (sensor_type present)")
    else:
        # Add sensor_type
        try:
            cur.execute(f"""
                ALTER TABLE {table}
                ADD COLUMN sensor_type VARCHAR(20)
                    NOT NULL DEFAULT 'acceleration'
                    CHECK (sensor_type IN ('acceleration', 'current', 'audio'));
            """)
            conn.commit()
            print(f"  ALTERED  {table}  (sensor_type added)")
        except Exception as e:
            conn.rollback()
            print(f"  ERROR    {table}  alter failed: {e}")

    cur.close()

print("\n" + "=" * 70)
print("VERIFYING FINAL STATE")
print("=" * 70)

cur = conn.cursor()
cur.execute("""
    SELECT t.table_name,
           bool_or(c.column_name = 'sensor_type') AS has_sensor_type,
           COUNT(c.column_name) AS total_columns
    FROM information_schema.tables t
    JOIN information_schema.columns c ON c.table_name = t.table_name AND c.table_schema = 'public'
    WHERE t.table_schema = 'public'
      AND t.table_name = ANY(%s)
    GROUP BY t.table_name
    ORDER BY t.table_name;
""", (FAULT_TABLES,))

rows = cur.fetchall()
for row in rows:
    table_name, has_st, col_count = row
    status = "OK" if has_st else "MISSING sensor_type"
    print(f"  {table_name:<35} columns={col_count:<3} sensor_type={status}")

cur.close()
conn.close()
print("\nDone.")
