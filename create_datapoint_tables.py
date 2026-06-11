#!/usr/bin/env python3
"""Create datapoint tables in Neon database for raw sensor data storage"""

import psycopg2

conn_string = 'postgresql://neondb_owner:npg_ziolKjb53ZPY@ep-shiny-sound-apnhvmu6-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

try:
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    print("=" * 70)
    print("CREATING DATAPOINT TABLES IN NEON")
    print("=" * 70)
    
    # SQL to create the three datapoint tables
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            batch VARCHAR(20) NOT NULL CHECK (batch IN ('max', 'min', 'combined')),
            datapoints FLOAT8[] NOT NULL,
            datapoint_timestamps BIGINT[] NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_{table_name}_batch_created 
        ON {table_name}(batch, created_at DESC);
        
        CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp 
        ON {table_name}(timestamp DESC);
    """
    
    tables = ['acceleration_datapoints', 'current_datapoints', 'audio_datapoints']
    
    for table in tables:
        try:
            sql = create_table_sql.format(table_name=table)
            cur.execute(sql)
            print(f"✓ Created table: {table}")
        except psycopg2.Error as e:
            if 'already exists' in str(e):
                print(f"⚠ Table already exists: {table}")
            else:
                print(f"✗ Error creating {table}: {e}")
    
    conn.commit()
    print("\n" + "=" * 70)
    print("✅ DATAPOINT TABLES CREATED SUCCESSFULLY")
    print("=" * 70)
    
    # Show table structure
    print("\nTable Structure:")
    cur.execute("""
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name IN ('acceleration_datapoints', 'current_datapoints', 'audio_datapoints')
        ORDER BY table_name, ordinal_position
    """)
    
    current_table = None
    for row in cur.fetchall():
        table_name, col_name, data_type = row
        if current_table != table_name:
            print(f"\n{table_name}:")
            current_table = table_name
        print(f"  - {col_name}: {data_type}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
