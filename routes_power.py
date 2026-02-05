from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import db, Machine, PowerCommand, User
from auth import admin_required
from datetime import datetime
from config import Config

power_bp = Blueprint('power', __name__, url_prefix='/api/power')

def get_current_user():
    """Get current authenticated user"""
    try:
        user_id = get_jwt_identity()
        return User.query.get(int(user_id))
    except:
        return None


def is_safe_to_shutdown(machine, command_type):
    """
    Safety check before issuing shutdown command - REFACTORED
    Never shutdown ACTIVE machines
    """
    # Allow LOCK anytime
    if command_type == 'LOCK':
        return True, None
    
    # For SLEEP/SHUTDOWN/RESTART, check idle status
    if machine.status == 'ACTIVE':
        return False, f"Cannot {command_type.lower()} active machine. Machine is currently in use."
    
    if machine.status == 'OFFLINE':
        return False, f"Cannot {command_type.lower()} offline machine. Machine is not connected."
    
    # IDLE machines can be safely controlled
    if machine.status == 'IDLE':
        # Additional check: must be idle for at least threshold
        idle_threshold_seconds = Config.IDLE_THRESHOLD_MINUTES * 60
        if machine.idle_seconds < idle_threshold_seconds:
            return False, f"Machine idle time ({machine.idle_seconds}s) below threshold ({idle_threshold_seconds}s)"
        
        return True, None
    
    return False, "Unknown machine status"


@power_bp.route('/sleep/<int:machine_id>', methods=['POST'])
@admin_required()
def sleep_machine(machine_id):
    """
    Queue sleep command - REFACTORED with safety checks
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Safety check
        safe, reason = is_safe_to_shutdown(machine, 'SLEEP')
        if not safe:
            return jsonify({'error': reason}), 400
        
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
        
        return jsonify({
            'message': f'Sleep command queued for {machine.pc_id}',
            'command': command.to_dict(),
            'estimated_execution': 'Within next agent heartbeat (5-15 seconds)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/shutdown/<int:machine_id>', methods=['POST'])
@admin_required()
def shutdown_machine(machine_id):
    """
    Queue shutdown command - REFACTORED with safety checks
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Safety check
        safe, reason = is_safe_to_shutdown(machine, 'SHUTDOWN')
        if not safe:
            return jsonify({'error': reason}), 400
        
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
        
        return jsonify({
            'message': f'Shutdown command queued for {machine.pc_id}',
            'command': command.to_dict(),
            'warning': 'Machine will shutdown with 60 second delay',
            'estimated_execution': 'Within next agent heartbeat (5-15 seconds)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/lock/<int:machine_id>', methods=['POST'])
@admin_required()
def lock_machine(machine_id):
    """
    Queue lock command - NEW
    Safe to use on active machines
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        if machine.status == 'OFFLINE':
            return jsonify({'error': 'Cannot lock offline machine'}), 400
        
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
        
        return jsonify({
            'message': f'Lock command queued for {machine.pc_id}',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/sleep-all-idle', methods=['POST'])
@admin_required()
def sleep_all_idle():
    """
    Queue sleep for ALL idle machines - REFACTORED
    Only affects machines with status=IDLE
    Returns list of affected machines
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Get ONLY idle machines
        idle_machines = Machine.query.filter_by(status='IDLE').all()
        
        if not idle_machines:
            return jsonify({
                'message': 'No idle machines found',
                'affected_machines': [],
                'count': 0
            }), 200
        
        # Safety check: verify each machine is truly idle
        safe_machines = []
        unsafe_machines = []
        
        for machine in idle_machines:
            safe, reason = is_safe_to_shutdown(machine, 'SLEEP')
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
                'unsafe_machines': unsafe_machines,
                'count': 0
            }), 200
        
        # Create commands for safe machines
        commands_created = []
        for machine in safe_machines:
            command = PowerCommand(
                machine_id=machine.id,
                command='SLEEP',
                status='PENDING',
                issued_by=user.username,
                issued_at=datetime.utcnow(),
                idle_seconds_at_issue=machine.idle_seconds
            )
            db.session.add(command)
            commands_created.append({
                'pc_id': machine.pc_id,
                'idle_seconds': machine.idle_seconds,
                'command_id': command.id
            })
        
        db.session.commit()
        
        return jsonify({
            'message': f'Sleep commands queued for {len(safe_machines)} idle machines',
            'affected_machines': commands_created,
            'unsafe_machines': unsafe_machines,
            'count': len(safe_machines),
            'estimated_execution': 'Within next agent heartbeat (5-15 seconds)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/command-history', methods=['GET'])
@admin_required()
def command_history():
    """
    Get command execution history
    Shows all commands with their status
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        
        commands = PowerCommand.query.order_by(
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
        return jsonify({'error': str(e)}), 500


@power_bp.route('/pending-commands', methods=['GET'])
@admin_required()
def pending_commands():
    """
    Get all pending commands
    For real-time monitoring
    """
    try:
        pending = PowerCommand.query.filter_by(
            status='PENDING'
        ).order_by(PowerCommand.issued_at).all()
        
        result = []
        for cmd in pending:
            machine = Machine.query.get(cmd.machine_id)
            cmd_dict = cmd.to_dict()
            cmd_dict['machine'] = machine.to_dict() if machine else None
            
            # Add time waiting
            wait_seconds = (datetime.utcnow() - cmd.issued_at).total_seconds()
            cmd_dict['waiting_seconds'] = int(wait_seconds)
            
            result.append(cmd_dict)
        
        return jsonify({
            'commands': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
