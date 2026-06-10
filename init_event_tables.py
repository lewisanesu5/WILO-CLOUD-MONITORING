#!/usr/bin/env python3
"""
Initialize event-specific failure tables in Neon database.
Run this once to create all 11 failure-specific tables for storing event data.
"""

import psycopg2
from database import get_connection, FAILURE_TABLE_MAPPING
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Table schema for all failure-specific event tables
TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS {table_name} (
    {table_name}_id SERIAL PRIMARY KEY,
    fault_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    x_min FLOAT,
    x_max FLOAT,
    mean FLOAT,
    standard_deviation FLOAT,
    range FLOAT,
    variance FLOAT,
    skewness FLOAT,
    kurtosis FLOAT,
    frequency1 FLOAT,
    frequency2 FLOAT,
    frequency3 FLOAT,
    frequency4 FLOAT,
    frequency5 FLOAT,
    amplitude1 FLOAT,
    amplitude2 FLOAT,
    amplitude3 FLOAT,
    amplitude4 FLOAT,
    amplitude5 FLOAT
);

CREATE INDEX IF NOT EXISTS idx_{table_name}_fault_id ON {table_name}(fault_id);
CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp);
"""

def create_event_tables():
    """Create all 11 failure-specific event tables."""
    conn = None
    created_tables = []
    failed_tables = []
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        logger.info("=" * 60)
        logger.info("🚀 Initializing Event Tables in Neon Database")
        logger.info("=" * 60)
        
        for failure_name, table_name in FAILURE_TABLE_MAPPING.items():
            try:
                # Create table
                schema = TABLE_SCHEMA.format(table_name=table_name)
                cur.execute(schema)
                conn.commit()
                
                logger.info(f"✅ Table '{table_name}' ready")
                created_tables.append(table_name)
                
            except Exception as e:
                logger.error(f"❌ Error creating table '{table_name}': {e}")
                failed_tables.append((table_name, str(e)))
                conn.rollback()
        
        # Summary
        logger.info("=" * 60)
        logger.info(f"📊 Summary:")
        logger.info(f"   ✅ Created/Verified: {len(created_tables)}")
        logger.info(f"   ❌ Failed: {len(failed_tables)}")
        logger.info("=" * 60)
        
        if created_tables:
            logger.info("✅ Tables ready:")
            for table in created_tables:
                logger.info(f"   - {table}")
        
        if failed_tables:
            logger.error("❌ Failed tables:")
            for table, error in failed_tables:
                logger.error(f"   - {table}: {error}")
            return False
        
        logger.info("\n🎉 All event tables initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Fatal error initializing tables: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

if __name__ == '__main__':
    success = create_event_tables()
    exit(0 if success else 1)
