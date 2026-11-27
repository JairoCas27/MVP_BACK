from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from .models.database import db
import os
from dotenv import load_dotenv

DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    load_dotenv()
    app = Flask(__name__)

    configured = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins = [o.strip() for o in configured.split(",") if o.strip()] or DEFAULT_ORIGINS

    database_url = os.getenv('DATABASE_URL')

    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace(
                'postgres://',
                'postgresql+psycopg2://',
                1
            )
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace(
                'postgresql://',
                'postgresql+psycopg2://',
                1
            )
        elif database_url.startswith('postgresql+psycopg://'):
            database_url = database_url.replace(
                'postgresql+psycopg://',
                'postgresql+psycopg2://',
                1
            )

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True
    )

    db.init_app(app)
    JWTManager(app)
    socketio.init_app(app)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"[DB] No se pudieron crear las tablas al arrancar: {e}")

    from .routes.public import public_bp
    from .routes.admin import admin_bp
    from .routes.auth import auth_bp
    from .routes.driver import driver_bp
    from .routes.kitchen import kitchen_bp
    app.register_blueprint(public_bp, url_prefix='/api/public')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(driver_bp, url_prefix='/api/driver')
    app.register_blueprint(kitchen_bp, url_prefix='/api/kitchen')

    try:
        from .routes.ai import ai_bp
        app.register_blueprint(ai_bp, url_prefix='/api/ai')
    except Exception as e:
        print(f"AI module not available: {e}")

    from .sockets import events

    from flask import send_from_directory

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    uploads_dir = os.path.abspath(uploads_dir)
    os.makedirs(uploads_dir, exist_ok=True)

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(uploads_dir, filename)

    @app.route('/')
    @app.route('/health')
    def health_check():
        info = {
            "status": "ok",
            "database_configured": bool(os.getenv("DATABASE_URL")),
        }
        try:
            from sqlalchemy import inspect
            info["tables"] = inspect(db.engine).get_table_names()
        except Exception as e:
            info["status"] = "degraded"
            info["db_error"] = str(e)
        return jsonify(info), 200 if info["status"] == "ok" else 503

    app.config['UPLOADS_DIR'] = uploads_dir

    try:
        from .swagger import register_swagger
        register_swagger(app)
    except Exception as e:
        print(f"Swagger no disponible: {e}")

    return app