import pytest
from app import create_app, db
from app.models.database import Admin
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        admin = Admin(
            username='admin@demo.com',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_admin_login(client):
    response = client.post('/login', json={
        'username': 'admin@demo.com',
        'password': 'admin123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['role'] == 'admin'
    assert 'access_token' in data['data']