from flask import Blueprint, request, jsonify
from models import db, Machine, Metric, PowerCommand
from datetime import datetime, timedelta
from config import Config

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')

def compute_status(idle_seconds, last_seen):
    """
    Compute machine status - REFACTORED
    Based on REAL idle_seconds from OS, not timers
    """
    # Check if machine is offline (no heartbeat in 60 seconds)
    offline_threshold = datetime.utcnow() - timedelta(seconds=60)
    if last_seen < offline_threshold:
        return 'OFFLINE'
    
    # Compute status from idle_seconds
    idle_threshold = Config.IDLE_THRESHOLD_MINUTES * 60  # Convert to seconds
    
    if idle_seconds >= idle_threshold:
        return 'IDLE'
    else:
        return 'ACTIVE'


@agent_bp.route('/register', methods=['POST'])
def register():
    """
    Register or update machine - REFACTORED
    Sets last_seen explicitly, never uses database defaults
    """
    try:
        data = request.get_json()
        
        required_fields = ['mac_address', 'pc_id', 'department', 'lab', 'hostname', 'os']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        mac_address = data['mac_address'].upper()
        idle_seconds = data.get('idle_seconds', 0)
        
        # CRITICAL: Use server timestamp, not database default
        current_time = datetime.utcnow()
        
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if machine:
            # Update existing machine
            machine.pc_id = data['pc_id']
            machine.department = data['department']
            machine.lab = data['lab']
            machine.hostname = data['hostname']
            machine.os = data['os']
            machine.idle_seconds = idle_seconds
            machine.last_seen = current_time
            machine.status = compute_status(idle_seconds, current_time)
        else:
            # Create new machine - set ALL timestamps explicitly
            machine = Machine(
                mac_address=mac_address,
                pc_id=data['pc_id'],
                department=data['department'],
                lab=data['lab'],
                hostname=data['hostname'],
                os=data['os'],
                idle_seconds=idle_seconds,
                first_seen=current_time,  # EXPLICIT
                last_seen=current_time,   # EXPLICIT
                status=compute_status(idle_seconds, current_time)
            )
            db.session.add(machine)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Machine registered successfully',
            'machine': machine.to_dict(),
            'server_time': current_time.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    Heartbeat with metrics - REFACTORED
    Receives idle_seconds from OS, computes status
    Creates metric entry
    """
    try:
        data = request.get_json()
        
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper()
        idle_seconds = data.get('idle_seconds', 0)
        
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            return jsonify({'error': 'Machine not found. Please register first.'}), 404
        
        # CRITICAL: Use server timestamp
        current_time = datetime.utcnow()
        
        # Update machine with REAL idle time
        machine.idle_seconds = idle_seconds
        machine.last_seen = current_time
        machine.status = compute_status(idle_seconds, current_time)
        
        # Calculate energy waste
        idle_threshold_seconds = Config.IDLE_THRESHOLD_MINUTES * 60
        energy_waste_kwh = 0.0
        
        if idle_seconds >= idle_threshold_seconds:
            # Only count time ABOVE threshold
            excess_idle_seconds = idle_seconds - idle_threshold_seconds
            excess_idle_hours = excess_idle_seconds / 3600.0
            power_kw = Config.POWER_CONSUMPTION_WATTS / 1000.0
            energy_waste_kwh = power_kw * excess_idle_hours
        
        # Create metric entry
        metric = Metric(
            machine_id=machine.id,
            idle_seconds=idle_seconds,
            cpu_usage=data.get('cpu_usage'),
            memory_usage=data.get('memory_usage'),
            disk_usage=data.get('disk_usage'),
            energy_waste_kwh=round(energy_waste_kwh, 6),
            timestamp=current_time  # EXPLICIT
        )
        
        db.session.add(metric)
        db.session.commit()
        
        return jsonify({
            'message': 'Heartbeat received',
            'status': machine.status,
            'energy_waste_kwh': energy_waste_kwh,
            'idle_seconds': idle_seconds
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/commands', methods=['POST'])
def get_commands():
    """
    Get pending commands for machine - QUEUE BASED
    Agent polls this endpoint
    """
    try:
        data = request.get_json()
        
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper()
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Get PENDING commands only
        pending_commands = PowerCommand.query.filter_by(
            machine_id=machine.id,
            status='PENDING'
        ).order_by(PowerCommand.issued_at).all()
        
        # Mark as EXECUTING
        for cmd in pending_commands:
            cmd.status = 'EXECUTING'
        
        db.session.commit()
        
        return jsonify({
            'commands': [cmd.to_dict() for cmd in pending_commands],
            'count': len(pending_commands)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/command-status', methods=['POST'])
def update_command_status():
    """
    Update command execution status - RESULT REPORTING
    Agent calls this after executing command
    """
    try:
        data = request.get_json()
        
        if 'command_id' not in data or 'status' not in data:
            return jsonify({'error': 'command_id and status required'}), 400
        
        command_id = data['command_id']
        status = data['status']  # EXECUTED or FAILED
        result_message = data.get('result_message', '')
        
        command = PowerCommand.query.get(command_id)
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        # Update command status
        command.status = status
        command.executed_at = datetime.utcnow()
        command.result_message = result_message
        
        db.session.commit()
        
        return jsonify({
            'message': 'Command status updated',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
