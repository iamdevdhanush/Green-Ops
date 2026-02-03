from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from models import User

def admin_required():
    """Decorator to require admin authentication"""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                verify_jwt_in_request()
                current_user_id = get_jwt_identity()
                
                if not current_user_id:
                    return jsonify({'error': 'Invalid token - no identity'}), 401
                
                user = User.query.get(int(current_user_id))
                
                if not user:
                    return jsonify({'error': 'User not found'}), 401
                    
                if user.role != 'ADMIN':
                    return jsonify({'error': 'Admin access required'}), 403
                
                return fn(*args, **kwargs)
            except Exception as e:
                import traceback
                traceback.print_exc()  # This will print the error to console
                return jsonify({'error': f'Authentication failed: {str(e)}'}), 401
        return decorator
    return wrapper


def get_current_user():
    """Get current authenticated user"""
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        return User.query.get(current_user_id)
    except:
        return None
