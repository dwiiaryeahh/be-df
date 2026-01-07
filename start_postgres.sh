#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}PostgreSQL Setup Script${NC}"
echo -e "${YELLOW}========================================${NC}"

# Configuration
DB_NAME="backpack_df"
DB_USER="backpack_user"
DB_PASS="b4cKpaCk_2026!@"
DB_HOST="localhost"
DB_PORT="5432"

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed. Please install PostgreSQL.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Creating PostgreSQL user and database...${NC}"

# Create database and user
# Note: This assumes the default postgres user can connect without password
# If you need to provide a password, modify the PGPASSWORD variable

psql -h $DB_HOST -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
psql -h $DB_HOST -U postgres << EOF
-- Create user if not exists
DO
\$do\$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
   END IF;
END
\$do\$;

-- Create database if not exists
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT USAGE ON SCHEMA public TO $DB_USER;
GRANT CREATE ON SCHEMA public TO $DB_USER;

EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database and user created/verified successfully${NC}"
else
    echo -e "${RED}✗ Error creating database or user${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 2: Creating tables...${NC}"

# Create tables using SQL
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME << 'EOF'

-- Create heartbeat table
CREATE TABLE IF NOT EXISTS heartbeat (
    source_ip VARCHAR NOT NULL PRIMARY KEY,
    state VARCHAR NOT NULL,
    temp VARCHAR NOT NULL,
    mode VARCHAR NOT NULL,
    ch VARCHAR NOT NULL,
    timestamp VARCHAR NOT NULL
);

-- Create campaign table
CREATE TABLE IF NOT EXISTS campaign (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    imsi VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    status VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index for campaign
CREATE INDEX IF NOT EXISTS idx_campaign_imsi ON campaign(imsi);
CREATE INDEX IF NOT EXISTS idx_campaign_name ON campaign(name);

-- Create crawling table
CREATE TABLE IF NOT EXISTS crawling (
    id SERIAL PRIMARY KEY,
    timestamp VARCHAR NOT NULL,
    rsrp VARCHAR NOT NULL,
    "taType" VARCHAR NOT NULL,
    "ulCqi" VARCHAR NOT NULL,
    "ulRssi" VARCHAR NOT NULL,
    imsi VARCHAR NOT NULL,
    ip VARCHAR NOT NULL,
    campaign_id INTEGER,
    FOREIGN KEY (campaign_id) REFERENCES campaign(id) ON DELETE CASCADE
);

-- Create indexes for crawling
CREATE INDEX IF NOT EXISTS idx_crawling_imsi ON crawling(imsi);
CREATE INDEX IF NOT EXISTS idx_crawling_ip ON crawling(ip);
CREATE INDEX IF NOT EXISTS idx_crawling_campaign_id ON crawling(campaign_id);

EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tables created successfully${NC}"
else
    echo -e "${RED}✗ Error creating tables${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 3: Verifying setup...${NC}"

# Verify tables exist
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\dt" 

echo -e ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ PostgreSQL setup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e ""
echo -e "Database credentials:"
echo -e "  Host: $DB_HOST"
echo -e "  Port: $DB_PORT"
echo -e "  Database: $DB_NAME"
echo -e "  User: $DB_USER"
echo -e "  Password: ••••••••••"
echo -e ""
echo -e "Connection string in .env:"
echo -e "  ${YELLOW}postgresql://$DB_USER:b4cKpaCk_2026!@$DB_HOST/$DB_NAME${NC}"
echo -e ""
echo -e "You can now start the application with: ${YELLOW}python run.py${NC}"
echo -e ""
