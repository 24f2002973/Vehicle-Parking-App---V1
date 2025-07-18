from app import db, User
from werkzeug.security import generate_password_hash

def init_db():
    db.create_all()
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@parking.com',
            password=generate_password_hash('admin'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created.')
    print('Database initialized.')

if __name__ == "__main__":
    from app import app
    with app.app_context():
        init_db()