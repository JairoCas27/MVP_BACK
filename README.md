# La Fogata - Backend (MVP_BACK)

Backend REST del sistema de pedidos de la pollería **La Fogata**, construido con **Flask** y **SQLAlchemy**. Expone la API consumida por el frontend (MVP_FRONT) y gestiona autenticación por roles, pedidos, productos, entregas, cocina, métricas e insights de IA.

## Stack
- Python 3.12
- Flask 3.0
- Flask-SQLAlchemy / SQLAlchemy 2.x
- PostgreSQL (producción) / SQLite (desarrollo)
- Flask-JWT-Extended (autenticación por roles)
- Flask-SocketIO + eventlet (tiempo real)
- Flask-CORS
- Gunicorn (servidor WSGI en producción)
- Flasgger/Swagger UI (documentación)
- SMTP (emails de bienvenida, comprobantes, estados, recuperación de contraseña)

## Estructura
```
MVP_BACK/
├── app/
│   ├── __init__.py          # create_app, blueprints, swagger
│   ├── models/database.py   # Modelos: Admin, Client, Driver, Kitchen, Product, Order, OrderItem, Feedback, PasswordResetToken
│   ├── routes/              # public, admin, auth, driver, kitchen, ai
│   ├── ai/                  # business_insights, ml_advanced_models, regression_model
│   ├── sockets/             # eventos SocketIO
│   ├── utils/               # email
│   └── swagger.py           # spec OpenAPI + UI
├── init_db.py               # seed local (upsert por nombre)
├── run.py                   # entrypoint local
├── render.yaml              # configuración Render
├── requirements.txt
└── tests/
```

## Roles y credenciales demo
- Admin: `admin@demo.com` / `admin123`
- Cliente: `cliente@demo.com` / `cliente123`
- Repartidor: `repartidor@demo.com` / `repartidor123`
- Cocina: `cocina@demo.com` / `cocina123`

## Endpoints principales
Base: `/api`

- `/public` — productos, pedidos, tracking, opiniones, init-db
- `/auth` — login unificado por rol, registro cliente, perfil, recuperación de contraseña
- `/admin` — pedidos, productos, repartidores, cocinas, clientes, entregas, métricas, ingresos, opiniones
- `/driver` — disponibles, activas, historial, aceptar/entregar, optimización de ruta
- `/kitchen` — pedidos, preparar, listo, historial
- `/ai` — recomendaciones (A*) e insights de negocio (IA)
- `/swagger`, `/docs`, `/swagger.json` — documentación interactiva

## Variables de entorno
```
DATABASE_URL=sqlite:///polleria.db   # o postgresql://...
JWT_SECRET_KEY=...
ALLOWED_ORIGINS=*
PORT=10000
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=...
SMTP_USE_TLS=true
INIT_SECRET=init-secret-2026
```

## Ejecución local
```bash
cd MVP_BACK
pip install -r requirements.txt
python run.py
```
API disponible en `http://localhost:10000`.

## Inicializar base de datos
- Local: `python init_db.py`
- Producción (Render): `GET /api/public/init-db?secret=init-secret-2026`

## Despliegue (Render)
- Build: `pip install -r requirements.txt`
- Start: `gunicorn -w 1 "app:create_app()"`
- Variables: `DATABASE_URL`, `JWT_SECRET_KEY`, `ALLOWED_ORIGINS`, `PYTHON_VERSION=3.12.0`
- Auto-deploy desde rama `main`/`dev`.

## Funcionalidades
- Autenticación unificada por rol en `/cuenta`.
- Gestión de productos con opciones (salsas, marcas).
- Pedidos con modalidades (mesa, recojo, delivery) y métodos de pago.
- Panel admin: pedidos activos, productos, repartidores, cocinas, clientes, entregas, métricas, ingresos, opiniones.
- Panel cocina: pedidos, preparar, listo, historial.
- Panel repartidor: disponibles, activas, historial, aceptar/entregar, optimización de ruta.
- Seguimiento de pedido por código.
- Emails: bienvenida, comprobante, actualización de estado, recuperación de contraseña (token 90s).
- Insights de IA (regresión, clasificación, ML avanzado) con datos sintéticos de respaldo.
- Documentación Swagger en `/swagger`.

## Repositorio
Rama de desarrollo: `dev`. Rama de despliegue: `main`.