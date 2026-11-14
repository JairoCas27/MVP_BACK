import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app, db
from app.models.database import Admin, Product, Client, Driver, Kitchen
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.create_all()

    # Admin seed
    if not Admin.query.filter_by(username='admin@demo.com').first():
        admin = Admin(username='admin@demo.com', password_hash=generate_password_hash('admin123'))
        db.session.add(admin)

    # Client seed
    if not Client.query.filter_by(email='cliente@demo.com').first():
        client = Client(name='Cliente Demo', email='cliente@demo.com', dni='12345678', phone='999999999', address='Av. Demo 123', photo='https://i.pravatar.cc/150?img=12', password_hash=generate_password_hash('cliente123'))
        db.session.add(client)

    # Driver seed
    if not Driver.query.filter_by(username='repartidor@demo.com').first():
        driver = Driver(name='Repartidor Demo', username='repartidor@demo.com', dni='87654321', password_hash=generate_password_hash('repartidor123'), phone='999888777', address='Av. Repartidor 123', photo='https://i.pravatar.cc/150?img=33', is_active=True)
        db.session.add(driver)

    # Kitchen seed
    if not Kitchen.query.filter_by(username='cocina@demo.com').first():
        kitchen = Kitchen(name='Cocina Demo', username='cocina@demo.com', password_hash=generate_password_hash('cocina123'), is_active=True)
        db.session.add(kitchen)

    # Products seed (only if empty)
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
            {"name": "Alitas BBQ (6 und)", "description": "Alitas de pollo banadas en salsa BBQ", "price": 18.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: 6 alitas BBQ."},
            {"name": "Chicharron de Pollo", "description": "Crocante chicharron de pollo con yuca", "price": 22.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: chicharron de pollo y yuca."},
            {"name": "Mollejitas al sillao", "description": "Mollejitas de pollo salteadas al sillao", "price": 20.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: mollejitas al sillao."},
            {"name": "Pollo Broaster (2 presas)", "description": "Pollo broaster crocante con papas", "price": 16.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: 2 presas broaster y papas."},
            {"name": "Pollo a la Brasa Familiar", "description": "Pollo entero a la brasa para compartir", "price": 52.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: pollo familiar, papas y ensalada."},
            {"name": "Alitas Picantes (8 und)", "description": "Alitas de pollo con salsa picante", "price": 20.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: 8 alitas picantes."},
            {"name": "Nuggets de Pollo (10 und)", "description": "Nuggets crocantes de pollo", "price": 15.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: 10 nuggets de pollo."},
            {"name": "Salchipapas", "description": "Salchicha con papas fritas y salsas", "price": 12.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: salchicha y papas."},
            {"name": "Papa Rellena", "description": "Papa rellena de carne y huevo", "price": 9.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: papa rellena."},
            {"name": "Torta de Chocolate", "description": "Porcion de torta de chocolate", "price": 8.00, "image": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=600&q=80", "includes": "Incluye: porcion de torta."},
            {"name": "Arroz con Pollo", "description": "Arroz con pollo a la peruana", "price": 18.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: arroz con pollo."},
            {"name": "Lomo Saltado", "description": "Lomo saltado con papas y arroz", "price": 24.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: lomo saltado."},
            {"name": "Arroz Chaufa de Pollo", "description": "Arroz chaufa con pollo", "price": 16.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: arroz chaufa."},
            {"name": "Tallarin Saltado", "description": "Tallarin saltado de pollo", "price": 17.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: tallarin saltado."},
            {"name": "Sopa de Pollo", "description": "Sopa de pollo con fideos", "price": 12.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: sopa de pollo."},
            {"name": "Anticuchos de Corazon", "description": "Anticuchos con papa y choclo", "price": 15.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: anticuchos."},
            {"name": "Yuca Frita", "description": "Yuca frita crocante", "price": 7.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: yuca frita."},
            {"name": "Camote Frito", "description": "Camote frito dulce", "price": 6.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: camote frito."},
            {"name": "Ensalada Cesar", "description": "Ensalada cesar con pollo", "price": 10.00, "image": "https://framerusercontent.com/images/2SW7sWzterGNO2Utmq3KXXFA.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: ensalada cesar."},
            {"name": "Pollo al Horno", "description": "Pollo al horno con hierbas", "price": 28.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: pollo al horno."},
        ]
        for p in sample_products:
            db.session.add(Product(name=p["name"], description=p["description"], includes=p.get("includes"), price=p["price"], image=p["image"], is_active=True))

    db.session.commit()
    print("Base de datos inicializada correctamente.")
    print("Admin: admin@demo.com / admin123")