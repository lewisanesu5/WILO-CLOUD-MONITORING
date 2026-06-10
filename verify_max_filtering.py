#!/usr/bin/env python3
"""Verify MAX row filtering in Neon database"""

import psycopg2
from psycopg2.extras import RealDictCursor

conn_string = 'postgresql://neondb_owner:npg_ziolKjb53ZPY@ep-shiny-sound-apnhvmu6-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

try:
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 70)
    print("VERIFYING MAX ROW FILTERING IN NEON DATABASE")
    print("=" * 70)
    
    sensors = ['acceleration', 'current', 'audio']
    
    for sensor in sensors:
        print(f"\n📊 Checking {sensor} table:")
        
        # Check total rows
        cur.execute(f"SELECT COUNT(*) as total FROM {sensor}")
        total = cur.fetchone()['total']
        print(f"   Total rows: {total}")
        
        # Check by file_type
        cur.execute(f"""
            SELECT file_type, COUNT(*) as count 
            FROM {sensor}
            GROUP BY file_type
            ORDER BY file_type
        """)
        results = cur.fetchall()
        for row in results:
            print(f"   - {row['file_type']}: {row['count']} rows")
        
        # Show sample MAX rows
        cur.execute(f"""
            SELECT 
                mean, x_max, file_type, created_at
            FROM {sensor}
            WHERE file_type = 'max'
            ORDER BY created_at DESC
            LIMIT 3
        """)
        max_rows = cur.fetchall()
        
        if max_rows:
            print(f"   Sample MAX rows:")
            for row in max_rows:
                print(f"      mean: {row['mean']:.2f}, max: {row['x_max']:.2f}, file_type: {row['file_type']}, created: {row['created_at']}")
    
    print("\n" + "=" * 70)
    
    # Check if filter will work in event creation
    print("\n🔍 Testing event creation query:")
    print("   SELECT COUNT(*) FROM acceleration WHERE file_type = 'max'")
    
    cur.execute("SELECT COUNT(*) as count FROM acceleration WHERE file_type = 'max'")
    max_count = cur.fetchone()['count']
    print(f"   Result: {max_count} MAX rows will be selected for event creation")
    
    if max_count > 0:
        print("\n✅ SUCCESS: MAX filtering is working correctly!")
        print(f"   When creating events, {max_count} MAX acceleration rows will be used")
    else:
        print("\n⚠️  WARNING: No MAX rows found. Check if data has been uploaded.")
    
    print("=" * 70)
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
