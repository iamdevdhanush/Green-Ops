from flask import Flask
from flask_jwt_extended import JWTManager
from models import db, User
from config import Config
from routes_auth import auth_bp
from routes_agent_fixed import agent_bp
from routes_admin import admin_bp
from routes_power import power_bp
import sys
import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(app):
    """Configure application logging with rotation"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # File handler with rotation (10MB files, keep 10 backups)
    file_handler = RotatingFileHandler(
        'logs/greenops_server.log',
        maxBytes=10_485_760,  # 10MB
        backupCount=10
    )
    
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.INFO)
    
    # Configure app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    # Also configure root logger for libraries
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.WARNING)  # Only warnings and errors from libraries
    
    app.logger.info('Logging configured successfully')


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Setup logging first
    setup_logging(app)
    
    # Validate configuration
    if len(app.config['SECRET_KEY']) < 32:
        app.logger.error("SECRET_KEY must be at least 32 characters")
        sys.exit(1)
    
    if len(app.config['JWT_SECRET_KEY']) < 32:
        app.logger.error("JWT_SECRET_KEY must be at least 32 characters")
        sys.exit(1)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # JWT error handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        app.logger.warning(f"Invalid token: {error}")
        return {'error': 'Invalid token'}, 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.info("Token expired")
        return {'error': 'Token expired'}, 401
    
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        app.logger.warning(f"Unauthorized: {error}")
        return {'error': 'Missing authorization'}, 401
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(power_bp)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring"""
        try:
            # Check database connection
            db.session.execute('SELECT 1')
            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}, 503
    
    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Endpoint not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal server error: {e}", exc_info=True)
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        db.session.rollback()
        return {'error': 'An unexpected error occurred'}, 500
    
    app.logger.info("Application created successfully")
    
    return app


def init_database(app):
    """Initialize database and create default admin user"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            app.logger.info("Database tables created")
            
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            
            if not admin:
                # Create default admin user
                admin = User(
                    username='admin',
                    role='ADMIN',
                    must_change_password=True
                )
                admin.set_password('changeme')
                db.session.add(admin)
                db.session.commit()
                
                print("\n" + "!"*70)
                print("! DEFAULT ADMIN USER CREATED")
                print("!"*70)
                print("! Username: admin")
                print("! Password: changeme")
                print("!")
                print("! ⚠️  CRITICAL: Change this password immediately after first login!")
                print("!"*70 + "\n")
                
                app.logger.warning("Default admin user created with password 'changeme'")
            else:
                app.logger.info("Admin user already exists")
            
            # Cleanup stale EXECUTING commands on startup
            from models import PowerCommand
            from datetime import datetime, timedelta
            
            stale_threshold = datetime.utcnow() - timedelta(minutes=5)
            stale_commands = PowerCommand.query.filter(
                PowerCommand.status == 'EXECUTING',
                PowerCommand.issued_at < stale_threshold
            ).all()
            
            if stale_commands:
                for cmd in stale_commands:
                    cmd.status = 'FAILED'
                    cmd.result_message = 'Command failed during server restart'
                    cmd.executed_at = datetime.utcnow()
                
                db.session.commit()
                app.logger.info(f"Cleaned up {len(stale_commands)} stale commands from previous session")
            
            app.logger.info("Database initialized successfully")
            
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}", exc_info=True)
            print(f"\n✗ Database initialization failed: {e}\n")
            sys.exit(1)


def validate_environment():
    """Validate critical environment variables"""
    errors = []
    
    # Check SECRET_KEY
    secret_key = Config.SECRET_KEY
    if not secret_key or secret_key.startswith('dev-'):
        errors.append("SECRET_KEY not set or using dev key in production")
    
    if len(secret_key) < 32:
        errors.append(f"SECRET_KEY too short ({len(secret_key)} chars, need 32+)")
    
    # Check JWT_SECRET_KEY
    jwt_key = Config.JWT_SECRET_KEY
    if not jwt_key or jwt_key.startswith('dev-'):
        errors.append("JWT_SECRET_KEY not set or using dev key in production")
    
    if len(jwt_key) < 32:
        errors.append(f"JWT_SECRET_KEY too short ({len(jwt_key)} chars, need 32+)")
    
    # Check database URL
    if not Config.DATABASE_URL:
        errors.append("DATABASE_URL not set")
    
    if errors:
        print("\n" + "="*70)
        print("CONFIGURATION ERRORS DETECTED")
        print("="*70)
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        print("\nGenerate secure keys with:")
        print("  python -c \"import secrets; print(secrets.token_hex(32))\"")
        print("="*70 + "\n")
        
        # Only exit if critical issues
        if any('not set' in e for e in errors):
            sys.exit(1)
        else:
            print("⚠️  Warning: Using dev keys - acceptable for development only\n")


if __name__ == '__main__':
    # Validate environment
    validate_environment()
    
    # Create app
    app = create_app()
    
    # Initialize database
    init_database(app)
    
    # Print startup banner
    print("\n" + "="*70)
    print("GreenOps Server - Production Ready")
    print("="*70)
    print(f"Host: {Config.HOST}")
    print(f"Port: {Config.PORT}")
    print(f"Database: {Config.DATABASE_URL}")
    print(f"Idle Threshold: {Config.IDLE_THRESHOLD_MINUTES} minutes")
    print(f"Power Consumption: {Config.POWER_CONSUMPTION_WATTS}W")
    print(f"Log File: logs/greenops_server.log")
    print("="*70)
    print("\nEndpoints:")
    print("  Web UI: http://{}:{}/".format(Config.HOST, Config.PORT))
    print("  Login: http://{}:{}/login".format(Config.HOST, Config.PORT))
    print("  Dashboard: http://{}:{}/dashboard".format(Config.HOST, Config.PORT))
    print("  Health: http://{}:{}/health".format(Config.HOST, Config.PORT))
    print("="*70 + "\n")
    
    app.logger.info("="*70)
    app.logger.info("GreenOps Server Starting")
    app.logger.info(f"Host: {Config.HOST}, Port: {Config.PORT}")
    app.logger.info("="*70)
    
    # Run application
    # NOTE: Use production WSGI server (gunicorn, uwsgi) in production
    # This is Flask's development server
    try:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=False,  # Never use debug=True in production
            threaded=True  # Handle concurrent requests
        )
    except KeyboardInterrupt:
        app.logger.info("Server stopped by user")
        print("\n✓ Server stopped gracefully\n")
    except Exception as e:
        app.logger.critical(f"Server crashed: {e}", exc_info=True)
        print(f"\n✗ Server crashed: {e}\n")
        sys.exit(1)
