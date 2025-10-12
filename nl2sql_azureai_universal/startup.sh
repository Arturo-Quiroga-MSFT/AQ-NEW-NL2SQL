#!/bin/bash
# startup.sh - Azure App Service startup script

echo "=========================================="
echo "Starting NL2SQL Teams Bot on Azure"
echo "=========================================="

# Activate virtual environment if it exists
if [ -d "/home/site/wwwroot/antenv" ]; then
    source /home/site/wwwroot/antenv/bin/activate
fi

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Change to app directory
cd /home/site/wwwroot

# Start the bot server
echo "Starting bot server..."
python start_server.py
