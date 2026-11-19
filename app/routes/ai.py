from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt
from app.models.database import db, Order, Product
from app.ai.business_insights import get_human_readable_ai_insights
import math
import heapq

ai_bp = Blueprint('ai', __name__)

class RecommendationGraph:
    def __init__(self, products, client_prefs):
        self.products = {p.id: p for p in products}
        self.client_prefs = client_prefs
        self.edges = self._build_edges(products)

    def _get_keyword(self, p):
        text = f"{p.name} {p.description or ''}".lower()
        if 'pollo' in text:
            return 'pollo'
        if 'papas' in text or 'patatas' in text:
            return 'papas'
        if 'gaseosa' in text or 'bebida' in text or 'inka' in text or 'coca' in text:
            return 'bebida'
        return 'general'

    def _calculate_cost(self, p1, p2):
        k1 = self._get_keyword(p1)
        k2 = self._get_keyword(p2)
        match_diff = 0.0 if k1 == k2 else 3.0
        price_diff = abs(float(p1.price) - float(p2.price))
        return round(1.0 + match_diff + (price_diff * 0.1), 2)

    def _build_edges(self, products):
        edges = {}
        for p1 in products:
            edges[p1.id] = {}
            for p2 in products:
                if p1.id != p2.id:
                    edges[p1.id][p2.id] = self._calculate_cost(p1, p2)
        return edges

    def heuristic(self, item_id, target_keyword):
        item = self.products.get(item_id)
        if not item:
            return 10.0
        score = 0.0
        if self._get_keyword(item) == target_keyword:
            score += 5.0
        pref_price = self.client_prefs.get('avg_price', 35.0)
        p_diff = abs(float(item.price) - pref_price)
        similarity = math.exp(-0.05 * p_diff)
        score += similarity * 5.0
        return max(0.0, 10.0 - score)

    def a_star_search(self, start_id, target_keyword):
        pq = [(0 + self.heuristic(start_id, target_keyword), 0, start_id, [start_id])]
        visited = set()
        nodes_explored = 0

        while pq:
            _, cost, current_id, path = heapq.heappop(pq)
            if current_id in visited:
                continue
            visited.add(current_id)
            nodes_explored += 1

            if len(path) >= 4 or nodes_explored > 20:
                return path, nodes_explored

            for neighbor, weight in self.edges.get(current_id, {}).items():
                if neighbor not in visited:
                    new_cost = cost + weight
                    new_f = new_cost + self.heuristic(neighbor, target_keyword)
                    heapq.heappush(pq, (new_f, new_cost, neighbor, path + [neighbor]))

        return [start_id], nodes_explored

@ai_bp.route('/recommendations', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def get_ai_recommendations():
    if request.method == 'OPTIONS':
        return '', 200

    claims = get_jwt()
    client_name = claims.get('sub')

    orders = Order.query.filter_by(customer_name=client_name).all()
    keywords = []
    prices = []
    for order in orders:
        for item in order.items:
            prod = Product.query.get(item.product_id)
            if prod:
                text = f"{prod.name} {prod.description or ''}".lower()
                if 'pollo' in text:
                    keywords.append('pollo')
                elif 'papas' in text:
                    keywords.append('papas')
                elif 'gaseosa' in text or 'bebida' in text:
                    keywords.append('bebida')
                else:
                    keywords.append('general')
                prices.append(float(prod.price))

    top_keyword = max(set(keywords), key=keywords.count) if keywords else 'pollo'
    avg_price = sum(prices) / len(prices) if prices else 35.0

    client_prefs = {
        'favorite_keyword': top_keyword,
        'avg_price': avg_price
    }

    all_products = Product.query.filter_by(is_active=True).all()
    if not all_products:
        all_products = Product.query.all()
    if not all_products:
        return jsonify({'status': 'success', 'data': []}), 200

    start_product = all_products[0]
    graph = RecommendationGraph(all_products, client_prefs)
    path_ids, explored = graph.a_star_search(start_product.id, top_keyword)

    recommendations = []
    for pid in path_ids:
        p = Product.query.get(pid)
        if p:
            recommendations.append({
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'price': float(p.price),
                'image': p.image
            })

    return jsonify({
        'status': 'success',
        'message': 'Recomendaciones inteligentes generadas mediante Algoritmo A*',
        'data': {
            'nodes_explored': explored,
            'client_profile': client_prefs,
            'recommendations': recommendations
        }
    }), 200

@ai_bp.route('/business-human-insights', methods=['GET', 'OPTIONS'])
@cross_origin()
def business_human_insights():
    if request.method == 'OPTIONS':
        return '', 200
    data = get_human_readable_ai_insights()
    return jsonify({
        'status': 'success',
        **data
    }), 200