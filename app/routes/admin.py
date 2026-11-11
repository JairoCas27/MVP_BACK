from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from app.models.database import db, Order, OrderItem, Product, Feedback, Client, Driver, Kitchen
from app import socketio
from app.utils.email import send_status_update

admin_bp = Blueprint('admin', __name__)

def _admin_only():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return False
    return True

@admin_bp.route('/orders/active', methods=['GET'])
@jwt_required()
def get_active_orders():
    active_orders = Order.query.filter(
        Order.status.notin_(['FINALIZADO', 'CANCELADO'])
    ).order_by(Order.created_at.asc()).all()

    orders_list = []
    for order in active_orders:
        items_data = []
        for item in order.items:
            product = Product.query.get(item.product_id)
            items_data.append({
                'product_name': product.name if product else 'Producto Eliminado',
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'subtotal': float(item.subtotal)
            })

        orders_list.append({
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'order_type': order.order_type,
            'delivery_address': order.delivery_address,
            'payment_type': order.payment_type,
            'delivery_fee': float(order.delivery_fee),
            'total_amount': float(order.total_amount),
            'status': order.status,
            'created_at': order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'items': items_data
        })

    return jsonify({
        'status': 'success',
        'message': 'Pedidos activos cargados',
        'data': orders_list,
        'meta': {
            'total_orders': len(orders_list)
        }
    }), 200

