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


def build_swagger_spec(app):
    paths = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        path = str(rule.rule)
        # Convert Flask path params <int:id> -> {id}
        import re
        path = re.sub(r'<(?:[^:>]+:)?([^>]+)>', r'{\1}', path)
        methods = sorted(m for m in rule.methods if m not in ('HEAD', 'OPTIONS'))
        if not methods:
            continue
        entry = {}
        for method in methods:
            entry[method.lower()] = {
                "summary": f"{method} {path}",
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