from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from app.models.database import Admin, Client, Driver, Kitchen, PasswordResetToken, db
from app.utils.email import send_welcome, send_reset_token
import datetime
import os

auth_bp = Blueprint('auth', __name__)

ALLOWED_ORDER_TYPES = {'SALON', 'DELIVERY', 'RECOJO_TIENDA'}
ALLOWED_PAYMENT_TYPES = {'EFECTIVO', 'YAPE', 'PLIN'}


def _error(message, status=400, details=None):
    payload = {'status': 'error', 'message': message, 'data': None}
    if details is not None:
        payload['details'] = details
    return jsonify(payload), status


@auth_bp.route('/ping', methods=['GET', 'OPTIONS'])
@cross_origin()
def ping():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({
        'status': 'success',
        'message': 'Servidor activo y funcionando',
        'data': None
    }), 200


@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@auth_bp.route('/login/', methods=['POST', 'OPTIONS'])
@cross_origin()
def login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json(silent=True)
    if not data or not data.get('username') or not data.get('password'):
        return _error('Faltan credenciales (username y password son requeridos)')

    username = data.get('username')
    password = data.get('password')

    admin = Admin.query.filter_by(username=username).first()
    if admin and check_password_hash(admin.password_hash, password):
        expires = datetime.timedelta(hours=12)
        access_token = create_access_token(
            identity=admin.username,
            additional_claims={'role': 'admin'},
            expires_delta=expires,
        )
        return jsonify({
            'status': 'success',
            'message': 'Login exitoso',
            'data': {'access_token': access_token, 'role': 'admin'}
        }), 200

    return _error('Usuario o contraseña incorrectos', 401)


@auth_bp.route('/admin/me', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def admin_me():
    if request.method == 'OPTIONS':
        return '', 200
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return _error('Acceso restringido', 403)
    admin = Admin.query.filter_by(username=get_jwt_identity()).first()
    if not admin:
        return _error('Administrador no encontrado', 404)
    return jsonify({
        'status': 'success',
        'message': 'Perfil obtenido',
        'data': {
            'id': admin.id,
            'username': admin.username,
        },
    }), 200

@auth_bp.route('/admin/profile', methods=['PUT', 'OPTIONS'])
@cross_origin()
@jwt_required()
def admin_update_profile():
    if request.method == 'OPTIONS':
        return '', 200
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return _error('Acceso restringido', 403)
    admin = Admin.query.filter_by(username=get_jwt_identity()).first()
    if not admin:
        return _error('Administrador no encontrado', 404)
    data = request.get_json(silent=True) or {}
    if 'password' in data and (data.get('password') or '').strip():
        if len(data.get('password')) < 6:
            return _error('La contraseña debe tener al menos 6 caracteres')
        admin.password_hash = generate_password_hash(data.get('password'))
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': 'Perfil actualizado',
        'data': {
            'id': admin.id,
            'username': admin.username,
        },
    }), 200


@auth_bp.route('/client/register', methods=['POST', 'OPTIONS'])
@cross_origin()
def client_register():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    dni = (data.get('dni') or '').strip()
    phone = (data.get('phone') or '').strip()
    address = (data.get('address') or '').strip()
    photo = (data.get('photo') or '').strip()

    if not name or not email or not password:
        return _error('Nombre, email y contraseña son obligatorios')
    if len(password) < 6:
        return _error('La contraseña debe tener al menos 6 caracteres')
    if Client.query.filter_by(email=email).first():
        return _error('Ya existe una cuenta con ese email', 409)

    client = Client(
        name=name,
        email=email,
        dni=dni or None,
        phone=phone,
        address=address,
        photo=photo or None,
        password_hash=generate_password_hash(password),
    )
    db.session.add(client)
    db.session.commit()

    try:
        send_welcome(client.name, client.email)
    except Exception:
        pass

    token = create_access_token(
        identity=email,
        additional_claims={'role': 'client', 'client_id': client.id},
        expires_delta=datetime.timedelta(days=7),
    )
    return jsonify({
        'status': 'success',
        'message': 'Cuenta creada correctamente',
        'data': {
            'access_token': token,
            'role': 'client',
            'client': {
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'dni': client.dni,
                'phone': client.phone,
                'address': client.address,
                'photo': client.photo,
            },
        },
    }), 201


