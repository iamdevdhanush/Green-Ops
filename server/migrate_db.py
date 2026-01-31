"""
Database migration script for GreenOps v2.0
Adds MAC address field to systems table
"""

import sqlite3
import sys
import os
from datetime import datetime

def migrate_database(db_path='greenops.db'):
    """Safely migrate database to new schema"""
    
    print(f"Starting database migration for {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Will be created on first run.")
        return True
    
    # Backup database
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
    except Exception as e:
        print(f"Warning: Could not create backup: {e}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if mac_address column exists
        cursor.execute("PRAGMA table_info(systems)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'mac_address' not in columns:
            print("Adding mac_address column to systems table...")
            
            # Add mac_address column
            cursor.execute("""
                ALTER TABLE systems 
                ADD COLUMN mac_address TEXT
            """)
            
            # Add department column if not exists
            if 'department' not in columns:
                cursor.execute("""
                    ALTER TABLE systems 
                    ADD COLUMN department TEXT
                """)
            
            # Add lab column if not exists
            if 'lab' not in columns:
                cursor.execute("""
                    ALTER TABLE systems 
                    ADD COLUMN lab TEXT
                """)
            
            # Add first_seen column if not exists
            if 'first_seen' not in columns:
                cursor.execute("""
                    ALTER TABLE systems 
                    ADD COLUMN first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
            
            conn.commit()
            print("Schema updated successfully")
            
            # Generate MAC addresses for existing systems
            cursor.execute("SELECT id, pc_id FROM systems WHERE mac_address IS NULL")
            existing_systems = cursor.fetchall()
            
            if existing_systems:
                print(f"Generating MAC addresses for {len(existing_systems)} existing systems...")
                
                for system_id, pc_id in existing_systems:
                    # Generate a fake but consistent MAC based on PC ID
                    mac_hash = hash(pc_id)
                    fake_mac = f"02:00:00:{(mac_hash >> 16) & 0xFF:02X}:{(mac_hash >> 8) & 0xFF:02X}:{mac_hash & 0xFF:02X}"
                    
                    cursor.execute("""
                        UPDATE systems 
                        SET mac_address = ?, 
                            department = 'MIGRATED',
                            lab = 'LEGACY',
                            first_seen = last_seen
                        WHERE id = ?
                    """, (fake_mac, system_id))
                
                conn.commit()
                print("Existing systems migrated")
            
            # Create unique index on mac_address
            try:
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_systems_mac 
                    ON systems(mac_address)
                """)
                conn.commit()
                print("Unique index created on mac_address")
            except Exception as e:
                print(f"Warning: Could not create unique index: {e}")
        else:
            print("Database schema is up to date")
        
        conn.close()
        print("Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        print(f"Database backup available at: {backup_path}")
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'greenops.db'
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
