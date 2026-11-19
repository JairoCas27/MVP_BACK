import re
from flask import jsonify, render_template_string


SWAGGER_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>La Fogata - API Swagger</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function() {
      SwaggerUIBundle({
        url: '/swagger.json',
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
        layout: 'BaseLayout'
      });
    };
  </script>
</body>
</html>"""


DESCRIPTIONS = {
    "admin.admin_get_clients": "Lista todos los clientes registrados.",
    "admin.admin_update_client": "Actualiza los datos de un cliente.",
    "admin.admin_delete_client": "Elimina un cliente.",
    "admin.admin_get_deliveries": "Lista las entregas activas.",
    "admin.admin_assign_delivery": "Asigna un repartidor a una entrega.",
    "admin.admin_mark_delivered": "Marca una entrega como entregada.",
    "admin.admin_get_all_deliveries": "Lista todas las entregas (activas e historicas).",
    "admin.admin_get_drivers": "Lista todos los repartidores.",
    "admin.admin_create_driver": "Crea un nuevo repartidor.",
    "admin.admin_update_driver": "Actualiza los datos de un repartidor.",
    "admin.admin_delete_driver": "Elimina un repartidor.",
    "admin.get_feedbacks": "Lista las opiniones de los clientes.",
    "admin.admin_update_feedback": "Actualiza una opinion.",
    "admin.admin_delete_feedback": "Elimina una opinion.",
    "admin.admin_get_kitchens": "Lista el personal de cocina.",
    "admin.admin_create_kitchen": "Crea una cuenta de cocina.",
    "admin.admin_update_kitchen": "Actualiza una cuenta de cocina.",
    "admin.admin_delete_kitchen": "Elimina una cuenta de cocina.",
    "admin.admin_metrics": "Obtiene metricas del negocio.",
    "admin.cancel_order": "Cancela un pedido.",
    "admin.advance_order_state": "Avanza el pedido al siguiente estado.",
    "admin.get_active_orders": "Lista los pedidos activos.",
    "admin.admin_get_products": "Lista todos los productos.",
    "admin.admin_create_product": "Crea un nuevo producto.",
    "admin.admin_update_product": "Actualiza un producto.",
    "admin.admin_delete_product": "Elimina un producto.",
    "admin.get_revenue": "Obtiene ingresos y reportes.",
    "ai.business_human_insights": "Genera insights de negocio con IA.",
    "ai.get_ai_recommendations": "Genera recomendaciones personalizadas con IA.",
    "auth.admin_me": "Obtiene el perfil del administrador autenticado.",
    "auth.admin_update_profile": "Actualiza el perfil del administrador.",
    "auth.client_login": "Inicia sesion de cliente.",
    "auth.client_me": "Obtiene el perfil del cliente autenticado.",
    "auth.client_update_profile": "Actualiza el perfil del cliente.",
    "auth.client_register": "Registra un nuevo cliente.",
    "auth.driver_login": "Inicia sesion de repartidor.",
    "auth.driver_me": "Obtiene el perfil del repartidor autenticado.",
    "auth.driver_update_profile": "Actualiza el perfil del repartidor.",
    "auth.forgot_password": "Solicita recuperacion de contrasena.",
    "auth.kitchen_login": "Inicia sesion de cocina.",
    "auth.login": "Inicia sesion de administrador.",
    "auth.ping": "Verifica que el servidor este activo.",
    "auth.resend_token": "Reenvia el token de recuperacion.",
    "auth.reset_password": "Restablece la contrasena con un token.",
    "driver.driver_active": "Lista las entregas activas del repartidor.",
    "driver.driver_available": "Lista las entregas disponibles para aceptar.",
    "driver.driver_delivery_detail": "Obtiene el detalle de una entrega.",
    "driver.driver_accept": "Acepta una entrega disponible.",
    "driver.driver_mark_delivered": "Marca una entrega como entregada.",
    "driver.driver_optimize_route": "Optimiza la ruta de entrega.",
    "driver.driver_history": "Historial de entregas del repartidor.",
    "kitchen.kitchen_history": "Historial de pedidos de cocina.",
    "kitchen.kitchen_orders": "Lista los pedidos pendientes de cocina.",
    "kitchen.kitchen_prepare": "Marca un pedido como en preparacion.",
    "kitchen.kitchen_ready": "Marca un pedido como listo.",
    "public.client_orders": "Lista los pedidos de un cliente.",
    "public.list_feedbacks": "Lista las opiniones publicas.",
    "public.submit_feedback": "Envia una opinion.",
    "public.init_database": "Inicializa la base de datos con datos demo.",
    "public.create_order": "Crea un nuevo pedido.",
    "public.get_products": "Lista los productos disponibles.",
    "public.get_product": "Obtiene el detalle de un producto.",
    "public.get_tracking": "Rastrea un pedido por codigo.",
}


def build_swagger_spec(app):
    paths = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint in ('static', 'swagger_ui', 'swagger_json', 'uploaded_file'):
            continue
        path = str(rule.rule)
        path = re.sub(r'<(?:[^:>]+:)?([^>]+)>', r'{\1}', path)
        methods = sorted(m for m in rule.methods if m not in ('HEAD', 'OPTIONS'))
        if not methods:
            continue
        entry = {}
        for method in methods:
            desc = DESCRIPTIONS.get(rule.endpoint, f"{method} {path}")
            entry[method.lower()] = {
                "summary": desc,
                "description": desc,
                "tags": [path.split('/')[2] if len(path.split('/')) > 2 else 'root'],
                "responses": {
                    "200": {"description": "OK"},
                    "400": {"description": "Bad Request"},
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Not Found"},
                    "500": {"description": "Server Error"},
                },
            }
        paths.setdefault(path, {}).update(entry)

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "La Fogata Polleria API",
            "description": "Documentacion de endpoints del backend de La Fogata.",
            "version": "1.0.0",
        },
        "servers": [{"url": "/"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
        "security": [{"bearerAuth": []}],
        "paths": paths,
    }
    return spec


def register_swagger(app):
    spec = build_swagger_spec(app)

    @app.route('/swagger.json')
    def swagger_json():
        return jsonify(spec)

    @app.route('/swagger')
    @app.route('/docs')
    def swagger_ui():
        return render_template_string(SWAGGER_HTML)

    return app