@auth_bp.route('/client/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def client_login():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return _error('Email y contraseña son obligatorios')

    client = Client.query.filter_by(email=email).first()
    if not client or not check_password_hash(client.password_hash, password):
        return _error('Credenciales incorrectas', 401)

    token = create_access_token(
        identity=email,
        additional_claims={'role': 'client', 'client_id': client.id},
        expires_delta=datetime.timedelta(days=7),
    )
    return jsonify({
        'status': 'success',
        'message': 'Login exitoso',
        'data': {
            'access_token': token,
            'role': 'client',
            'client': {
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'dni': client.dni,
                'phone': client.phone,
                'address': client.address,
                'photo': client.photo,
            },
        },
    }), 200


@auth_bp.route('/client/me', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def client_me():
    if request.method == 'OPTIONS':
        return '', 200
    claims = get_jwt()
    if claims.get('role') != 'client':
        return _error('Acceso restringido a clientes', 403)
    client = Client.query.filter_by(email=get_jwt_identity()).first()
    if not client:
        return _error('Cliente no encontrado', 404)
    return jsonify({
        'status': 'success',
        'message': 'Perfil obtenido',
        'data': {
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'dni': client.dni,
            'phone': client.phone,
            'address': client.address,
            'photo': client.photo,
        },
    }), 200


# ---------- Password reset ----------

@auth_bp.route('/forgot-password', methods=['POST', 'OPTIONS'])
@cross_origin()
def forgot_password():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return _error('Email es obligatorio')
    # Always respond success to avoid enumeration
    client = Client.query.filter_by(email=email).first()
    if client:
        import random, string
        token = ''.join(random.choice(string.digits) for _ in range(6))
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=90)
        # invalidate previous
        PasswordResetToken.query.filter_by(email=email, used=False).update({'used': True})
        db.session.add(PasswordResetToken(email=email, token=token, expires_at=expires))
        db.session.commit()
        send_reset_token(email, token)
    resp = {'status': 'success', 'message': 'Si el email existe, se envió un código de validación.'}
    if not os.getenv('SMTP_HOST'):
        resp['demo_token'] = token
    return jsonify(resp), 200

@auth_bp.route('/reset-password', methods=['POST', 'OPTIONS'])
@cross_origin()
def reset_password():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    token = (data.get('token') or '').strip()
    password = data.get('password') or ''
    if not email or not token or not password:
        return _error('Email, token y contraseña son obligatorios')
    if len(password) < 6:
        return _error('La contraseña debe tener al menos 6 caracteres')
    prt = PasswordResetToken.query.filter_by(email=email, token=token, used=False).first()
    if not prt:
        return _error('Código inválido', 400)
    if prt.expires_at < datetime.datetime.utcnow():
        prt.used = True
        db.session.commit()
        return _error('El código ha expirado', 400)
    client = Client.query.filter_by(email=email).first()
    if not client:
        return _error('Usuario no encontrado', 404)
    client.password_hash = generate_password_hash(password)
    prt.used = True
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Contraseña actualizada correctamente'}), 200

@auth_bp.route('/resend-token', methods=['POST', 'OPTIONS'])
@cross_origin()
def resend_token():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return _error('Email es obligatorio')
    client = Client.query.filter_by(email=email).first()
    if client:
        import random, string
        token = ''.join(random.choice(string.digits) for _ in range(6))
        expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=90)
        PasswordResetToken.query.filter_by(email=email, used=False).update({'used': True})
        db.session.add(PasswordResetToken(email=email, token=token, expires_at=expires))
        db.session.commit()
        send_reset_token(email, token)
    return jsonify({'status': 'success', 'message': 'Si el email existe, se envió un nuevo código.'}), 200


