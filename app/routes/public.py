from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.models.database import db, Order, OrderItem, Product, Feedback, Client
from app.utils.helpers import generate_tracking_id
from app import socketio
from app.utils.email import send_receipt, send_status_update
import os

public_bp = Blueprint('public', __name__)

ALLOWED_ORDER_TYPES = {'SALON', 'DELIVERY', 'RECOJO_TIENDA'}
ALLOWED_PAYMENT_TYPES = {'EFECTIVO', 'YAPE', 'PLIN'}


@public_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product or not product.is_active:
        return jsonify({'status': 'error', 'message': 'Producto no encontrado'}), 404
    return jsonify({
        'status': 'success',
        'message': 'Producto obtenido',
        'data': {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'includes': product.includes,
            'price': float(product.price),
            'image': product.image,
        },
    }), 200

@public_bp.route('/products', methods=['GET'])
def get_products():
    products = Product.query.filter_by(is_active=True).all()
    products_list = [
        {
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'price': float(p.price),
            'image': p.image
        } for p in products
    ]
    return jsonify({
        'status': 'success',
        'message': 'Menú cargado exitosamente',
        'data': products_list,
        'meta': {
            'total_items': len(products_list)
        }
    }), 200

@public_bp.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json(silent=True) or {}
    items = data.get('items') or []
    if not items:
        return jsonify({'status': 'error', 'message': 'El carrito está vacío'}), 400

    customer_name = (data.get('customer_name') or '').strip()
    customer_phone = (data.get('customer_phone') or '').strip()
    customer_email = (data.get('customer_email') or '').strip()
    if not customer_name or not customer_phone:
        return jsonify({'status': 'error', 'message': 'Nombre y teléfono son obligatorios'}), 400

    # If client logged in, use their email
    if not customer_email:
        try:
            from flask_jwt_extended import get_jwt, verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            claims = get_jwt()
            if claims.get('role') == 'client':
                from app.models.database import Client
                c = Client.query.get(claims.get('client_id'))
                if c:
                    customer_email = c.email
        except Exception:
            pass

    order_type = data.get('order_type', 'RECOJO_TIENDA')
    if order_type not in ALLOWED_ORDER_TYPES:
        return jsonify({'status': 'error', 'message': 'Tipo de orden inválido'}), 400

    payment_type = data.get('payment_type', 'EFECTIVO')
    if payment_type not in ALLOWED_PAYMENT_TYPES:
        return jsonify({'status': 'error', 'message': 'Método de pago inválido'}), 400

    delivery_address = (data.get('delivery_address') or '').strip()
    if order_type == 'DELIVERY' and not delivery_address:
        return jsonify({'status': 'error', 'message': 'Ingresa la dirección de entrega'}), 400

    table_number = (data.get('table_number') or '').strip()
    notes = (data.get('notes') or '').strip()

    # Optional client identification via JWT
    customer_id = None
    try:
        from flask_jwt_extended import get_jwt, verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        claims = get_jwt()
        if claims.get('role') == 'client':
            customer_id = claims.get('client_id')
    except Exception:
        customer_id = None

    tracking_id = generate_tracking_id()
    while Order.query.get(tracking_id):
        tracking_id = generate_tracking_id()

    total_amount = Decimal('0.00')
    order_items_to_insert = []

    for item in items:
        try:
            product_id = int(item['product_id'])
            quantity = int(item['quantity'])
        except (KeyError, ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Item inválido en el carrito'}), 400
        if quantity <= 0:
            return jsonify({'status': 'error', 'message': 'La cantidad debe ser mayor a 0'}), 400

        product = Product.query.get(product_id)
        if not product or not product.is_active:
            return jsonify({'status': 'error', 'message': f"Producto ID {product_id} no disponible"}), 400

        unit_price = product.price
        subtotal = unit_price * quantity
        total_amount += subtotal

        options = (item.get('options') or '').strip() if isinstance(item, dict) else ''
        order_items_to_insert.append(
            OrderItem(
                order_id=tracking_id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                options=options or None
            )
        )

    delivery_fee = Decimal('5.00') if order_type == 'DELIVERY' else Decimal('0.00')
    total_amount += delivery_fee

    items_data_socket = []
    for oi in order_items_to_insert:
        prod = Product.query.get(oi.product_id)
        items_data_socket.append({
            'product_name': prod.name if prod else 'Producto',
            'quantity': oi.quantity,
            'unit_price': float(oi.unit_price),
            'subtotal': float(oi.subtotal),
            'options': oi.options
        })

    new_order = Order(
        id=tracking_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_email=customer_email or None,
        customer_phone=customer_phone,
        order_type=order_type,
        delivery_address=delivery_address,
        table_number=table_number or None,
        notes=notes or None,
        payment_type=payment_type,
        delivery_fee=delivery_fee,
        total_amount=total_amount,
        status='PENDIENTE'
    )

    try:
        db.session.add(new_order)
        db.session.flush()
        db.session.bulk_save_objects(order_items_to_insert)
        db.session.commit()

        try:
            send_receipt(new_order, items_data_socket)
        except Exception:
            pass

        socketio.emit('nuevo_pedido', {
            'id': tracking_id,
            'customer_id': customer_id,
            'customer_name': new_order.customer_name,
            'customer_phone': new_order.customer_phone,
            'order_type': new_order.order_type,
            'delivery_address': new_order.delivery_address,
            'table_number': new_order.table_number,
            'notes': new_order.notes,
            'payment_type': new_order.payment_type,
            'delivery_fee': float(new_order.delivery_fee),
            'total_amount': float(new_order.total_amount),
            'status': new_order.status,
            'created_at': new_order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'items': items_data_socket
        }, to='admin_room')

        return jsonify({
            'status': 'success',
            'message': 'Pedido creado con éxito',
            'data': {
                'tracking_id': tracking_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error al procesar el pedido',
            'details': str(e)
        }), 500

@public_bp.route('/tracking/<order_id>', methods=['GET'])
def get_tracking(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404

    items = [{
        'product_name': (Product.query.get(i.product_id).name if Product.query.get(i.product_id) else 'Producto'),
        'quantity': i.quantity,
        'unit_price': float(i.unit_price),
        'subtotal': float(i.subtotal),
        'options': i.options
    } for i in order.items]

    return jsonify({
        'status': 'success',
        'message': 'Tracking obtenido correctamente',
        'data': {
            'id': order.id,
            'customer_name': order.customer_name,
            'order_type': order.order_type,
            'payment_type': order.payment_type,
            'status': order.status,
            'total_amount': float(order.total_amount),
            'delivery_address': order.delivery_address,
            'table_number': order.table_number,
            'notes': order.notes,
            'created_at': order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'items': items
        }
    }), 200


@public_bp.route('/client/orders', methods=['GET'])
@jwt_required()
def client_orders():
    claims = get_jwt()
    if claims.get('role') != 'client':
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    client_id = claims.get('client_id')
    orders = Order.query.filter_by(customer_id=client_id).order_by(Order.created_at.desc()).all()
    data = []
    for o in orders:
        items = [{
            'product_name': (Product.query.get(i.product_id).name if Product.query.get(i.product_id) else 'Producto'),
            'quantity': i.quantity,
            'subtotal': float(i.subtotal),
            'options': i.options,
        } for i in o.items]
        data.append({
            'id': o.id,
            'order_type': o.order_type,
            'payment_type': o.payment_type,
            'status': o.status,
            'total_amount': float(o.total_amount),
            'created_at': o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'items': items,
        })
    return jsonify({'status': 'success', 'message': 'Pedidos obtenidos', 'data': data}), 200

@public_bp.route('/feedbacks', methods=['GET'])
def list_feedbacks():
    feedbacks = Feedback.query.filter_by(is_visible=True).order_by(Feedback.created_at.desc()).limit(20).all()
    data = [{
        'id': f.id,
        'customer_name': f.customer_name,
        'phone': f.phone,
        'message': f.message,
        'rating': f.rating,
        'created_at': f.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for f in feedbacks]
    return jsonify({'status': 'success', 'message': 'Opiniones obtenidas', 'data': data}), 200

@public_bp.route('/feedbacks', methods=['POST'])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    if not data or 'message' not in data:
        return jsonify({'status': 'error', 'message': 'El mensaje es obligatorio'}), 400

    try:
        rating = int(data.get('rating', 5))
    except (ValueError, TypeError):
        rating = 5
    rating = max(1, min(5, rating))

    new_feedback = Feedback(
        customer_name=data.get('customer_name', 'Anónimo'),
        phone=data.get('phone', ''),
        message=data['message'],
        rating=rating
    )

    try:
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Comentario enviado con éxito',
            'data': None
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error al guardar el comentario',
            'details': str(e)
        }), 500

@public_bp.route('/init-db', methods=['GET'])
def init_database():
    import os
    secret = request.args.get('secret', '')
    expected = os.getenv('INIT_SECRET', 'init-secret-2026')
    if secret != expected:
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 403
    from app.models.database import db, Admin, Client, Driver, Kitchen, Product
    from werkzeug.security import generate_password_hash
    try:
        db.session.execute(db.text('DROP SCHEMA public CASCADE'))
        db.session.execute(db.text('CREATE SCHEMA public'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        try:
            db.drop_all()
        except Exception:
            pass
    try:
        db.create_all()
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error creando tablas: {str(e)}'}), 500

    if not Admin.query.filter_by(username='admin@demo.com').first():
        db.session.add(Admin(username='admin@demo.com', password_hash=generate_password_hash('admin123')))

    if not Client.query.filter_by(email='cliente@demo.com').first():
        db.session.add(Client(name='Cliente Demo', email='cliente@demo.com', dni='12345678', phone='999999999', address='Av. Demo 123', photo='https://i.pravatar.cc/150?img=12', password_hash=generate_password_hash('cliente123')))

    if not Driver.query.filter_by(username='repartidor@demo.com').first():
        db.session.add(Driver(name='Repartidor Demo', username='repartidor@demo.com', dni='87654321', password_hash=generate_password_hash('repartidor123'), phone='999888777', address='Av. Repartidor 123', photo='https://i.pravatar.cc/150?img=33', is_active=True))

    if not Kitchen.query.filter_by(username='cocina@demo.com').first():
        db.session.add(Kitchen(name='Cocina Demo', username='cocina@demo.com', password_hash=generate_password_hash('cocina123'), is_active=True))

    if Product.query.count() == 0:
        sample_products = [
            {"name": "Pollo a la Brasa Entero", "description": "Pollo entero a la brasa con papas y ensalada", "price": 45.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: pollo a la brasa entero, papas fritas, ensalada, mayonesa, aji y cremas."},
            {"name": "1/2 Pollo a la Brasa", "description": "Medio pollo a la brasa con papas", "price": 25.00, "image": "https://framerusercontent.com/images/VcqFSFyMjFJD90BjE0JLOuSYw.jpg?scale-down-to=1024&width=3000&height=1482", "includes": "Incluye: medio pollo a la brasa, papas fritas, ensalada, mayonesa, aji y cremas."},
            {"name": "1/4 Pollo a la Brasa (pecho)", "description": "Cuarto de pollo a la brasa (pecho)", "price": 14.00, "image": "https://framerusercontent.com/images/8MRbVnxxXoLVgWNVGonH04qTM.jpg?scale-down-to=1024&width=3000&height=1363", "includes": "Incluye: cuarto de pollo (pecho), papas fritas, ensalada, mayonesa, aji y cremas."},
            {"name": "1/4 Pollo a la Brasa (pierna)", "description": "Cuarto de pollo a la brasa (pierna)", "price": 14.00, "image": "https://framerusercontent.com/images/Qp6hU3BWOAAZq2nEN7Q2Hblds.jpg?scale-down-to=1024&width=3000&height=1375", "includes": "Incluye: cuarto de pollo (pierna), papas fritas, ensalada, mayonesa, aji y cremas."},
            {"name": "Papas Fritas", "description": "Porcion de papas fritas", "price": 8.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: porcion de papas fritas crocantes."},
            {"name": "Ensalada", "description": "Ensalada fresca", "price": 6.00, "image": "https://framerusercontent.com/images/2SW7sWzterGNO2Utmq3KXXFA.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: ensalada fresca con lechuga, tomate y aderezo."},
            {"name": "Gaseosa 1.5L", "description": "Bebida gaseosa", "price": 7.00, "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSVX4zZ5EFKRbeeec8zSCTA6hFnkMuPj_5F77jweIHwtwFWUiv7jt_-QRGe&s=10", "includes": "Incluye: botella de gaseosa 1.5L."},
            {"name": "Gaseosa 3L", "description": "Bebida gaseosa", "price": 12.00, "image": "https://saboresdelinca.com/wp-content/uploads/2025/01/gaseosas-de-3lt.webp", "includes": "Incluye: botella de gaseosa 3L."},
        ]
        for p in sample_products:
            db.session.add(Product(name=p["name"], description=p["description"], includes=p.get("includes"), price=p["price"], image=p["image"], is_active=True))

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Base de datos inicializada correctamente.'}), 200
