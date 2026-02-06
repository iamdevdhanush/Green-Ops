from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import db, Machine, PowerCommand, User
from auth import admin_required
from datetime import datetime
from config import Config
import logging

logger = logging.getLogger(__name__)

power_bp = Blueprint('power', __name__, url_prefix='/api/power')


def get_current_user():
    """Get current authenticated user"""
    try:
        user_id = get_jwt_identity()
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        return None


def is_safe_to_control(machine, command_type):
    """
    Safety check before issuing power command - HARDENED
    
    Rules:
    1. LOCK: Always allowed if online
    2. SLEEP/SHUTDOWN/RESTART: Only if IDLE (not ACTIVE)
    3. Must be idle for at least threshold duration
    4. Must not be OFFLINE
    
    Returns:
        (safe: bool, reason: str or None)
    """
    # Allow LOCK anytime (safe operation)
    if command_type == 'LOCK':
        if machine.status == 'OFFLINE':
            return False, "Cannot lock offline machine"
        return True, None
    
    # For destructive operations (SLEEP/SHUTDOWN/RESTART)
    if machine.status == 'OFFLINE':
        return False, f"Cannot {command_type.lower()} offline machine - no connection"
    
    if machine.status == 'ACTIVE':
        return False, f"Cannot {command_type.lower()} active machine - user is currently working"
    
    # Machine must be IDLE
    if machine.status != 'IDLE':
        return False, f"Machine status is {machine.status}, must be IDLE"
    
    # Additional safety: verify idle duration
    idle_threshold_seconds = Config.IDLE_THRESHOLD_MINUTES * 60
    
    if machine.idle_seconds < idle_threshold_seconds:
        return False, (
            f"Machine idle time ({machine.idle_seconds}s) "
            f"below safety threshold ({idle_threshold_seconds}s)"
        )
    
    # All checks passed
    return True, None


