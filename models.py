from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='ADMIN')
    must_change_password = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'must_change_password': self.must_change_password,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Machine(db.Model):
    """
    Machine model - REFACTORED
    Status is computed from idle_seconds, NOT from last_seen
    """
    __tablename__ = 'machines'
    
    id = db.Column(db.Integer, primary_key=True)
    pc_id = db.Column(db.String(100), nullable=False, index=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False, index=True)
    department = db.Column(db.String(50), nullable=False)
    lab = db.Column(db.String(50), nullable=False)
    hostname = db.Column(db.String(100))
    os = db.Column(db.String(100))
    
    # Status computed from idle_seconds and last_seen
    status = db.Column(db.String(20), default='ACTIVE', index=True)
    
    # CRITICAL: idle_seconds is REAL OS idle time, not calculated
    idle_seconds = db.Column(db.Integer, default=0)
    
    # Timestamps - NEVER use database defaults, always set explicitly
    first_seen = db.Column(db.DateTime, nullable=False)
    last_seen = db.Column(db.DateTime, nullable=False, index=True)
    
    # Relationships
    metrics = db.relationship('Metric', backref='machine', lazy='dynamic', cascade='all, delete-orphan')
    commands = db.relationship('PowerCommand', backref='machine', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'mac_address': self.mac_address,
            'department': self.department,
            'lab': self.lab,
            'hostname': self.hostname,
            'os': self.os,
            'status': self.status,
            'idle_seconds': self.idle_seconds,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }


class Metric(db.Model):
    """
    Metric model - REFACTORED
    Stores REAL idle_seconds from OS, not calculated values
    """
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False, index=True)
    
    # REAL idle time from OS (seconds)
    idle_seconds = db.Column(db.Integer, default=0)
    
    # System metrics
    cpu_usage = db.Column(db.Float)
    memory_usage = db.Column(db.Float)
    disk_usage = db.Column(db.Float)
    
    # Energy waste calculated from idle_seconds
    energy_waste_kwh = db.Column(db.Float, default=0.0)
    
    # Timestamp - set explicitly
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'idle_seconds': self.idle_seconds,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'energy_waste_kwh': self.energy_waste_kwh,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class PowerCommand(db.Model):
    """
    Power command queue - REFACTORED for reliability
    Commands are queued and executed by agent, not pushed
    """
    __tablename__ = 'power_commands'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False, index=True)
    
    # Command type
    command = db.Column(db.String(20), nullable=False)  # SLEEP, SHUTDOWN, RESTART, LOCK
    
    # Status tracking
    status = db.Column(db.String(20), default='PENDING', index=True)  # PENDING, EXECUTING, EXECUTED, FAILED
    
    # Metadata
    issued_by = db.Column(db.String(80))  # Admin username
    issued_at = db.Column(db.DateTime, nullable=False)
    executed_at = db.Column(db.DateTime)
    
    # Result
    result_message = db.Column(db.String(500))
    
    # Safety check - idle_seconds when command was issued
    idle_seconds_at_issue = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'command': self.command,
            'status': self.status,
            'issued_by': self.issued_by,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'result_message': self.result_message,
            'idle_seconds_at_issue': self.idle_seconds_at_issue
        }
