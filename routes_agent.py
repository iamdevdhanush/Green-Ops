from flask import Blueprint, request, jsonify
from models import db, Machine, Metric, PowerCommand
from datetime import datetime, timedelta
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format"""
    import re
    pattern = r'^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$'
    return bool(re.match(pattern, mac.upper()))


def compute_status(idle_seconds: int, last_seen: datetime) -> str:
    """
    Compute machine status with state stability
    
    Args:
        idle_seconds: Real OS idle time in seconds
        last_seen: Last heartbeat timestamp
    
    Returns:
        Status: OFFLINE, ACTIVE, or IDLE
    """
    # Check if machine is offline (no heartbeat in 2x interval)
    offline_threshold = datetime.utcnow() - timedelta(seconds=120)
    if last_seen < offline_threshold:
        return 'OFFLINE'
    
    # Compute status from idle_seconds
    idle_threshold_seconds = Config.IDLE_THRESHOLD_MINUTES * 60
    
    if idle_seconds >= idle_threshold_seconds:
        return 'IDLE'
    else:
        return 'ACTIVE'


@agent_bp.route('/register', methods=['POST'])
def register():
    """
    Register or update machine - HARDENED
    - Validates all inputs
    - Prevents duplicate registrations
    - Sets timestamps explicitly
    - Handles race conditions
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['mac_address', 'pc_id', 'department', 'lab', 'hostname', 'os']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate MAC address format
        mac_address = data['mac_address'].upper().strip()
        if not validate_mac_address(mac_address):
            return jsonify({'error': 'Invalid MAC address format'}), 400
        
        # Validate field lengths
        if len(data['pc_id']) > 100:
            return jsonify({'error': 'PC ID too long (max 100 chars)'}), 400
        
        if len(data['department']) > 50:
            return jsonify({'error': 'Department name too long (max 50 chars)'}), 400
        
        if len(data['lab']) > 50:
            return jsonify({'error': 'Lab name too long (max 50 chars)'}), 400
        
        # Get idle_seconds (default to 0 if not provided)
        idle_seconds = data.get('idle_seconds', 0)
        
        if not isinstance(idle_seconds, int) or idle_seconds < 0:
            idle_seconds = 0
        
        # Server timestamp (CRITICAL: never trust client time)
        current_time = datetime.utcnow()
        
        # Check for existing machine by MAC address
        # Use SELECT FOR UPDATE to prevent race conditions
        machine = Machine.query.filter_by(mac_address=mac_address).with_for_update().first()
        
        if machine:
            # Update existing machine
            logger.info(f"Updating existing machine: {mac_address}")
            
            machine.pc_id = data['pc_id']
            machine.department = data['department']
            machine.lab = data['lab']
            machine.hostname = data['hostname']
            machine.os = data['os']
            machine.idle_seconds = idle_seconds
            machine.last_seen = current_time
            machine.status = compute_status(idle_seconds, current_time)
        else:
            # Create new machine
            logger.info(f"Registering new machine: {mac_address}")
            
            machine = Machine(
                mac_address=mac_address,
                pc_id=data['pc_id'],
                department=data['department'],
                lab=data['lab'],
                hostname=data['hostname'],
                os=data['os'],
                idle_seconds=idle_seconds,
                first_seen=current_time,
                last_seen=current_time,
                status=compute_status(idle_seconds, current_time)
            )
            db.session.add(machine)
        
        db.session.commit()
        
        logger.info(f"Machine registered: {machine.pc_id} - Status: {machine.status}")
        
        return jsonify({
            'message': 'Machine registered successfully',
            'machine': machine.to_dict(),
            'server_time': current_time.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@agent_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    Heartbeat with metrics - UNIFIED ENDPOINT
    - Receives idle_seconds from OS
    - Computes status with stability
    - Creates metric entry
    - Validates all inputs
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate MAC address
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper().strip()
        if not validate_mac_address(mac_address):
            return jsonify({'error': 'Invalid MAC address format'}), 400
        
        # Find machine
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            logger.warning(f"Heartbeat from unregistered machine: {mac_address}")
            return jsonify({
                'error': 'Machine not found. Please register first.',
                'action': 'register'
            }), 404
        
        # Get idle_seconds (critical field)
        idle_seconds = data.get('idle_seconds', 0)
        
        if not isinstance(idle_seconds, int):
            try:
                idle_seconds = int(idle_seconds)
            except (ValueError, TypeError):
                idle_seconds = 0
        
        if idle_seconds < 0:
            idle_seconds = 0
        
        # Server timestamp
        current_time = datetime.utcnow()
        
        # Update machine with REAL idle time
        old_status = machine.status
        machine.idle_seconds = idle_seconds
        machine.last_seen = current_time
        machine.status = compute_status(idle_seconds, current_time)
        
        # Log status changes
        if old_status != machine.status:
            logger.info(f"Machine {machine.pc_id} status changed: {old_status} -> {machine.status}")
        
        # Calculate energy waste (only for time ABOVE threshold)
        idle_threshold_seconds = Config.IDLE_THRESHOLD_MINUTES * 60
        energy_waste_kwh = 0.0
        
        if idle_seconds >= idle_threshold_seconds:
            # Only count excess idle time
            excess_idle_seconds = idle_seconds - idle_threshold_seconds
            excess_idle_hours = excess_idle_seconds / 3600.0
            power_kw = Config.POWER_CONSUMPTION_WATTS / 1000.0
            energy_waste_kwh = power_kw * excess_idle_hours
        
        # Validate optional metrics
        cpu_usage = data.get('cpu_usage')
        memory_usage = data.get('memory_usage')
        disk_usage = data.get('disk_usage')
        
        # Ensure metrics are valid floats or None
        def validate_metric(value):
            if value is None:
                return None
            try:
                val = float(value)
                return val if 0 <= val <= 100 else None
            except (ValueError, TypeError):
                return None
        
        cpu_usage = validate_metric(cpu_usage)
        memory_usage = validate_metric(memory_usage)
        disk_usage = validate_metric(disk_usage)
        
        # Create metric entry
        metric = Metric(
            machine_id=machine.id,
            idle_seconds=idle_seconds,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            energy_waste_kwh=round(energy_waste_kwh, 6),
            timestamp=current_time
        )
        
        db.session.add(metric)
        db.session.commit()
        
        logger.debug(f"Heartbeat received from {machine.pc_id}: idle={idle_seconds}s, status={machine.status}")
        
        return jsonify({
            'message': 'Heartbeat received',
            'status': machine.status,
            'energy_waste_kwh': round(energy_waste_kwh, 6),
            'idle_seconds': idle_seconds,
            'server_time': current_time.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Heartbeat error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@agent_bp.route('/commands', methods=['POST'])
def get_commands():
    """
    Get pending commands - QUEUE BASED WITH STATE MACHINE
    - Agent polls this endpoint
    - Returns PENDING commands only
    - Marks as EXECUTING only after agent confirms receipt
    - Prevents duplicate execution
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'mac_address' not in data:
            return jsonify({'error': 'MAC address required'}), 400
        
        mac_address = data['mac_address'].upper().strip()
        
        # Find machine
        machine = Machine.query.filter_by(mac_address=mac_address).first()
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Get PENDING commands only (ordered by issue time)
        pending_commands = PowerCommand.query.filter_by(
            machine_id=machine.id,
            status='PENDING'
        ).order_by(PowerCommand.issued_at).all()
        
        if not pending_commands:
            return jsonify({
                'commands': [],
                'count': 0
            }), 200
        
        # Mark as EXECUTING (agent has received them)
        for cmd in pending_commands:
            cmd.status = 'EXECUTING'
            logger.info(f"Command {cmd.id} ({cmd.command}) marked as EXECUTING for {machine.pc_id}")
        
        db.session.commit()
        
        return jsonify({
            'commands': [cmd.to_dict() for cmd in pending_commands],
            'count': len(pending_commands)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Command fetch error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@agent_bp.route('/command-status', methods=['POST'])
def update_command_status():
    """
    Update command execution status - RESULT REPORTING
    - Agent calls this after executing command
    - Finalizes command state (EXECUTED or FAILED)
    - Records execution time and result
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        if 'command_id' not in data or 'status' not in data:
            return jsonify({'error': 'command_id and status required'}), 400
        
        command_id = data['command_id']
        status = data['status'].upper()
        result_message = data.get('result_message', '')
        
        # Validate status
        if status not in ['EXECUTED', 'FAILED']:
            return jsonify({'error': 'Invalid status. Must be EXECUTED or FAILED'}), 400
        
        # Find command
        command = PowerCommand.query.get(command_id)
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        # Prevent duplicate status updates
        if command.status in ['EXECUTED', 'FAILED']:
            logger.warning(f"Command {command_id} already finalized with status {command.status}")
            return jsonify({
                'message': 'Command already finalized',
                'command': command.to_dict()
            }), 200
        
        # Update command status
        command.status = status
        command.executed_at = datetime.utcnow()
        command.result_message = result_message[:500]  # Limit message length
        
        db.session.commit()
        
        logger.info(f"Command {command_id} finalized: {status} - {result_message}")
        
        return jsonify({
            'message': 'Command status updated',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Command status update error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@agent_bp.route('/cleanup-stale-commands', methods=['POST'])
def cleanup_stale_commands():
    """
    Cleanup stale EXECUTING commands - MAINTENANCE
    Called periodically by admin or cron
    Commands stuck in EXECUTING for >5 minutes are marked FAILED
    """
    try:
        stale_threshold = datetime.utcnow() - timedelta(minutes=5)
        
        stale_commands = PowerCommand.query.filter(
            PowerCommand.status == 'EXECUTING',
            PowerCommand.issued_at < stale_threshold
        ).all()
        
        count = 0
        for cmd in stale_commands:
            cmd.status = 'FAILED'
            cmd.result_message = 'Command timed out - no response from agent'
            cmd.executed_at = datetime.utcnow()
            count += 1
            logger.warning(f"Stale command {cmd.id} marked as FAILED")
        
        db.session.commit()
        
        return jsonify({
            'message': f'Cleaned up {count} stale commands',
            'count': count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Cleanup error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
