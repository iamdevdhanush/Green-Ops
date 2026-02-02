from flask import Flask
from flask_jwt_extended import JWTManager
from models import db, User
from config import Config
from routes_auth import auth_bp
from routes_agent import agent_bp
from routes_admin import admin_bp
import sys

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_bp)
    
    return app


def init_database(app):
    """Initialize database and create default admin user"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
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
                print("✓ Default admin user created (username: admin, password: changeme)")
                print("⚠ Please change the default password on first login!")
            else:
                print("✓ Admin user already exists")
            
            print("✓ Database initialized successfully")
            
        except Exception as e:
            print(f"✗ Database initialization failed: {e}")
            sys.exit(1)


if __name__ == '__main__':
    app = create_app()
    
    # Initialize database
    init_database(app)
    
    print("\n" + "="*60)
    print("GreenOps Server Starting")
    print("="*60)
    print(f"Host: {Config.HOST}")
    print(f"Port: {Config.PORT}")
    print(f"Database: {Config.DATABASE_URL}")
    print("="*60 + "\n")
    
    # Run application
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=False
    )
