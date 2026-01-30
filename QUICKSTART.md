# GreenOps Quick Start Guide

This guide will help you get GreenOps up and running in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- (Optional) Docker and Docker Compose

## Option 1: Quick Local Setup (Recommended for Testing)

### Step 1: Start the Server

```bash
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

The server will start at `http://localhost:5000`

**Default credentials:**
- Username: `admin`
- Password: `changeme`

### Step 2: Start an Agent

Open a new terminal:

```bash
# Navigate to agent directory
cd agent

# Install dependencies
pip install -r requirements.txt

# Run the agent
python agent.py
```

### Step 3: View Dashboard

Open your browser and navigate to:
```
http://localhost:5000
```

You should see the GreenOps dashboard with real-time system monitoring!

## Option 2: Docker Setup (Recommended for Production)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access dashboard
# Open http://localhost:5000
```

## Option 3: Production Setup

### Server (Production)

1. **Set up PostgreSQL database:**
```bash
# Install PostgreSQL
sudo apt-get install postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE greenops;
CREATE USER greenops WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE greenops TO greenops;
\q
```

2. **Configure environment:**
```bash
cd server
cp .env.example .env
nano .env  # Edit with your settings
```

3. **Install and start:**
```bash
pip install -r requirements.txt
python app.py
# Or use gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Agent (Production)

#### Linux
```bash
cd agent
sudo ./install_service.sh
```

#### Windows
```cmd
cd agent
python install_service_windows.py install
python install_service_windows.py start
```

## Verification

### Check Server Health
```bash
curl http://localhost:5000/health
```

Should return:
```json
{
  "status": "ok",
  "version": "2.0.0",
  "database": "ok",
  "demo_mode": true
}
```

### Check Agent Connection
Look for agent reports in the dashboard or check logs:
```bash
# Agent logs
cat agent/greenops_agent.log

# Server logs
cat server/logs/greenops.log
```

## Configuration

### Agent Configuration
Edit `agent/config.json`:
```json
{
  "server_url": "http://localhost:5000",
  "idle_threshold_minutes": 15,
  "sleep_after_minutes": 30
}
```

### Server Configuration
Edit `server/.env`:
```env
DEMO_MODE=false  # Enable real power actions
CARBON_BUDGET_MONTHLY=5000
CO2_FACTOR=0.82
```

## Troubleshooting

### Agent can't connect to server
- Verify server is running: `curl http://localhost:5000/health`
- Check firewall settings
- Verify server URL in agent config.json

### "Permission denied" on Linux
- For system sleep, agent may need sudo privileges
- Configure sudoers or run as service (recommended)

### Database errors
- Ensure PostgreSQL is running
- Verify DATABASE_URL in .env
- Check database permissions

## Next Steps

1. **Change default password**: Log in and change admin password
2. **Configure policies**: Set up power management policies
3. **Add users**: Create accounts for team members
4. **Set budgets**: Configure carbon budgets for departments
5. **Deploy agents**: Install agents on all systems
6. **Monitor**: Watch the dashboard for carbon savings!

## Getting Help

- **Documentation**: See README.md for detailed docs
- **API Reference**: See API.md for API documentation
- **Issues**: https://github.com/yourusername/greenops/issues
- **Email**: support@greenops.io

## Success!

If you see systems reporting in the dashboard, congratulations! 🎉
You're now actively reducing your IT carbon footprint.

**Typical Results:**
- 40-60% reduction in idle system energy consumption
- ROI in 2-3 months for typical deployments
- Measurable carbon impact within first week
