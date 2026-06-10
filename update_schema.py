#!/usr/bin/env python3
"""Update Neon database schema to add file_type column"""

import psycopg2

# Connection string
conn_string = 'postgresql://neondb_owner:npg_ziolKjb53ZPY@ep-shiny-sound-apnhvmu6-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

try:
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    tables = ['acceleration', 'current', 'audio']
    
    for table in tables:
        try:
            # Add file_type column
            alter_query = f"ALTER TABLE {table} ADD COLUMN file_type VARCHAR(20) DEFAULT 'max';"
            cur.execute(alter_query)
            print(f'✓ Added file_type column to {table} table')
        except psycopg2.Error as e:
            if 'already exists' in str(e):
                print(f'⚠ file_type column already exists in {table} table')
            else:
                print(f'✗ Error adding column to {table}: {e}')
    
    conn.commit()
    cur.close()
    conn.close()
    print('\n✓ Database schema updated successfully!')
    
except psycopg2.OperationalError as e:
    print(f'✗ Connection error: {e}')
except Exception as e:
    print(f'✗ Error: {e}')
