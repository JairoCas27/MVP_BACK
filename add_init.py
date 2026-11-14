addition = '''

@public_bp.route('/init-db', methods=['GET'])
def init_database():
    import os
    secret = request.args.get('secret', '')
    expected = os.getenv('INIT_SECRET', 'init-secret-2026')
    if secret != expected:
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 403
    from app.models.database import db, Admin, Client, Driver, Kitchen, Product
    from werkzeug.security import generate_password_hash
    db.drop_all()
    db.create_all()

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
'''

p = r'C:\Users\jairo\Desktop\polleria\MVP_BACK\app\routes\public.py'
s = open(p, encoding='utf-8').read()
s = s + addition
open(p, 'w', encoding='utf-8').write(s)
print('done')
