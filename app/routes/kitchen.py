from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt
from app.models.database import db, Order, Product
from app import socketio
from app.utils.email import send_status_update

kitchen_bp = Blueprint('kitchen', __name__)

def _kitchen_id():
    claims = get_jwt()
    if claims.get('role') != 'kitchen':
        return None
    return claims.get('kitchen_id')

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
        'order_type': o.order_type,
        'status': o.status,
        'payment_type': o.payment_type,
        'total_amount': float(o.total_amount),
        'created_at': o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        'items': items,
    }

@kitchen_bp.route('/orders', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def kitchen_orders():
    if request.method == 'OPTIONS':
        return '', 200
    if _kitchen_id() is None:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    orders = Order.query.filter(Order.status.notin_(['FINALIZADO', 'CANCELADO'])).order_by(Order.created_at.asc()).all()
    return jsonify({'status': 'success', 'message': 'Pedidos activos', 'data': [_serialize(o) for o in orders]}), 200

@kitchen_bp.route('/orders/<order_id>/prepare', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def kitchen_prepare(order_id):
    if request.method == 'OPTIONS':
        return '', 200
    if _kitchen_id() is None:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404
    order.status = 'PREPARANDO'
    db.session.commit()
    try:
        send_status_update(order, 'PREPARANDO')
    except Exception:
        pass
    socketio.emit('actualizacion_estado', {'id': order.id, 'order_id': order.id, 'status': 'PREPARANDO'})
    return jsonify({'status': 'success', 'message': 'Pedido en preparación'}), 200

@kitchen_bp.route('/orders/<order_id>/ready', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def kitchen_ready(order_id):
    if request.method == 'OPTIONS':
        return '', 200
    if _kitchen_id() is None:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404
    order.status = 'LISTO_PARA_RECOJO'
    db.session.commit()
    try:
        send_status_update(order, 'LISTO_PARA_RECOJO')
    except Exception:
        pass
    socketio.emit('actualizacion_estado', {'id': order.id, 'order_id': order.id, 'status': 'LISTO_PARA_RECOJO'})
    return jsonify({'status': 'success', 'message': 'Pedido listo'}), 200

@kitchen_bp.route('/history', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
def kitchen_history():
    if request.method == 'OPTIONS':
        return '', 200
    if _kitchen_id() is None:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    orders = Order.query.filter(Order.status.in_(['FINALIZADO'])).order_by(Order.updated_at.desc()).limit(50).all()
    data = [{
        'id': o.id,
        'customer_name': o.customer_name,
        'status': o.status,
        'total_amount': float(o.total_amount),
        'created_at': o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for o in orders]
    return jsonify({'status': 'success', 'message': 'Historial', 'data': data}), 200