import heapq
import math
from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import or_
from app.models.database import Order, Product, db

ai_bp = Blueprint("ai", __name__)

MAX_PATH_LENGTH = 4
MAX_EXPLORED_NODES = 20
DEFAULT_HEURISTIC = 10.0
KEYWORD_WEIGHT = 5.0
PRICE_WEIGHT = 5.0
PRICE_DECAY = 0.05
MISMATCH_PENALTY = 3.0
BASE_TRANSITION_COST = 1.0
PRICE_COST_FACTOR = 0.1
FIRST_ORDER_DESCRIPTION = "Haz tu primer pedido solicitando esta recomendacion"

KEYWORD_TERMS = {
    "pollo": ("pollo",),
    "papas": ("papas", "patatas", "salchipapas", "papa rellena", "yuca", "camote"),
    "bebida": ("gaseosa", "bebida", "inka", "coca"),
}


def detect_keyword(product):
    text = f"{product.name or ''} {product.description or ''}".lower()
    for kw, terms in KEYWORD_TERMS.items():
        if any(term in text for term in terms):
            return kw
    return "general"


class RecommendationGraph:
    def __init__(self, products, client_prefs):
        self.products = {p.id: p for p in products}
        self.keywords = {p.id: detect_keyword(p) for p in products}
        self.client_prefs = client_prefs
        self.edges = self._build_edges(products)

    def _calculate_cost(self, p1, p2):
        same_kw = self.keywords[p1.id] == self.keywords[p2.id]
        match_diff = 0.0 if same_kw else MISMATCH_PENALTY
        price_diff = abs(float(p1.price) - float(p2.price))
        return round(BASE_TRANSITION_COST + match_diff + (price_diff * PRICE_COST_FACTOR), 2)

    def _build_edges(self, products):
        graph_edges = {}
        for p1 in products:
            graph_edges[p1.id] = {}
            for p2 in products:
                if p1.id != p2.id:
                    graph_edges[p1.id][p2.id] = self._calculate_cost(p1, p2)
        return graph_edges

    def heuristic(self, item_id, target_keyword):
        item = self.products.get(item_id)
        if not item:
            return DEFAULT_HEURISTIC

        score = 0.0
        if target_keyword and self.keywords[item_id] == target_keyword:
            score += KEYWORD_WEIGHT

        pref_price = self.client_prefs.get("avg_price")
        if pref_price is not None:
            p_diff = abs(float(item.price) - float(pref_price))
            similarity = math.exp(-PRICE_DECAY * p_diff)
            score += similarity * PRICE_WEIGHT

        return max(0.0, DEFAULT_HEURISTIC - score)

    def a_star_search(self, start_id, target_keyword):
        pq = [(0 + self.heuristic(start_id, target_keyword), 0.0, start_id, [start_id])]
        visited = set()
        nodes_explored = 0

        while pq:
            _, cost, current_id, path = heapq.heappop(pq)
            if current_id in visited:
                continue
            visited.add(current_id)
            nodes_explored += 1

            if len(path) >= MAX_PATH_LENGTH or nodes_explored > MAX_EXPLORED_NODES:
                return path, nodes_explored

            for neighbor, weight in self.edges.get(current_id, {}).items():
                if neighbor not in visited:
                    new_cost = cost + weight
                    new_f = new_cost + self.heuristic(neighbor, target_keyword)
                    heapq.heappush(pq, (new_f, new_cost, neighbor, path + [neighbor]))

        return [start_id], nodes_explored


def get_real_client_profile(client_key, products_by_id):
    if not client_key:
        return {"favorite_keyword": None, "avg_price": None}

    filters = [Order.customer_name == client_key, Order.customer_email == client_key]
    if str(client_key).isdigit():
        filters.append(Order.customer_id == int(client_key))

    orders = Order.query.filter(or_(*filters)).all()
    keywords = []
    prices = []

    for order in orders:
        for item in order.items:
            prod = products_by_id.get(item.product_id)
            if prod:
                keywords.append(detect_keyword(prod))
                prices.append(float(item.unit_price if item.unit_price is not None else prod.price))

    if not keywords:
        return {"favorite_keyword": None, "avg_price": None}

    return {
        "favorite_keyword": max(set(keywords), key=keywords.count),
        "avg_price": round(sum(prices) / len(prices), 2),
    }


def pick_start_product(products, keywords_by_id, client_prefs):
    fav_kw = client_prefs.get("favorite_keyword")
    avg_price = client_prefs.get("avg_price")
    if not fav_kw and avg_price is None:
        return products[0]

    def affinity_score(prod):
        kw_match = 1 if fav_kw and keywords_by_id[prod.id] == fav_kw else 0
        price_penalty = abs(float(prod.price) - float(avg_price)) if avg_price is not None else 0.0
        return (-kw_match, price_penalty, prod.id)

    return min(products, key=affinity_score)


@ai_bp.route("/recommendations", methods=["POST", "OPTIONS"])
@cross_origin()
@jwt_required()
def get_ai_recommendations():
    if request.method == "OPTIONS":
        return "", 200

    claims = get_jwt()
    client_key = claims.get("sub")

    all_products = Product.query.filter_by(is_active=True).all()
    if not all_products:
        all_products = Product.query.all()
    if not all_products:
        return jsonify({
            "status": "success",
            "message": "Recomendaciones inteligentes generadas mediante Algoritmo A*",
            "data": {
                "nodes_explored": 0,
                "client_profile": {"favorite_keyword": None, "avg_price": None},
                "recommendations": [],
            },
        }), 200

    products_by_id = {p.id: p for p in all_products}
    keywords_by_id = {p.id: detect_keyword(p) for p in all_products}
    client_prefs = get_real_client_profile(client_key, products_by_id)

    has_history = client_prefs["favorite_keyword"] is not None or client_prefs["avg_price"] is not None
    if not has_history:
        first_prod = all_products[0]
        return jsonify({
            "status": "success",
            "message": "Recomendaciones inteligentes generadas mediante Algoritmo A*",
            "data": {
                "nodes_explored": 0,
                "client_profile": {"favorite_keyword": None, "avg_price": None},
                "recommendations": [
                    {
                        "id": first_prod.id,
                        "name": first_prod.name,
                        "description": FIRST_ORDER_DESCRIPTION,
                        "price": float(first_prod.price),
                        "image": first_prod.image,
                    }
                ],
            },
        }), 200

    start_product = pick_start_product(all_products, keywords_by_id, client_prefs)
    graph = RecommendationGraph(all_products, client_prefs)
    path_ids, explored = graph.a_star_search(start_product.id, client_prefs["favorite_keyword"])

    recommendations = []
    for pid in path_ids:
        prod = products_by_id.get(pid)
        if prod:
            recommendations.append({
                "id": prod.id,
                "name": prod.name,
                "description": prod.description,
                "price": float(prod.price),
                "image": prod.image,
            })

    return jsonify({
        "status": "success",
        "message": "Recomendaciones inteligentes generadas mediante Algoritmo A*",
        "data": {
            "nodes_explored": explored,
            "client_profile": client_prefs,
            "recommendations": recommendations,
        },
    }), 200


@ai_bp.route("/business-human-insights", methods=["GET", "OPTIONS"])
@cross_origin()
def business_human_insights():
    if request.method == "OPTIONS":
        return "", 200
    from app.ai.business_insights import get_human_readable_ai_insights
    data = get_human_readable_ai_insights()
    return jsonify({
        "status": "success",
        **data,
    }), 200
