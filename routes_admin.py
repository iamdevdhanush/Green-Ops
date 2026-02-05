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


def update_machine_statuses():
    """
    Update all machine statuses based on last_seen - REFACTORED
    Marks machines as OFFLINE if no heartbeat in 60 seconds
    """
    offline_threshold = datetime.utcnow() - timedelta(seconds=60)
    
    offline_machines = Machine.query.filter(
        Machine.last_seen < offline_threshold,
        Machine.status != 'OFFLINE'
    ).all()
    
    for machine in offline_machines:
        machine.status = 'OFFLINE'
    
    if offline_machines:
        db.session.commit()
    
    return len(offline_machines)


# API Routes
@admin_bp.route('/api/admin/machines', methods=['GET'])
@admin_required()
def get_machines():
    """
    Get all machines - REFACTORED
    Status is already correct from agent heartbeat
    Just update OFFLINE status for non-responding machines
    """
    try:
        # Update offline statuses
        update_machine_statuses()
        
        machines = Machine.query.order_by(Machine.last_seen.desc()).all()
        
        return jsonify({
            'machines': [m.to_dict() for m in machines],
            'count': len(machines)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/machine/<int:machine_id>', methods=['GET'])
@admin_required()
def get_machine(machine_id):
    """
    Get single machine details with metrics
    """
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
            'metrics': [m.to_dict() for m in metrics],
            'metrics_count': len(metrics)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required()
def get_stats():
    """
    Get dashboard statistics - REFACTORED
    Status counts are accurate from real activity detection
    """
    try:
        # Update offline statuses first
        update_machine_statuses()
        
        # Get counts by status
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
        
        # Get idle machines list for additional stats
        idle_machines = Machine.query.filter_by(status='IDLE').all()
        total_idle_seconds = sum(m.idle_seconds for m in idle_machines)
        
        return jsonify({
            'total_machines': total,
            'active_machines': active,
            'idle_machines': idle,
            'offline_machines': offline,
            'energy_waste_24h': round(total_energy_waste, 4),
            'total_idle_seconds': total_idle_seconds,
            'average_idle_seconds': int(total_idle_seconds / idle) if idle > 0 else 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/realtime-status', methods=['GET'])
@admin_required()
def realtime_status():
    """
    Get real-time status for dashboard polling - NEW
    Called every 5 seconds by dashboard
    """
    try:
        # Update offline statuses
        update_machine_statuses()
        
        # Get basic counts
        status_counts = db.session.query(
            Machine.status,
            func.count(Machine.id)
        ).group_by(Machine.status).all()
        
        # Get recently changed machines (last 10 seconds)
        recent_threshold = datetime.utcnow() - timedelta(seconds=10)
        recently_updated = Machine.query.filter(
            Machine.last_seen >= recent_threshold
        ).all()
        
        # Get pending commands count
        from models import PowerCommand
        pending_commands = PowerCommand.query.filter_by(status='PENDING').count()
        
        return jsonify({
            'status_counts': dict(status_counts),
            'recently_updated': [m.to_dict() for m in recently_updated],
            'pending_commands': pending_commands,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
