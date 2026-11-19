import sys
import os
import random
import string
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app, db
from app.models.database import Admin, Product, Client, Driver, Kitchen, Order, OrderItem

app = create_app()

def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

with app.app_context():
    db.drop_all()
    db.create_all()

    admin = Admin(username='admin@demo.com', password_hash=generate_password_hash('admin123'))
    db.session.add(admin)

    driver = Driver(
        name='Repartidor Demo',
        username='repartidor@demo.com',
        dni='87654321',
        password_hash=generate_password_hash('repartidor123'),
        phone='999888777',
        address='Av. Repartidor 123',
        photo='https://i.pravatar.cc/150?img=33',
        is_active=True
    )
    db.session.add(driver)

    kitchen = Kitchen(
        name='Cocina Demo',
        username='cocina@demo.com',
        password_hash=generate_password_hash('cocina123'),
        is_active=True
    )
    db.session.add(kitchen)

    first_names = [
        "Juan", "Carlos", "Luis", "Jose", "Miguel", "Pedro", "Ana", "Maria", 
        "Carmen", "Rosa", "Jorge", "Manuel", "David", "Daniel", "Alejandro", 
        "Sofía", "Lucía", "Elena", "Valeria", "Camila", "Mateo", "Santiago", 
        "Gabriel", "Fernando", "Ricardo", "Alberto", "Patricia", "Claudia", "Monica", "Diana"
    ]
    
    last_names = [
        "Perez", "Gomez", "Rodriquez", "Lopez", "Garcia", "Martinez", "Sanchez", 
        "Fernandez", "Gonzalez", "Torres", "Ramirez", "Flores", "Rivera", "Gomez", 
        "Diaz", "Cruz", "Morales", "Ortiz", "Gutierrez", "Chavez", "Ramos", "Castillo", 
        "Silva", "Mendoza", "Vargas", "Rojas", "Medina", "Herrera", "Castro", "Romero"
    ]

    clients_list = []
    for i in range(30):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@demo.com"
        client = Client(
            name=f"{fn} {ln}",
            email=email,
            dni=str(random.randint(10000000, 99999999)),
            phone=f"9{random.randint(10000000, 99999999)}",
            address=f"Av. Principal {random.randint(100, 999)}",
            photo=f"https://i.pravatar.cc/150?img={i+1}",
            password_hash=generate_password_hash('cliente123')
        )
        db.session.add(client)
        clients_list.append(client)

    db.session.commit()

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
        {"name": "Chicharrón de Pollo", "description": "Crocante chicharrón de pollo con yuca", "price": 22.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: chicharrón de pollo y yuca."},
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
        {"name": "Tallarín Saltado", "description": "Tallarín saltado de pollo", "price": 17.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: tallarin saltado."},
        {"name": "Sopa de Pollo", "description": "Sopa de pollo con fideos", "price": 12.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: sopa de pollo."},
        {"name": "Anticuchos de Corazón", "description": "Anticuchos con papa y choclo", "price": 15.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: anticuchos."},
        {"name": "Yuca Frita", "description": "Yuca frita crocante", "price": 7.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: yuca frita."},
        {"name": "Camote Frito", "description": "Camote frito dulce", "price": 6.00, "image": "https://framerusercontent.com/images/YdJMeSsRp9FR1HbonhNr5pEymS0.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: camote frito."},
        {"name": "Ensalada César", "description": "Ensalada césar con pollo", "price": 10.00, "image": "https://framerusercontent.com/images/2SW7sWzterGNO2Utmq3KXXFA.jpg?scale-down-to=1024&width=1200&height=800", "includes": "Incluye: ensalada cesar."},
        {"name": "Pollo al Horno", "description": "Pollo al horno con hierbas", "price": 28.00, "image": "https://framerusercontent.com/images/psjgAUJ76yTxyTp51RByNg6JYjs.jpg?scale-down-to=1024&width=2682&height=1602", "includes": "Incluye: pollo al horno."}
    ]

    for p in sample_products:
        db.session.add(Product(
            name=p["name"],
            description=p["description"],
            includes=p.get("includes"),
            price=p["price"],
            image=p["image"],
            is_active=True
        ))

    db.session.commit()

    driver_record = Driver.query.first()
    products_list = Product.query.all()

    order_types = ['SALON', 'DELIVERY', 'RECOJO_TIENDA']
    payments = ['YAPE', 'PLIN', 'EFECTIVO']
    base_date = datetime.now() - timedelta(days=60)

    for _ in range(200):
        assigned_client = random.choice(clients_list)
        random_days = random.randint(0, 59)
        random_hour = random.choices(
            range(12, 23),
            weights=[5, 10, 12, 8, 5, 6, 10, 18, 22, 15, 8],
            k=1
        )[0]
        created = base_date + timedelta(days=random_days, hours=random_hour, minutes=random.randint(0, 59))
        is_weekend = 1 if created.weekday() >= 5 else 0
        o_type = random.choice(order_types)

        selected_product = random.choice(products_list)
        quantity = random.randint(1, 3)
        base_subtotal = float(selected_product.price) * quantity
        
        weekend_extra = 15.0 if is_weekend else 0.0
        delivery_extra = 12.0 if o_type == 'DELIVERY' else 0.0
        total = base_subtotal + weekend_extra + delivery_extra + random.uniform(2.0, 8.0)
        
        fee = 6.0 if o_type == 'DELIVERY' else 0.0

        delay_score = (1 if o_type == 'DELIVERY' else 0) * 0.4 + (1 if random_hour >= 20 else 0) * 0.4 + (total / 150.0) * 0.2 + random.uniform(-0.1, 0.1)
        is_delayed = 1 if delay_score > 0.5 else 0
        
        prep_minutes = random.randint(45, 75) if is_delayed == 1 else random.randint(15, 35)
        status_val = 'CANCELADO' if (is_delayed == 1 and random.random() < 0.2) else 'FINALIZADO'

        order_id = generate_order_id()
        while db.session.get(Order, order_id):
            order_id = generate_order_id()

        new_order = Order(
            id=order_id,
            customer_id=assigned_client.id,
            customer_name=assigned_client.name,
            customer_email=assigned_client.email,
            customer_phone=assigned_client.phone,
            order_type=o_type,
            delivery_address=assigned_client.address if o_type == 'DELIVERY' else "",
            payment_type=random.choice(payments),
            delivery_fee=fee,
            total_amount=round(total, 2),
            status=status_val,
            driver_id=driver_record.id if (driver_record and o_type == 'DELIVERY') else None,
            driver_name=driver_record.name if (driver_record and o_type == 'DELIVERY') else None,
            created_at=created,
            delivered_at=created + timedelta(minutes=prep_minutes)
        )
        db.session.add(new_order)

        item = OrderItem(
            order_id=order_id,
            product_id=selected_product.id,
            quantity=quantity,
            unit_price=selected_product.price,
            subtotal=round(base_subtotal, 2)
        )
        db.session.add(item)

    db.session.commit()