@auth_bp.route('/driver/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def driver_login():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return _error('Usuario y contraseña son obligatorios')
    driver = Driver.query.filter_by(username=username).first()
    if not driver or not driver.is_active or not check_password_hash(driver.password_hash, password):
        return _error('Credenciales incorrectas', 401)
    token = create_access_token(
        identity=username,
        additional_claims={'role': 'driver', 'driver_id': driver.id, 'name': driver.name},
        expires_delta=datetime.timedelta(hours=12),
    )
    return jsonify({
        'status': 'success',
        'message': 'Login exitoso',
        'data': {
            'access_token': token,
            'role': 'driver',
            'driver': {
                'id': driver.id,
                'name': driver.name,
                'username': driver.username,
                'phone': driver.phone,
            },
        },
    }), 200


@auth_bp.route('/kitchen/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def kitchen_login():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return _error('Usuario y contraseña son obligatorios')
    kitchen = Kitchen.query.filter_by(username=username).first()
    if not kitchen or not kitchen.is_active or not check_password_hash(kitchen.password_hash, password):
        return _error('Credenciales incorrectas', 401)
    token = create_access_token(
        identity=username,
        additional_claims={'role': 'kitchen', 'kitchen_id': kitchen.id, 'name': kitchen.name},
        expires_delta=datetime.timedelta(hours=12),
    )
    return jsonify({
        'status': 'success',
        'message': 'Login exitoso',
        'data': {
            'access_token': token,
            'role': 'kitchen',
            'kitchen': {
                'id': kitchen.id,
                'name': kitchen.name,
                'username': kitchen.username,
            },
        },
    }), 200


@auth_bp.route('/driver/me', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_me():
    if request.method == 'OPTIONS':
        return '', 200
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return _error('Acceso restringido', 403)
    driver = Driver.query.get(claims.get('driver_id'))
    if not driver:
        return _error('Repartidor no encontrado', 404)
    return jsonify({
        'status': 'success',
        'message': 'Perfil obtenido',
        'data': {
            'id': driver.id,
            'name': driver.name,
            'username': driver.username,
            'dni': driver.dni,
            'phone': driver.phone,
            'is_active': driver.is_active,
        },
    }), 200

@auth_bp.route('/driver/profile', methods=['PUT', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_update_profile():
    if request.method == 'OPTIONS':
        return '', 200
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return _error('Acceso restringido', 403)
    driver = Driver.query.get(claims.get('driver_id'))
    if not driver:
        return _error('Repartidor no encontrado', 404)
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        driver.name = (data.get('name') or '').strip() or driver.name
    if 'dni' in data:
        driver.dni = (data.get('dni') or '').strip() or None
    if 'phone' in data:
        driver.phone = (data.get('phone') or '').strip() or None
    if 'password' in data and (data.get('password') or '').strip():
        if len(data.get('password')) < 6:
            return _error('La contraseña debe tener al menos 6 caracteres')
        driver.password_hash = generate_password_hash(data.get('password'))
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': 'Perfil actualizado',
        'data': {
            'id': driver.id,
            'name': driver.name,
            'username': driver.username,
            'phone': driver.phone,
        },
    }), 200


@auth_bp.route('/client/profile', methods=['PUT', 'OPTIONS'])
@cross_origin()
@jwt_required()
def client_update_profile():
    if request.method == 'OPTIONS':
        return '', 200
    claims = get_jwt()
    if claims.get('role') != 'client':
        return _error('Acceso restringido', 403)
    client = Client.query.filter_by(email=get_jwt_identity()).first()
    if not client:
        return _error('Cliente no encontrado', 404)

    uploads_dir = current_app.config.get('UPLOADS_DIR')
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form
        if 'photo' in request.files:
            f = request.files['photo']
            if f and f.filename:
                from werkzeug.utils import secure_filename
                import uuid, os
                ext = os.path.splitext(f.filename)[1]
                filename = f"{uuid.uuid4().hex}{ext}"
                save_path = os.path.join(uploads_dir, filename)
                f.save(save_path)
                client.photo = f"/uploads/{filename}"
    else:
        data = request.get_json(silent=True) or {}

    if 'name' in data:
        client.name = (data.get('name') or '').strip() or client.name
    if 'dni' in data:
        client.dni = (data.get('dni') or '').strip() or None
    if 'phone' in data:
        client.phone = (data.get('phone') or '').strip() or None
    if 'address' in data:
        client.address = (data.get('address') or '').strip() or None
    if request.form.get('remove_photo') in ('1', 'true', 'True'):
        client.photo = None
    elif 'photo' in data and not request.files.get('photo'):
        val = (data.get('photo') or '').strip()
        client.photo = val if val else None

    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': 'Perfil actualizado',
        'data': {
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'dni': client.dni,
            'phone': client.phone,
            'address': client.address,
            'photo': client.photo,
        },
    }), 200