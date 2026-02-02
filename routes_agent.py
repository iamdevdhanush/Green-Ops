from flask import Blueprint, request, jsonify
from models import db, Machine, Metric
from datetime import datetime, timedelta
from config import Config

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')

@agent_bp.route('/register', methods=['POST'])
def register():
    """Register or update machine"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['mac_address', 'pc_id', 'department', 'lab', 'hostname', 'os']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        mac_address = data['mac_address'].upper()
        
        # Check if machine exists
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if machine:
            # Update existing machine
            machine.pc_id = data['pc_id']
            machine.department = data['department']
            machine.lab = data['lab']
            machine.hostname = data['hostname']
            machine.os = data['os']
            machine.status = 'ACTIVE'
            machine.last_seen = datetime.utcnow()
        else:
            # Create new machine
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
            return jsonify({'error': 'Machine not found. Please register first.'}), 404
        
        # Update last seen and status
        machine.last_seen = datetime.utcnow()
        
        # Determine status based on idle time
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
            return jsonify({'error': 'Machine not found. Please register first.'}), 404
        
        idle_time_minutes = data.get('idle_time_minutes', 0)
        
        # Calculate energy waste
        # Formula: (Power in kW) × (Idle time in hours) = Energy in kWh
        energy_waste_kwh = 0.0
        if idle_time_minutes >= Config.IDLE_THRESHOLD_MINUTES:
            idle_hours = idle_time_minutes / 60.0
            power_kw = Config.POWER_CONSUMPTION_WATTS / 1000.0
            energy_waste_kwh = power_kw * idle_hours
        
        # Create metric entry
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
        
        # Update machine status
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
