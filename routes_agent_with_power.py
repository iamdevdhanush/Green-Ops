from flask import Blueprint, request, jsonify
from models import db, Machine, Metric, PowerCommand
from datetime import datetime, timedelta
from config import Config

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')

@agent_bp.route('/register', methods=['POST'])
def register():
    """Register or update machine"""
    try:
        data = request.get_json()
        
        required_fields = ['mac_address', 'pc_id', 'department', 'lab', 'hostname', 'os']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        mac_address = data['mac_address'].upper()
        
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if machine:
            machine.pc_id = data['pc_id']
            machine.department = data['department']
            machine.lab = data['lab']
            machine.hostname = data['hostname']
            machine.os = data['os']
            machine.status = 'ACTIVE'
            machine.last_seen = datetime.utcnow()
        else:
            machine = Machine(
                mac_address=mac_address,
                pc_id=data['pc_id'],
                department=data['department'],
                lab=data['lab'],
                hostname=data['hostname'],
                os=data['os'],
                status='ACTIVE',
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            db.session.add(machine)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Machine registered successfully',
            'machine': machine.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Update machine heartbeat"""
    try:
        data = request.get_json()
        
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper()
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        machine.last_seen = datetime.utcnow()
        
        idle_time_minutes = data.get('idle_time_minutes', 0)
        if idle_time_minutes >= Config.IDLE_THRESHOLD_MINUTES:
            machine.status = 'IDLE'
        else:
            machine.status = 'ACTIVE'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Heartbeat received',
            'status': machine.status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/metrics', methods=['POST'])
def submit_metrics():
    """Submit machine metrics"""
    try:
        data = request.get_json()
        
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper()
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        idle_time_minutes = data.get('idle_time_minutes', 0)
        
        energy_waste_kwh = 0.0
        if idle_time_minutes >= Config.IDLE_THRESHOLD_MINUTES:
            idle_hours = idle_time_minutes / 60.0
            power_kw = Config.POWER_CONSUMPTION_WATTS / 1000.0
            energy_waste_kwh = power_kw * idle_hours
        
        metric = Metric(
            machine_id=machine.id,
            idle_time_minutes=idle_time_minutes,
            cpu_usage=data.get('cpu_usage'),
            memory_usage=data.get('memory_usage'),
            disk_usage=data.get('disk_usage'),
            energy_waste_kwh=round(energy_waste_kwh, 4),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(metric)
        
        if idle_time_minutes >= Config.IDLE_THRESHOLD_MINUTES:
            machine.status = 'IDLE'
        else:
            machine.status = 'ACTIVE'
        
        machine.last_seen = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Metrics submitted successfully',
            'energy_waste_kwh': energy_waste_kwh
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/commands', methods=['POST'])
def get_commands():
    """Get pending power commands for machine"""
    try:
        data = request.get_json()
        
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper()
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Get pending commands
        pending_commands = PowerCommand.query.filter_by(
            machine_id=machine.id,
            status='PENDING'
        ).all()
        
        return jsonify({
            'commands': [cmd.to_dict() for cmd in pending_commands],
            'count': len(pending_commands)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/command-status', methods=['POST'])
def update_command_status():
    """Update power command execution status"""
    try:
        data = request.get_json()
        
        if 'command_id' not in data or 'status' not in data:
            return jsonify({'error': 'command_id and status required'}), 400
        
        command_id = data['command_id']
        status = data['status']
        error_message = data.get('error_message')
        
        command = PowerCommand.query.get(command_id)
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        command.status = status
        command.executed_at = datetime.utcnow()
        command.error_message = error_message
        
        db.session.commit()
        
        return jsonify({
            'message': 'Command status updated',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
