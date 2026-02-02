#!/usr/bin/env python3
"""
Quick fix script to regenerate database and fix JWT issues
"""

import os
import sys

print("=" * 60)
print("GreenOps Quick Fix Script")
print("=" * 60)

# Remove old database
if os.path.exists('greenops.db'):
    print("\n1. Removing old database...")
    os.remove('greenops.db')
    print("   ✓ Old database removed")
else:
    print("\n1. No old database found (skipping)")

# Update .env
print("\n2. Checking .env file...")
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        content = f.read()
    
    # Check if keys are too short
    if 'dev-secret-key-for-testing-only' in content and len('dev-secret-key-for-testing-only') < 32:
        print("   Updating .env with proper key lengths...")
        content = content.replace(
            'SECRET_KEY=dev-secret-key-for-testing-only',
            'SECRET_KEY=dev-secret-key-for-testing-only-change-this-in-production'
        )
        content = content.replace(
            'JWT_SECRET_KEY=dev-jwt-secret-for-testing-only',
            'JWT_SECRET_KEY=dev-jwt-secret-for-testing-only-change-this-in-production'
        )
        with open('.env', 'w') as f:
            f.write(content)
        print("   ✓ .env updated")
    else:
        print("   ✓ .env keys are good")
else:
    print("   ✗ .env not found - copying from .env.example")
    if os.path.exists('.env.example'):
        with open('.env.example', 'r') as f:
            content = f.read()
        with open('.env', 'w') as f:
            f.write(content)
        print("   ✓ .env created")

print("\n3. Ready to restart!")
print("\n" + "=" * 60)
print("Next steps:")
print("=" * 60)
print("1. Stop the server (Ctrl+C)")
print("2. Run: python app.py")
print("3. Login again (token will be regenerated)")
print("4. Dashboard should work now!")
print("=" * 60)