@power_bp.route('/sleep/<int:machine_id>', methods=['POST'])
@admin_required()
def sleep_machine(machine_id):
    """
    Queue sleep command with safety checks
    
    Only works on IDLE machines that have been idle > threshold
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User authentication failed'}), 401
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Safety check
        safe, reason = is_safe_to_control(machine, 'SLEEP')
        if not safe:
            logger.warning(f"Sleep command rejected for {machine.pc_id}: {reason}")
            return jsonify({'error': reason}), 400
        
        # Check for duplicate pending commands
        existing = PowerCommand.query.filter_by(
            machine_id=machine_id,
            command='SLEEP',
            status='PENDING'
        ).first()
        
        if existing:
            return jsonify({
                'message': 'Sleep command already pending',
                'command': existing.to_dict()
            }), 200
        
        # Create command
        command = PowerCommand(
            machine_id=machine_id,
            command='SLEEP',
            status='PENDING',
            issued_by=user.username,
            issued_at=datetime.utcnow(),
            idle_seconds_at_issue=machine.idle_seconds
        )
        
        db.session.add(command)
        db.session.commit()
        
        logger.info(f"Sleep command queued for {machine.pc_id} by {user.username}")
        
        return jsonify({
            'message': f'Sleep command queued for {machine.pc_id}',
            'command': command.to_dict(),
            'estimated_execution': 'Within next agent poll (60-120 seconds)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Sleep command error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@power_bp.route('/shutdown/<int:machine_id>', methods=['POST'])
@admin_required()
def shutdown_machine(machine_id):
    """
    Queue shutdown command with safety checks
    
    Includes 60 second delay for last-minute cancellation
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User authentication failed'}), 401
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Safety check
        safe, reason = is_safe_to_control(machine, 'SHUTDOWN')
        if not safe:
            logger.warning(f"Shutdown command rejected for {machine.pc_id}: {reason}")
            return jsonify({'error': reason}), 400
        
        # Check for duplicate pending commands
        existing = PowerCommand.query.filter_by(
            machine_id=machine_id,
            command='SHUTDOWN',
            status='PENDING'
        ).first()
        
        if existing:
            return jsonify({
                'message': 'Shutdown command already pending',
                'command': existing.to_dict()
            }), 200
        
        # Create command
        command = PowerCommand(
            machine_id=machine_id,
            command='SHUTDOWN',
            status='PENDING',
            issued_by=user.username,
            issued_at=datetime.utcnow(),
            idle_seconds_at_issue=machine.idle_seconds
        )
        
        db.session.add(command)
        db.session.commit()
        
        logger.warning(f"Shutdown command queued for {machine.pc_id} by {user.username}")
        
        return jsonify({
            'message': f'Shutdown command queued for {machine.pc_id}',
            'command': command.to_dict(),
            'warning': 'Machine will shutdown after 60 second delay',
            'estimated_execution': 'Within next agent poll (60-120 seconds)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Shutdown command error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@power_bp.route('/lock/<int:machine_id>', methods=['POST'])
@admin_required()
def lock_machine(machine_id):
    """
    Queue lock command
    
    Safe to use on ACTIVE machines (non-destructive)
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User authentication failed'}), 401
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Safety check (simpler for LOCK)
        safe, reason = is_safe_to_control(machine, 'LOCK')
        if not safe:
            return jsonify({'error': reason}), 400
        
        # Create command
        command = PowerCommand(
            machine_id=machine_id,
            command='LOCK',
            status='PENDING',
            issued_by=user.username,
            issued_at=datetime.utcnow(),
            idle_seconds_at_issue=machine.idle_seconds
        )
        
        db.session.add(command)
        db.session.commit()
        
        logger.info(f"Lock command queued for {machine.pc_id} by {user.username}")
        
        return jsonify({
            'message': f'Lock command queued for {machine.pc_id}',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Lock command error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@power_bp.route('/sleep-all-idle', methods=['POST'])
@admin_required()
def sleep_all_idle():
    """
    Queue sleep for ALL idle machines - OPTIMIZED
    
    Only affects machines with:
    - status = IDLE
    - idle_seconds >= threshold
    - no pending commands
    
    Returns detailed list of affected/rejected machines
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User authentication failed'}), 401
        
        # Get all IDLE machines
        idle_machines = Machine.query.filter_by(status='IDLE').all()
        
        if not idle_machines:
            return jsonify({
                'message': 'No idle machines found',
                'affected_machines': [],
                'unsafe_machines': [],
                'count': 0
            }), 200
        
        # Categorize machines
        safe_machines = []
        unsafe_machines = []
        already_pending = []
        
        for machine in idle_machines:
            # Check for existing pending commands
            existing = PowerCommand.query.filter_by(
                machine_id=machine.id,
                status='PENDING'
            ).first()
            
            if existing:
                already_pending.append({
                    'pc_id': machine.pc_id,
                    'reason': f'Command already pending: {existing.command}'
                })
                continue
            
            # Safety check
            safe, reason = is_safe_to_control(machine, 'SLEEP')
            
            if safe:
                safe_machines.append(machine)
            else:
                unsafe_machines.append({
                    'pc_id': machine.pc_id,
                    'reason': reason
                })
        
        if not safe_machines:
            return jsonify({
                'message': 'No machines safe to sleep',
                'affected_machines': [],
                'unsafe_machines': unsafe_machines,
                'already_pending': already_pending,
                'count': 0
            }), 200
        
        # Bulk create commands (single transaction)
        commands_created = []
        current_time = datetime.utcnow()
        
        for machine in safe_machines:
            command = PowerCommand(
                machine_id=machine.id,
                command='SLEEP',
                status='PENDING',
                issued_by=user.username,
                issued_at=current_time,
                idle_seconds_at_issue=machine.idle_seconds
            )
            db.session.add(command)
            
            commands_created.append({
                'pc_id': machine.pc_id,
                'idle_seconds': machine.idle_seconds,
                'department': machine.department,
                'lab': machine.lab
            })
        
        db.session.commit()
        
        logger.info(f"Bulk sleep: {len(safe_machines)} commands queued by {user.username}")
        
        return jsonify({
            'message': f'Sleep commands queued for {len(safe_machines)} idle machines',
            'affected_machines': commands_created,
            'unsafe_machines': unsafe_machines,
            'already_pending': already_pending,
            'count': len(safe_machines),
            'estimated_execution': 'Within next agent poll cycle (60-120 seconds)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk sleep error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@power_bp.route('/cancel-command/<int:command_id>', methods=['POST'])
@admin_required()
def cancel_command(command_id):
    """
    Cancel pending command
    
    Only works on PENDING commands (not EXECUTING or completed)
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User authentication failed'}), 401
        
        command = PowerCommand.query.get(command_id)
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        if command.status != 'PENDING':
            return jsonify({
                'error': f'Cannot cancel command with status {command.status}'
            }), 400
        
        # Mark as cancelled (using FAILED status with specific message)
        command.status = 'FAILED'
        command.result_message = f'Cancelled by {user.username}'
        command.executed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Command {command_id} cancelled by {user.username}")
        
        return jsonify({
            'message': 'Command cancelled successfully',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Cancel command error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@power_bp.route('/command-history', methods=['GET'])
@admin_required()
def command_history():
    """
    Get command execution history with filtering
    
    Query params:
    - limit: number of records (default: 50)
    - machine_id: filter by machine
    - status: filter by status
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        machine_id = request.args.get('machine_id', type=int)
        status = request.args.get('status', type=str)
        
        # Validate limit
        limit = min(max(limit, 1), 500)  # Between 1 and 500
        
        # Build query
        query = PowerCommand.query
        
        if machine_id:
            query = query.filter_by(machine_id=machine_id)
        
        if status:
            status = status.upper()
            if status in ['PENDING', 'EXECUTING', 'EXECUTED', 'FAILED']:
                query = query.filter_by(status=status)
        
        # Execute query
        commands = query.order_by(
            PowerCommand.issued_at.desc()
        ).limit(limit).all()
        
        # Join with machine data
        result = []
        for cmd in commands:
            machine = Machine.query.get(cmd.machine_id)
            cmd_dict = cmd.to_dict()
            cmd_dict['machine'] = machine.to_dict() if machine else None
            result.append(cmd_dict)
        
        # Count by status
        status_counts = db.session.query(
            PowerCommand.status,
            db.func.count(PowerCommand.id)
        ).group_by(PowerCommand.status).all()
        
        return jsonify({
            'commands': result,
            'count': len(result),
            'status_summary': dict(status_counts)
        }), 200
        
    except Exception as e:
        logger.error(f"Command history error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@power_bp.route('/pending-commands', methods=['GET'])
@admin_required()
def pending_commands():
    """
    Get all pending commands with wait time
    
    For real-time monitoring dashboard
    """
    try:
        pending = PowerCommand.query.filter_by(
            status='PENDING'
        ).order_by(PowerCommand.issued_at).all()
        
        result = []
        current_time = datetime.utcnow()
        
        for cmd in pending:
            machine = Machine.query.get(cmd.machine_id)
            cmd_dict = cmd.to_dict()
            cmd_dict['machine'] = machine.to_dict() if machine else None
            
            # Calculate wait time
            wait_seconds = (current_time - cmd.issued_at).total_seconds()
            cmd_dict['waiting_seconds'] = int(wait_seconds)
            
            # Flag stale commands
            if wait_seconds > 300:  # 5 minutes
                cmd_dict['is_stale'] = True
            
            result.append(cmd_dict)
        
        return jsonify({
            'commands': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Pending commands error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
