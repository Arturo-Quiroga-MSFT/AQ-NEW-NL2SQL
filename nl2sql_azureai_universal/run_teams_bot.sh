#!/bin/bash

# run_teams_bot.sh - Helper script to run the NL2SQL Teams Bot
# This script activates the virtual environment and starts the bot server

echo "🤖 Starting NL2SQL Teams Bot..."
echo ""

# Check if .venv exists
if [ ! -d "../.venv" ]; then
    echo "❌ Error: Virtual environment not found at ../.venv"
    echo "Please create a virtual environment first:"
    echo "  python -m venv ../.venv"
    echo "  source ../.venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source ../.venv/bin/activate

# Check if microsoft_agents is installed
python -c "import microsoft_agents" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: Microsoft Agents SDK not installed"
    echo "Please install the required packages:"
    echo "  pip install -i https://test.pypi.org/simple/ microsoft-agents-core"
    echo "  pip install -i https://test.pypi.org/simple/ microsoft-agents-authorization"
    echo "  pip install -i https://test.pypi.org/simple/ microsoft-agents-connector"
    echo "  pip install -i https://test.pypi.org/simple/ microsoft-agents-builder"
    echo "  pip install -i https://test.pypi.org/simple/ microsoft-agents-authentication-msal"
    echo "  pip install -i https://test.pypi.org/simple/ microsoft-agents-hosting-aiohttp"
    exit 1
fi

echo "✓ Microsoft Agents SDK found"
echo "✓ Starting bot server..."
echo ""

# Start the bot
python start_server.py
