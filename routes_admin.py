from flask import Blueprint, request, jsonify, render_template
from models import db, Machine, Metric
from auth import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

# Web Routes
@admin_bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')


@admin_bp.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')


@admin_bp.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    return render_template('dashboard.html')


@admin_bp.route('/change-password')
def change_password_page():
    """Change password page"""
    return render_template('change_password.html')


# API Routes
@admin_bp.route('/api/admin/machines', methods=['GET'])
@admin_required()
def get_machines():
    """Get all machines"""
    try:
        machines = Machine.query.all()
        
        # Update offline status for machines not seen in 5 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        for machine in machines:
            if machine.last_seen < cutoff_time:
                machine.status = 'OFFLINE'
        
        db.session.commit()
        
        return jsonify({
            'machines': [m.to_dict() for m in machines],
            'count': len(machines)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/machine/<int:machine_id>', methods=['GET'])
@admin_required()
def get_machine(machine_id):
    """Get single machine details"""
    try:
        machine = Machine.query.get(machine_id)
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Get recent metrics (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        metrics = Metric.query.filter(
            Metric.machine_id == machine_id,
            Metric.timestamp >= cutoff_time
        ).order_by(Metric.timestamp.desc()).limit(100).all()
        
        return jsonify({
            'machine': machine.to_dict(),
            'metrics': [m.to_dict() for m in metrics]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required()
def get_stats():
    """Get dashboard statistics"""
    try:
        # Update offline status
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        offline_machines = Machine.query.filter(Machine.last_seen < cutoff_time).all()
        for machine in offline_machines:
            machine.status = 'OFFLINE'
        db.session.commit()
        
        # Get counts
        total = Machine.query.count()
        active = Machine.query.filter_by(status='ACTIVE').count()
        idle = Machine.query.filter_by(status='IDLE').count()
        offline = Machine.query.filter_by(status='OFFLINE').count()
        
        # Get energy waste (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        total_energy_waste = db.session.query(
            func.sum(Metric.energy_waste_kwh)
        ).filter(
            Metric.timestamp >= cutoff_time
        ).scalar() or 0.0
        
        return jsonify({
            'total_machines': total,
            'active_machines': active,
            'idle_machines': idle,
            'offline_machines': offline,
            'energy_waste_24h': round(total_energy_waste, 2)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
