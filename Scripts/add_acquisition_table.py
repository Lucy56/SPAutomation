#!/usr/bin/env python3
from pg_schema_enhanced import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Create customer acquisition tracking table
cursor.execute("""
CREATE TABLE IF NOT EXISTS customer_acquisition (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,

    -- Metrics
    new_customers INTEGER DEFAULT 0,
    first_orders INTEGER DEFAULT 0,
    first_order_revenue NUMERIC(12, 2) DEFAULT 0,

    -- Calculated at
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date, utm_source, utm_medium, utm_campaign)
)
""")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_acquisition_date ON customer_acquisition(date)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_acquisition_source ON customer_acquisition(utm_source)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_acquisition_campaign ON customer_acquisition(utm_campaign)')

conn.commit()
cursor.close()
conn.close()

print('✅ Added customer_acquisition table for tracking new customers by source daily')
