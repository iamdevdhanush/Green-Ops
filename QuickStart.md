# GreenOps - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (1 minute)

```bash
cd greenops
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure (30 seconds)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and change these lines:
SECRET_KEY=your-random-secret-key-here
JWT_SECRET_KEY=your-random-jwt-key-here

# Generate random keys:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### Step 3: Start Server (10 seconds)

```bash
python app.py
```

You should see:
```
============================================================
GreenOps Server Starting
============================================================
Host: 0.0.0.0
Port: 5000
Database: sqlite:///greenops.db
============================================================

✓ Default admin user created (username: admin, password: changeme)
⚠ Please change the default password on first login!
✓ Database initialized successfully
```

### Step 4: Access Dashboard (30 seconds)

1. Open browser: **http://localhost:5000**
2. Login: **admin** / **changeme**
3. Change password (required on first login)
4. View dashboard

### Step 5: Run Agent on Client PC (2 minutes)

```bash
# Install dependencies
pip install requests psutil

# Run agent
python agent.py --server http://YOUR_SERVER_IP:5000
```

You should see:
```
============================================================
GreenOps Agent Started
============================================================
PC ID: PES-BCA-LAB1-19A7
MAC Address: AA:BB:CC:DD:19:A7
Server: http://localhost:5000
Update Interval: 60 seconds
============================================================

✓ Registered successfully as PES-BCA-LAB1-19A7
  MAC: AA:BB:CC:DD:19:A7
  Hostname: YOUR-PC-NAME

Monitoring started. Press Ctrl+C to stop.
```

### Step 6: Verify (30 seconds)

1. Refresh dashboard
2. You should see your PC listed
3. Status should be **ACTIVE**
4. Metrics should update every minute

---

## 📋 Default Configuration

| Setting | Default Value | Description |
|---------|---------------|-------------|
| Host | 0.0.0.0 | Listen on all interfaces |
| Port | 5000 | Server port |
| Database | SQLite | For development |
| Idle Threshold | 15 minutes | When to mark PC as idle |
| Power Consumption | 100 watts | For energy calculations |
| Update Interval | 60 seconds | Agent update frequency |

---

## 🔧 Common Tasks

### Change Admin Password
1. Go to dashboard
2. Logout
3. Login again
4. Or use API:
```bash
curl -X POST http://localhost:5000/api/auth/change-password \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "old_password": "current",
    "new_password": "new_password"
  }'
```

### Run Agent as Background Service

**Linux:**
```bash
# Create service
sudo nano /etc/systemd/system/greenops-agent.service

# Add:
[Unit]
Description=GreenOps Agent

[Service]
ExecStart=/usr/bin/python3 /path/to/agent.py --server http://SERVER:5000
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable greenops-agent
sudo systemctl start greenops-agent
```

**Windows:**
Use Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start program
5. Program: `python.exe`
6. Arguments: `C:\path\to\agent.py --server http://SERVER:5000`

### View All Machines
```bash
curl http://localhost:5000/api/admin/machines \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Server Logs
```bash
# If running directly
tail -f output.log

# If using systemd
sudo journalctl -u greenops -f
```

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check Python version (needs 3.10+)
python3 --version

# Check port is free
netstat -tlnp | grep 5000

# Run with verbose errors
python app.py
```

### Agent can't connect
```bash
# Test server is reachable
curl http://SERVER_IP:5000

# Check firewall
sudo ufw allow 5000/tcp

# Verify server is running
ps aux | grep python
```

### Can't login
```bash
# Reset admin password in database
# For SQLite:
sqlite3 greenops.db
UPDATE users SET must_change_password = 1 WHERE username = 'admin';
.quit

# Clear browser cache/cookies
# Try incognito mode
```

---

## 📚 Next Steps

- Read [README.md](README.md) for complete documentation
- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- Read [VERIFICATION.md](VERIFICATION.md) for testing checklist
- Deploy agents to all client PCs
- Configure automated backups
- Setup HTTPS with nginx
- Monitor energy savings

---

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] Can login to dashboard
- [ ] Changed default password
- [ ] Agent registers successfully
- [ ] Machine appears in dashboard
- [ ] Status updates work
- [ ] Metrics are collected
- [ ] Energy calculations shown

**If all checked ✓ - You're ready to go!**

---

## 🆘 Need Help?

1. Check the logs
2. Read DEPLOYMENT.md
3. Review VERIFICATION.md
4. Check API responses
5. Verify network connectivity

---

**GreenOps is now running! Start monitoring your IT infrastructure for energy waste.**
