#!/bin/bash

echo "========================================="
echo "  GreenOps Server Startup"
echo "========================================="
echo ""

cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from .env.example..."
    cp ../.env.example .env
    echo "✅ .env created. Please edit it with your settings."
    echo ""
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
echo "🚀 Starting GreenOps Server..."
echo ""
echo "Access points:"
echo "  • Main Dashboard: http://localhost:5000"
echo "  • Admin Dashboard: http://localhost:5000/admin"
echo "  • Login Page: http://localhost:5000/login"
echo ""
echo "Default credentials: admin / admin123"
echo ""

python app.py
