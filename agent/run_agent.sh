#!/bin/bash

echo "========================================="
echo "  GreenOps Agent Startup"
echo "========================================="
echo ""

cd "$(dirname "$0")"

# Check if config.json exists
if [ ! -f config.json ]; then
    echo "⚠️  config.json not found!"
    echo "Creating config.json from config.example.json..."
    cp config.example.json config.json
    echo "✅ config.json created"
    echo ""
    echo "⚠️  IMPORTANT: Edit config.json and set:"
    echo "   • server_url (your GreenOps server)"
    echo "   • organization (e.g., 'PES')"
    echo "   • department (e.g., 'BCA')"
    echo "   • lab (e.g., 'LAB1')"
    echo ""
    read -p "Press Enter to continue after editing config.json..."
fi

# Check if venv exists
if [ ! -d venv ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "🚀 Starting GreenOps Agent..."
echo ""

python agent.py