@admin_bp.route('/orders/<order_id>/next-state', methods=['POST'])
@jwt_required()
def advance_order_state(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({
            'status': 'error',
            'message': 'Pedido no encontrado'
        }), 404

    current_status = order.status
    new_status = current_status

    if current_status == 'PENDIENTE':
        new_status = 'PREPARANDO'
    elif current_status == 'PREPARANDO':
        if order.order_type == 'DELIVERY':
            new_status = 'EN_CAMINO'
        else:
            new_status = 'LISTO_PARA_RECOJO'
    elif current_status in ['EN_CAMINO', 'LISTO_PARA_RECOJO']:
        new_status = 'FINALIZADO'
    elif current_status in ['FINALIZADO', 'CANCELADO']:
        return jsonify({
            'status': 'error',
            'message': 'El pedido ya está terminado, no puede avanzar más'
        }), 400

    if new_status != current_status:
        try:
            order.status = new_status
            db.session.commit()

            try:
                send_status_update(order, new_status)
            except Exception:
                pass

            socketio.emit('actualizacion_estado', {
                'id': order.id,
                'order_id': order.id,
                'status': new_status
            })
            
            return jsonify({
                'status': 'success',
                'message': f'Pedido avanzado a {new_status}',
                'data': {
                    'order_id': order.id,
                    'new_status': new_status
                }
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error al actualizar',
                'details': str(e)
            }), 500

    return jsonify({
        'status': 'success',
        'message': 'Sin cambios',
        'data': {
            'status': current_status
        }
    }), 200

@admin_bp.route('/orders/<order_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({
            'status': 'error',
            'message': 'Pedido no encontrado'
        }), 404

    if order.status in ['FINALIZADO', 'CANCELADO']:
        return jsonify({
            'status': 'error',
            'message': 'No se puede cancelar un pedido que ya está terminado o cancelado'
        }), 400

    try:
        order.status = 'CANCELADO'
        db.session.commit()

        try:
            send_status_update(order, 'CANCELADO')
        except Exception:
            pass

        socketio.emit('actualizacion_estado', {
            'id': order.id,
            'order_id': order.id,
            'status': 'CANCELADO'
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Pedido cancelado con éxito',
            'data': {
                'order_id': order.id,
                'new_status': 'CANCELADO'
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error al cancelar',
            'details': str(e)
        }), 500

@admin_bp.route('/feedbacks', methods=['GET'])
@jwt_required()
def get_feedbacks():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(50).all()
    feedbacks_list = [{
        'id': f.id,
        'customer_name': f.customer_name,
        'phone': f.phone,
        'message': f.message,
        'rating': f.rating,
        'is_visible': f.is_visible,
        'created_at': f.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for f in feedbacks]
    
    return jsonify({
        'status': 'success',
        'message': 'Comentarios cargados exitosamente',
        'data': feedbacks_list,
        'meta': {
            'total_feedbacks': len(feedbacks_list)
        }
    }), 200

@admin_bp.route('/revenue', methods=['GET'])
@jwt_required()
def get_revenue():
    try:
        total_revenue = db.session.query(func.sum(Order.total_amount)).filter(Order.status == 'FINALIZADO').scalar()
        total_revenue = float(total_revenue) if total_revenue else 0.00
        return jsonify({
            'status': 'success',
            'message': 'Ganancias calculadas exitosamente',
            'data': {
                'total_revenue': total_revenue
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Error al calcular las ganancias',
            'details': str(e)
        }), 500


# ---------- Products CRUD ----------

@admin_bp.route('/products', methods=['GET'])
@jwt_required()
def admin_get_products():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    products = Product.query.order_by(Product.id.desc()).all()
    data = [{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'includes': p.includes,
        'price': float(p.price),
        'image': p.image,
        'is_active': p.is_active,
    } for p in products]
    return jsonify({'status': 'success', 'message': 'Productos obtenidos', 'data': data}), 200


@admin_bp.route('/products', methods=['POST'])
@jwt_required()
def admin_create_product():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    price = data.get('price')
    if not name or price is None:
        return jsonify({'status': 'error', 'message': 'Nombre y precio son obligatorios'}), 400
    try:
        price = float(price)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Precio inválido'}), 400
    product = Product(
        name=name,
        description=(data.get('description') or '').strip(),
        includes=(data.get('includes') or '').strip(),
        price=price,
        image=(data.get('image') or '').strip(),
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Producto creado', 'data': {'id': product.id}}), 201


@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def admin_update_product(product_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'status': 'error', 'message': 'Producto no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        product.name = (data.get('name') or '').strip() or product.name
    if 'description' in data:
        product.description = (data.get('description') or '').strip()
    if 'includes' in data:
        product.includes = (data.get('includes') or '').strip()
    if 'price' in data:
        try:
            product.price = float(data.get('price'))
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Precio inválido'}), 400
    if 'image' in data:
        product.image = (data.get('image') or '').strip()
    if 'is_active' in data:
        product.is_active = bool(data.get('is_active'))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Producto actualizado'}), 200


@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_product(product_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'status': 'error', 'message': 'Producto no encontrado'}), 404
    product.is_active = False
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Producto desactivado'}), 200


# ---------- Deliveries ----------

@admin_bp.route('/deliveries', methods=['GET'])
@jwt_required()
def admin_get_deliveries():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    status_filter = request.args.get('status')
    q = Order.query.filter_by(order_type='DELIVERY')
    if status_filter:
        q = q.filter_by(status=status_filter)
    orders = q.order_by(Order.created_at.desc()).all()
    data = []
    for o in orders:
        data.append({
            'id': o.id,
            'customer_name': o.customer_name,
            'customer_phone': o.customer_phone,
            'delivery_address': o.delivery_address,
            'payment_type': o.payment_type,
            'status': o.status,
            'total_amount': float(o.total_amount),
            'driver_id': o.driver_id,
            'driver_name': o.driver_name,
            'created_at': o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return jsonify({'status': 'success', 'message': 'Entregas obtenidas', 'data': data}), 200


@admin_bp.route('/deliveries/<order_id>/assign', methods=['POST'])
@jwt_required()
def admin_assign_delivery(order_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order or order.order_type != 'DELIVERY':
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    driver_id = data.get('driver_id')
    if driver_id:
        driver = Driver.query.get(driver_id)
        if driver:
            order.driver_id = driver.id
            order.driver_name = driver.name
    if 'driver_name' in data:
        order.driver_name = (data.get('driver_name') or '').strip() or order.driver_name
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Repartidor asignado'}), 200


@admin_bp.route('/deliveries/all', methods=['GET'])
@jwt_required()
def admin_get_all_deliveries():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    orders = Order.query.filter_by(order_type='DELIVERY').order_by(Order.created_at.desc()).all()
    data = []
    for o in orders:
        data.append({
            'id': o.id,
            'customer_name': o.customer_name,
            'customer_phone': o.customer_phone,
            'delivery_address': o.delivery_address,
            'payment_type': o.payment_type,
            'status': o.status,
            'total_amount': float(o.total_amount),
            'driver_id': o.driver_id,
            'driver_name': o.driver_name,
            'delivered_at': o.delivered_at.strftime("%Y-%m-%d %H:%M:%S") if o.delivered_at else None,
            'created_at': o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return jsonify({'status': 'success', 'message': 'Todas las entregas', 'data': data}), 200

@admin_bp.route('/deliveries/<order_id>/delivered', methods=['POST'])
@jwt_required()
def admin_mark_delivered(order_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404
    from datetime import datetime
    order.status = 'FINALIZADO'
    order.delivered_at = datetime.utcnow()
    db.session.commit()
    socketio.emit('actualizacion_estado', {'id': order.id, 'order_id': order.id, 'status': 'FINALIZADO'})
    return jsonify({'status': 'success', 'message': 'Pedido entregado'}), 200


# ---------- Metrics ----------

@admin_bp.route('/metrics', methods=['GET'])
@jwt_required()
def admin_metrics():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    total_orders = Order.query.count()
    active_orders = Order.query.filter(Order.status.notin_(['FINALIZADO', 'CANCELADO'])).count()
    completed = Order.query.filter_by(status='FINALIZADO').count()
    cancelled = Order.query.filter_by(status='CANCELADO').count()
    revenue = db.session.query(func.sum(Order.total_amount)).filter(Order.status == 'FINALIZADO').scalar()
    revenue = float(revenue) if revenue else 0.0

    # Revenue last 7 days
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    daily = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        start = datetime(day.year, day.month, day.day)
        end = start + timedelta(days=1)
        day_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            Order.status == 'FINALIZADO',
            Order.created_at >= start,
            Order.created_at < end,
        ).scalar()
        day_count = Order.query.filter(
            Order.created_at >= start,
            Order.created_at < end,
        ).count()
        daily.append({
            'date': day.strftime('%Y-%m-%d'),
            'revenue': float(day_revenue) if day_revenue else 0.0,
            'orders': day_count,
        })

    # Top products
    top = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('qty'),
    ).join(OrderItem, OrderItem.product_id == Product.id).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    top_products = [{'name': t[0], 'quantity': int(t[1] or 0)} for t in top]

    # Revenue by payment type
    by_payment = db.session.query(
        Order.payment_type,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('revenue'),
    ).filter(Order.status == 'FINALIZADO').group_by(Order.payment_type).all()
    revenue_by_payment = [{'payment_type': r[0], 'count': int(r[1] or 0), 'revenue': float(r[2] or 0)} for r in by_payment]

    # Revenue by order type
    by_order_type = db.session.query(
        Order.order_type,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('revenue'),
    ).filter(Order.status == 'FINALIZADO').group_by(Order.order_type).all()
    revenue_by_order_type = [{'order_type': r[0], 'count': int(r[1] or 0), 'revenue': float(r[2] or 0)} for r in by_order_type]

    return jsonify({
        'status': 'success',
        'message': 'Métricas obtenidas',
        'data': {
            'total_orders': total_orders,
            'active_orders': active_orders,
            'completed_orders': completed,
            'cancelled_orders': cancelled,
            'total_revenue': revenue,
            'daily': daily,
            'top_products': top_products,
            'revenue_by_payment': revenue_by_payment,
            'revenue_by_order_type': revenue_by_order_type,
        },
    }), 200


# ---------- Clients ----------

@admin_bp.route('/clients', methods=['GET'])
@jwt_required()
def admin_get_clients():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    clients = Client.query.order_by(Client.id.desc()).all()
    data = [{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'dni': c.dni,
        'phone': c.phone,
        'address': c.address,
        'photo': c.photo,
        'is_active': c.is_active,
        'created_at': c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for c in clients]
    return jsonify({'status': 'success', 'message': 'Clientes obtenidos', 'data': data}), 200


# ---------- Drivers ----------

@admin_bp.route('/drivers', methods=['GET'])
@jwt_required()
def admin_get_drivers():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    drivers = Driver.query.order_by(Driver.id.desc()).all()
    data = [{
        'id': d.id,
        'name': d.name,
        'username': d.username,
        'dni': d.dni,
        'phone': d.phone,
        'address': d.address,
        'photo': d.photo,
        'is_active': d.is_active,
        'created_at': d.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for d in drivers]
    return jsonify({'status': 'success', 'message': 'Repartidores obtenidos', 'data': data}), 200

@admin_bp.route('/drivers', methods=['POST'])
@jwt_required()
def admin_create_driver():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    dni = (data.get('dni') or '').strip()
    phone = (data.get('phone') or '').strip()
    address = (data.get('address') or '').strip()
    photo = (data.get('photo') or '').strip()
    if not name or not username or not password:
        return jsonify({'status': 'error', 'message': 'Nombre, usuario y contraseña son obligatorios'}), 400
    if Driver.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'El usuario ya existe'}), 409
    driver = Driver(name=name, username=username, dni=dni or None, password_hash=generate_password_hash(password), phone=phone or None, address=address or None, photo=photo or None, is_active=True)
    db.session.add(driver)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Repartidor creado', 'data': {'id': driver.id}}), 201

@admin_bp.route('/drivers/<int:driver_id>', methods=['PUT'])
@jwt_required()
def admin_update_driver(driver_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    driver = Driver.query.get(driver_id)
    if not driver:
        return jsonify({'status': 'error', 'message': 'Repartidor no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    if 'is_active' in data:
        driver.is_active = bool(data.get('is_active'))
    if 'name' in data:
        driver.name = (data.get('name') or '').strip() or driver.name
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Repartidor actualizado'}), 200

@admin_bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_driver(driver_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    driver = Driver.query.get(driver_id)
    if not driver:
        return jsonify({'status': 'error', 'message': 'Repartidor no encontrado'}), 404
    db.session.delete(driver)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Repartidor eliminado'}), 200


# ---------- Kitchens ----------

@admin_bp.route('/kitchens', methods=['GET'])
@jwt_required()
def admin_get_kitchens():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    kitchens = Kitchen.query.order_by(Kitchen.id.desc()).all()
    data = [{'id': k.id, 'name': k.name, 'username': k.username, 'is_active': k.is_active, 'created_at': k.created_at.strftime("%Y-%m-%d %H:%M:%S")} for k in kitchens]
    return jsonify({'status': 'success', 'message': 'Cocinas obtenidas', 'data': data}), 200

@admin_bp.route('/kitchens', methods=['POST'])
@jwt_required()
def admin_create_kitchen():
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not name or not username or not password:
        return jsonify({'status': 'error', 'message': 'Nombre, usuario y contraseña son obligatorios'}), 400
    if Kitchen.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'El usuario ya existe'}), 409
    k = Kitchen(name=name, username=username, password_hash=generate_password_hash(password), is_active=True)
    db.session.add(k)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Cocina creada', 'data': {'id': k.id}}), 201

@admin_bp.route('/kitchens/<int:kitchen_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_kitchen(kitchen_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    k = Kitchen.query.get(kitchen_id)
    if not k:
        return jsonify({'status': 'error', 'message': 'Cocina no encontrada'}), 404
    db.session.delete(k)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Cocina eliminada'}), 200


@admin_bp.route('/clients/<int:client_id>', methods=['PUT'])
@jwt_required()
def admin_update_client(client_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'status': 'error', 'message': 'Usuario no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    if 'is_active' in data:
        client.is_active = bool(data.get('is_active'))
    if 'name' in data:
        client.name = (data.get('name') or '').strip() or client.name
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Usuario actualizado'}), 200

@admin_bp.route('/clients/<int:client_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_client(client_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'status': 'error', 'message': 'Usuario no encontrado'}), 404
    db.session.delete(client)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Usuario eliminado'}), 200


# ---------- Feedbacks management ----------

@admin_bp.route('/feedbacks/<int:feedback_id>', methods=['PUT'])
@jwt_required()
def admin_update_feedback(feedback_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    fb = Feedback.query.get(feedback_id)
    if not fb:
        return jsonify({'status': 'error', 'message': 'Comentario no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    if 'message' in data:
        fb.message = (data.get('message') or '').strip() or fb.message
    if 'rating' in data:
        try:
            fb.rating = max(1, min(5, int(data.get('rating'))))
        except (ValueError, TypeError):
            pass
    if 'is_visible' in data:
        fb.is_visible = bool(data.get('is_visible'))
    if 'customer_name' in data:
        fb.customer_name = (data.get('customer_name') or '').strip() or fb.customer_name
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Comentario actualizado'}), 200

@admin_bp.route('/feedbacks/<int:feedback_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_feedback(feedback_id):
    if not _admin_only():
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    fb = Feedback.query.get(feedback_id)
    if not fb:
        return jsonify({'status': 'error', 'message': 'Comentario no encontrado'}), 404
    db.session.delete(fb)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Comentario eliminado'}), 200