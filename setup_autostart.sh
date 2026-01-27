#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Settin up DF-Backpack Auto-start...${NC}"

# Get current user and directory
CURRENT_USER=$(whoami)
PROJECT_DIR=$(pwd)

# Prepare service file from template
SERVICE_FILE="df-backpack.service"
cp df-backpack.service.template $SERVICE_FILE

# Replace placeholders
sed -i "s|{{USER}}|$CURRENT_USER|g" $SERVICE_FILE
sed -i "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" $SERVICE_FILE

# Also update start_app.sh PROJECT_DIR
sed -i "s|PROJECT_DIR=.*|PROJECT_DIR=\"$PROJECT_DIR\"|g" start_app.sh

# Make start_app.sh executable
chmod +x start_app.sh

echo -e "${YELLOW}Installing systemd service...${NC}"

# Copy to systemd directory
sudo cp $SERVICE_FILE /etc/systemd/system/

# Reload systemd, enable and start service
sudo systemctl daemon-reload
sudo systemctl enable df-backpack
sudo systemctl start df-backpack

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ DF-Backpack service installed and started successfully!${NC}"
    echo -e "${GREEN}✓ It will now start automatically on every boot.${NC}"
    echo -e "${YELLOW}Check status with: ${NC}systemctl status df-backpack"
else
    echo -e "${RED}✗ Failed to install or start the service.${NC}"
    exit 1
fi
