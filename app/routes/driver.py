from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt
from app.models.database import db, Order, Driver, Product
from app import socketio
from app.utils.email import send_status_update

driver_bp = Blueprint('driver', __name__)

def _driver_id():
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return None
    return claims.get('driver_id')

def _serialize(o):
    items = []
    for i in o.items:
        prod = Product.query.get(i.product_id)
        items.append({
            'product_name': prod.name if prod else 'Producto',
            'product_image': prod.image if prod else None,
            'quantity': i.quantity,
            'subtotal': float(i.subtotal),
            'options': i.options,
        })
    return {
        'id': o.id,
        'customer_name': o.customer_name,
        'customer_phone': o.customer_phone,
        'delivery_address': o.delivery_address,
        'order_type': o.order_type,
        'status': o.status,
        'total_amount': float(o.total_amount),
        'payment_type': o.payment_type,
        'created_at': o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        'items': items,
    }

@driver_bp.route('/available', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_available():
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    orders = Order.query.filter_by(order_type='DELIVERY').filter(Order.driver_id.is_(None)).filter(Order.status.notin_(['FINALIZADO', 'CANCELADO'])).order_by(Order.created_at.asc()).all()
    return jsonify({'status': 'success', 'message': 'Entregas disponibles', 'data': [_serialize(o) for o in orders]}), 200

@driver_bp.route('/deliveries/<order_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_delivery_detail(order_id):
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order or order.driver_id != did:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404
    return jsonify({'status': 'success', 'message': 'Detalle de entrega', 'data': _serialize(order)}), 200

@driver_bp.route('/active', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_active():
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    orders = Order.query.filter_by(driver_id=did).filter(Order.status.notin_(['FINALIZADO', 'CANCELADO'])).order_by(Order.created_at.asc()).all()
    return jsonify({'status': 'success', 'message': 'Entregas activas', 'data': [_serialize(o) for o in orders]}), 200

@driver_bp.route('/history', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_history():
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    orders = Order.query.filter_by(driver_id=did, status='FINALIZADO').order_by(Order.delivered_at.desc()).all()
    data = [{
        'id': o.id,
        'customer_name': o.customer_name,
        'delivery_address': o.delivery_address,
        'total_amount': float(o.total_amount),
        'payment_type': o.payment_type,
        'delivered_at': o.delivered_at.strftime("%Y-%m-%d %H:%M:%S") if o.delivered_at else o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for o in orders]
    return jsonify({'status': 'success', 'message': 'Historial de entregas', 'data': data}), 200

@driver_bp.route('/deliveries/<order_id>/accept', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_accept(order_id):
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order or order.driver_id not in (None, did):
        return jsonify({'status': 'error', 'message': 'Pedido no disponible'}), 404
    if order.status in ['FINALIZADO', 'CANCELADO']:
        return jsonify({'status': 'error', 'message': 'El pedido ya está terminado'}), 400
    order.driver_id = did
    driver = Driver.query.get(did)
    if driver:
        order.driver_name = driver.name
    order.status = 'EN_CAMINO'
    db.session.commit()
    socketio.emit('actualizacion_estado', {'id': order.id, 'order_id': order.id, 'status': 'EN_CAMINO'})
    return jsonify({'status': 'success', 'message': 'Pedido aceptado, en camino'}), 200

@driver_bp.route('/deliveries/<order_id>/delivered', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_mark_delivered(order_id):
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order or order.driver_id != did:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404
    from datetime import datetime
    order.status = 'FINALIZADO'
    order.delivered_at = datetime.utcnow()
    db.session.commit()
    try:
        send_status_update(order, 'FINALIZADO')
    except Exception:
        pass
    socketio.emit('actualizacion_estado', {'id': order.id, 'order_id': order.id, 'status': 'FINALIZADO'})
    return jsonify({'status': 'success', 'message': 'Pedido entregado'}), 200