from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt
from app.models.database import db, Order, Driver, Product
from app import socketio
from app.utils.email import send_status_update
import math
import heapq
import urllib.request
import json

driver_bp = Blueprint('driver', __name__)

class DynamicDeliveryGraph:
    def __init__(self, start_lat, start_lon, goal_lat, goal_lon):
        self.nodes = {}
        self.edges = {}
        self._build_grid(start_lat, start_lon, goal_lat, goal_lon)

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def _build_grid(self, lat1, lon1, lat2, lon2):
        self.nodes['Local_Fogata'] = (lat1, lon1)
        self.nodes['Cliente_Destino'] = (lat2, lon2)

        steps = 4
        for i in range(1, steps):
            frac = i / float(steps)
            mid_lat = lat1 + (lat2 - lat1) * frac + (0.001 * (1 if i % 2 == 0 else -1))
            mid_lon = lon1 + (lon2 - lon1) * frac + (0.001 * (-1 if i % 2 == 0 else 1))
            self.nodes[f'Nodo_Intermedio_{i}'] = (mid_lat, mid_lon)

        node_keys = list(self.nodes.keys())
        for i in range(len(node_keys)):
            u = node_keys[i]
            self.edges[u] = {}
            for j in range(len(node_keys)):
                if i != j:
                    v = node_keys[j]
                    dist = self._haversine(self.nodes[u][0], self.nodes[u][1], self.nodes[v][0], self.nodes[v][1])
                    if dist < 5.0:
                        self.edges[u][v] = round(dist * 1.2, 2)

    def heuristic(self, node, goal):
        x1, y1 = self.nodes[node]
        x2, y2 = self.nodes[goal]
        return self._haversine(x1, y1, x2, y2)

    def a_star(self, start, goal):
        pq = [(0 + self.heuristic(start, goal), 0, start, [start])]
        visited = set()
        nodes_explored = 0
        while pq:
            _, cost, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            nodes_explored += 1
            if node == goal:
                return path, nodes_explored
            for neighbor, weight in self.edges.get(node, {}).items():
                if neighbor not in visited:
                    new_cost = cost + weight
                    new_f = new_cost + self.heuristic(neighbor, goal)
                    heapq.heappush(pq, (new_f, new_cost, neighbor, path + [neighbor]))
        return [start, goal], nodes_explored

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

@driver_bp.route('/deliveries/<order_id>/optimize-route', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def driver_optimize_route(order_id):
    if request.method == 'OPTIONS':
        return '', 200
    did = _driver_id()
    if not did:
        return jsonify({'status': 'error', 'message': 'Acceso restringido'}), 403
    order = Order.query.get(order_id)
    if not order or order.driver_id != did:
        return jsonify({'status': 'error', 'message': 'Pedido no encontrado'}), 404

    data = request.get_json() or {}
    driver_lat = float(data.get('driver_lat', -12.0464))
    driver_lon = float(data.get('driver_lon', -77.0428))
    dest_lat = float(data.get('dest_lat', -12.0580))
    dest_lon = float(data.get('dest_lon', -77.0500))

    graph = DynamicDeliveryGraph(driver_lat, driver_lon, dest_lat, dest_lon)
    path, nodes_explored = graph.a_star('Local_Fogata', 'Cliente_Destino')
    
    path_coordinates = [{'node': node, 'lat': graph.nodes[node][0], 'lon': graph.nodes[node][1]} for node in path]
    
    total_dist = 0
    for i in range(len(path) - 1):
        u, v = path[i], path[i+1]
        total_dist += graph.edges.get(u, {}).get(v, 1.0)

    standard_dist = round(total_dist * 1.35, 2)
    optimized_dist = round(total_dist, 2)

    return jsonify({
        'status': 'success',
        'message': 'Ruta optimizada mediante A*',
        'data': {
            'order_id': order.id,
            'optimal_path': path,
            'path_coordinates': path_coordinates,
            'nodes_explored': nodes_explored,
            'estimated_distance_km': optimized_dist,
            'standard_distance_km': standard_dist
        }
    }), 200

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