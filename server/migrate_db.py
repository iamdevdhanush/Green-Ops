"""
Database Migration Script for GreenOps v2.0
Safe migration with backup and rollback support
"""

import sqlite3
import sys
import os
from datetime import datetime
import shutil

def migrate_database(db_path='greenops.db'):
    """Safely migrate database to new schema"""
    
    print("=" * 60)
    print("GreenOps v2.0 Database Migration")
    print("=" * 60)
    print()
    
    if not os.path.exists(db_path):
        print(f"✓ Database {db_path} does not exist.")
        print("  A new database will be created on first run.")
        return True
    
    # Step 1: Backup
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ Database backed up to: {backup_path}")
    except Exception as e:
        print(f"✗ Warning: Could not create backup: {e}")
        response = input("Continue without backup? (yes/no): ")
        if response.lower() != 'yes':
            return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Step 2: Check current schema
        cursor.execute("PRAGMA table_info(systems)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        changes_made = False
        
        # Step 3: Add mac_address column if missing
        if 'mac_address' not in columns:
            print("\n→ Adding 'mac_address' column to systems table...")
            cursor.execute("ALTER TABLE systems ADD COLUMN mac_address TEXT")
            changes_made = True
            print("  ✓ Column added")
        else:
            print("\n✓ 'mac_address' column already exists")
        
        # Step 4: Add other required columns
        required_columns = {
            'department': 'TEXT',
            'lab': 'TEXT',
            'first_seen': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                print(f"→ Adding '{col_name}' column...")
                cursor.execute(f"ALTER TABLE systems ADD COLUMN {col_name} {col_type}")
                changes_made = True
                print(f"  ✓ Column added")
        
        if changes_made:
            conn.commit()
            print("\n✓ Schema updated successfully")
        
        # Step 5: Generate MAC addresses for existing systems
        cursor.execute("SELECT id, pc_id FROM systems WHERE mac_address IS NULL")
        existing_systems = cursor.fetchall()
        
        if existing_systems:
            print(f"\n→ Generating MAC addresses for {len(existing_systems)} existing systems...")
            
            for system_id, pc_id in existing_systems:
                # Generate consistent fake MAC from PC ID
                mac_hash = hash(str(pc_id))
                fake_mac = f"02:00:00:{(mac_hash >> 16) & 0xFF:02X}:{(mac_hash >> 8) & 0xFF:02X}:{mac_hash & 0xFF:02X}"
                
                cursor.execute("""
                    UPDATE systems 
                    SET mac_address = ?, 
                        department = COALESCE(department, 'MIGRATED'),
                        lab = COALESCE(lab, 'LEGACY'),
                        first_seen = COALESCE(first_seen, last_seen)
                    WHERE id = ?
                """, (fake_mac, system_id))
            
            conn.commit()
            print(f"  ✓ MAC addresses generated for existing systems")
        
        # Step 6: Create unique index on mac_address
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_systems_mac 
                ON systems(mac_address)
            """)
            conn.commit()
            print("✓ Unique index created on mac_address")
        except Exception as e:
            print(f"  Note: {e}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print(f"\nBackup location: {backup_path}")
        print("You can now start the server with: python app.py")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print(f"Database backup available at: {backup_path}")
        print("\nTo restore backup:")
        print(f"  cp {backup_path} {db_path}")
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'greenops.db'
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
