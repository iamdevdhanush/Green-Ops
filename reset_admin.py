#!/usr/bin/env python3
from werkzeug.security import generate_password_hash
import sqlite3

# Connect to database
conn = sqlite3.connect('greenops.db')
cursor = conn.cursor()

# Delete old admin
cursor.execute("DELETE FROM users WHERE username='admin'")

# Create new admin with password 'changeme'
password_hash = generate_password_hash('changeme')
cursor.execute("""
    INSERT INTO users (username, password_hash, role, must_change_password)
    VALUES (?, ?, 'ADMIN', 1)
""", ('admin', password_hash))

conn.commit()
conn.close()

print("✓ Admin user reset successfully")
print("Username: admin")
print("Password: changeme")
print("You will be prompted to change password on first login")
