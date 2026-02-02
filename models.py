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
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'must_change_password': self.must_change_password,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Machine(db.Model):
    """Machine model for registered PCs"""
    __tablename__ = 'machines'
    
    id = db.Column(db.Integer, primary_key=True)
    pc_id = db.Column(db.String(100), nullable=False, index=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False, index=True)
    department = db.Column(db.String(50), nullable=False)
    lab = db.Column(db.String(50), nullable=False)
    hostname = db.Column(db.String(100))
    os = db.Column(db.String(100))
    status = db.Column(db.String(20), default='ACTIVE', index=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    metrics = db.relationship('Metric', backref='machine', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'mac_address': self.mac_address,
            'department': self.department,
            'lab': self.lab,
            'hostname': self.hostname,
            'os': self.os,
            'status': self.status,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }


class Metric(db.Model):
    """Metric model for storing machine metrics"""
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False, index=True)
    idle_time_minutes = db.Column(db.Integer, default=0)
    cpu_usage = db.Column(db.Float)
    memory_usage = db.Column(db.Float)
    disk_usage = db.Column(db.Float)
    energy_waste_kwh = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'idle_time_minutes': self.idle_time_minutes,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'energy_waste_kwh': self.energy_waste_kwh,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
