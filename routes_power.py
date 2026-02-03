from flask import Blueprint, request, jsonify
from models import db, Machine, PowerCommand
from auth import admin_required
from datetime import datetime

power_bp = Blueprint('power', __name__, url_prefix='/api/power')

@power_bp.route('/sleep/<int:machine_id>', methods=['POST'])
@admin_required()
def sleep_machine(machine_id):
    """Send sleep command to machine"""
    try:
        # Get current user from request context
        from flask_jwt_extended import get_jwt_identity
        from models import User
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Create power command
        command = PowerCommand(
            machine_id=machine_id,
            command='SLEEP',
            status='PENDING',
            issued_by=user.username,
            issued_at=datetime.utcnow()
        )
        
        db.session.add(command)
        db.session.commit()
        
        return jsonify({
            'message': f'Sleep command sent to {machine.pc_id}',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/shutdown/<int:machine_id>', methods=['POST'])
@admin_required()
def shutdown_machine(machine_id):
    """Send shutdown command to machine"""
    try:
        from flask_jwt_extended import get_jwt_identity
        from models import User
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        machine = Machine.query.get(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Create power command
        command = PowerCommand(
            machine_id=machine_id,
            command='SHUTDOWN',
            status='PENDING',
            issued_by=user.username,
            issued_at=datetime.utcnow()
        )
        
        db.session.add(command)
        db.session.commit()
        
        return jsonify({
            'message': f'Shutdown command sent to {machine.pc_id}',
            'command': command.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/sleep-all-idle', methods=['POST'])
@admin_required()
def sleep_all_idle():
    """Send sleep command to all idle machines"""
    try:
        from flask_jwt_extended import get_jwt_identity
        from models import User
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        # Get all idle machines
        idle_machines = Machine.query.filter_by(status='IDLE').all()
        
        if not idle_machines:
            return jsonify({'message': 'No idle machines found'}), 200
        
        # Create commands for all idle machines
        commands_created = 0
        for machine in idle_machines:
            command = PowerCommand(
                machine_id=machine.id,
                command='SLEEP',
                status='PENDING',
                issued_by=user.username,
                issued_at=datetime.utcnow()
            )
            db.session.add(command)
            commands_created += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Sleep command sent to {commands_created} idle machines',
            'machines': [m.pc_id for m in idle_machines]
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@power_bp.route('/command-history', methods=['GET'])
@admin_required()
def command_history():
    """Get power command history"""
    try:
        # Get limit from query params
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
        
        return jsonify({
            'commands': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
