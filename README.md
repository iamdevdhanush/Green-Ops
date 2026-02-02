# GreenOps - Green IT Operations Platform

A production-ready centralized platform for monitoring, managing, and reducing energy waste across IT infrastructure.

## Features

- **Centralized Monitoring**: Track all PCs from a single dashboard
- **Auto-Registration**: Agents automatically register using MAC address
- **Real-time Status**: Monitor ACTIVE, IDLE, and OFFLINE machines
- **Energy Tracking**: Calculate and track energy waste from idle machines
- **Secure Authentication**: JWT-based authentication with role management
- **Professional UI**: Clean, responsive admin dashboard
- **Cross-platform Agent**: Works on Windows and Linux

## Technology Stack

- **Backend**: Python 3.10+, Flask, SQLAlchemy
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Authentication**: JWT tokens, bcrypt password hashing
- **Agent**: Python-based with psutil for system metrics

## Quick Start

### Option 1: Local Development (SQLite)

1. **Clone and Setup**
```bash
cd greenops
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env and set your secret keys
```

3. **Run Application**
```bash
python app.py
```

4. **Access Dashboard**
- Open browser: http://localhost:5000
- Default credentials: `admin` / `changeme`
- You will be prompted to change the password on first login

### Option 2: Docker Deployment (PostgreSQL)

1. **Build and Run**
```bash
docker-compose up -d
```

2. **Access Dashboard**
- Open browser: http://localhost:5000
- Default credentials: `admin` / `changeme`

3. **View Logs**
```bash
docker-compose logs -f app
```

4. **Stop Services**
```bash
docker-compose down
```

## Agent Installation

### On Client PCs

1. **Install Dependencies**
```bash
pip install requests psutil
```

2. **Copy Agent File**
Copy `agent.py` to the client PC

3. **Run Agent**
```bash
# Basic usage
python agent.py --server http://YOUR_SERVER_IP:5000

# Custom configuration
python agent.py \
  --server http://YOUR_SERVER_IP:5000 \
  --org PES \
  --department BCA \
  --lab LAB1 \
  --interval 60
```

4. **Verify Registration**
- Agent will auto-register on first run
- Check admin dashboard to see the new machine
- PC ID format: `ORG-DEPARTMENT-LAB-LAST4MAC`
  - Example: `PES-BCA-LAB1-19A7`

### Agent Parameters

- `--server`: GreenOps server URL (required)
- `--org`: Organization code (default: PES)
- `--department`: Department code (default: BCA)
- `--lab`: Lab name (default: LAB1)
- `--interval`: Update interval in seconds (default: 60)

## Configuration

### Environment Variables

Create a `.env` file with the following:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Database Configuration
# For PostgreSQL:
DATABASE_URL=postgresql://username:password@localhost:5432/greenops
# For SQLite:
DATABASE_URL=sqlite:///greenops.db

# Server Configuration
HOST=0.0.0.0
PORT=5000

# Green IT Configuration
IDLE_THRESHOLD_MINUTES=15
POWER_CONSUMPTION_WATTS=100
```

### Green IT Logic

**Idle Detection:**
- Machines are marked IDLE when inactive for ≥ IDLE_THRESHOLD_MINUTES
- Status automatically updates based on heartbeat data

**Energy Calculation:**
- Formula: (Power in kW) × (Idle time in hours) = Energy in kWh
- Default: 100W per machine (configurable)
- Only counts time above idle threshold

**Status Updates:**
- ACTIVE: Recently active, below idle threshold
- IDLE: Inactive for ≥ idle threshold
- OFFLINE: No heartbeat in last 5 minutes

## API Documentation

### Authentication

**POST /api/auth/login**
```json
{
  "username": "admin",
  "password": "your_password"
}
```

**POST /api/auth/change-password**
```json
{
  "username": "admin",
  "old_password": "current_password",
  "new_password": "new_password"
}
```

### Agent Endpoints

**POST /api/agent/register**
```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "pc_id": "PES-BCA-LAB1-19A7",
  "department": "BCA",
  "lab": "LAB1",
  "hostname": "PC-001",
  "os": "Windows 10"
}
```

**POST /api/agent/heartbeat**
```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "idle_time_minutes": 20
}
```

**POST /api/agent/metrics**
```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "idle_time_minutes": 20,
  "cpu_usage": 45.2,
  "memory_usage": 62.1,
  "disk_usage": 78.5
}
```

### Admin Endpoints

**GET /api/admin/machines**
- Returns: List of all machines
- Auth: Required (JWT)

**GET /api/admin/machine/<id>**
- Returns: Single machine details with metrics
- Auth: Required (JWT)

**GET /api/admin/stats**
- Returns: Dashboard statistics
- Auth: Required (JWT)

## Database Schema

### users
- id (Primary Key)
- username (Unique)
- password_hash
- role (ADMIN/AGENT)
- must_change_password
- created_at
- last_login

### machines
- id (Primary Key)
- pc_id
- mac_address (Unique)
- department
- lab
- hostname
- os
- status (ACTIVE/IDLE/OFFLINE)
- first_seen
- last_seen

### metrics
- id (Primary Key)
- machine_id (Foreign Key)
- idle_time_minutes
- cpu_usage
- memory_usage
- disk_usage
- energy_waste_kwh
- timestamp

## Security Features

- JWT-based authentication
- Bcrypt password hashing
- Forced password change on first login
- No hardcoded credentials
- Environment-based configuration
- Input validation on all endpoints

## Production Deployment

### Prerequisites
- Python 3.10 or higher
- PostgreSQL 12+ (recommended)
- Reverse proxy (nginx/Apache) for HTTPS

### Steps

1. **Server Setup**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb greenops
sudo -u postgres createuser greenops_user
sudo -u postgres psql
ALTER USER greenops_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE greenops TO greenops_user;
\q
```

2. **Application Setup**
```bash
# Clone repository
git clone <repository-url>
cd greenops

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit configuration
```

3. **Set Production Variables**
```bash
SECRET_KEY=<generate-strong-random-key>
JWT_SECRET_KEY=<generate-strong-random-key>
DATABASE_URL=postgresql://greenops_user:secure_password@localhost:5432/greenops
HOST=0.0.0.0
PORT=5000
```

4. **Run Application**
```bash
python app.py
```

5. **Setup as Service** (systemd)
```bash
sudo nano /etc/systemd/system/greenops.service
```

```ini
[Unit]
Description=GreenOps Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/greenops
Environment="PATH=/opt/greenops/venv/bin"
ExecStart=/opt/greenops/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable greenops
sudo systemctl start greenops
```

6. **Configure Nginx** (HTTPS)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Server won't start
- Check database connection in `.env`
- Ensure PostgreSQL is running
- Verify port 5000 is not in use

### Agent can't connect
- Verify server URL is correct
- Check firewall rules
- Ensure server is running

### Authentication fails
- Clear browser localStorage
- Reset admin password via database
- Check JWT_SECRET_KEY is set

### Database errors
- Run migrations if schema changed
- Check PostgreSQL logs
- Verify database credentials

## Monitoring

### Check Service Status
```bash
systemctl status greenops
```

### View Logs
```bash
journalctl -u greenops -f
```

### Database Backup
```bash
pg_dump greenops > backup.sql
```

## License

Proprietary - All rights reserved

## Support

For issues and feature requests, contact your system administrator.# Green-Ops
