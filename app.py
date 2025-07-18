from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask.cli import with_appcontext

app = Flask(__name__)
app.secret_key = 'not_a_real_secret_key_for_a_real_app'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------ Models ------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade="all, delete-orphan")

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False, default=10.0)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    # Cascade: delete spots if lot deleted
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True, cascade="all, delete-orphan")

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), default='A')  # 'O' = Occupied, 'A' = Available
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    # Cascade: delete reservations if spot deleted
    reservations = db.relationship('Reservation', backref='spot', lazy=True, cascade="all, delete-orphan")

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)

# ------ CLI Database Setup ------
@app.cli.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database and create admin user."""
    db.create_all()
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@parking.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created.')
    print('Database initialized.')

# ----- ROUTES -----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('register.html')
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ------ ADMIN ------
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    lots = ParkingLot.query.count()
    users = User.query.count()
    spots = ParkingSpot.query.count()
    reservations = Reservation.query.count()
    return render_template('admin_dashboard.html', lots=lots, users=users, spots=spots, reservations=reservations)

@app.route('/admin/lots', methods=['GET', 'POST'])
def manage_lots():
    if not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        address = request.form['address']
        pincode = request.form['pincode']
        max_spots = int(request.form['max_spots'])
        new_lot = ParkingLot(name=name, price=price, address=address, pincode=pincode, max_spots=max_spots)
        db.session.add(new_lot)
        db.session.commit()
        for spot_num in range(1, max_spots + 1):
            new_spot = ParkingSpot(spot_number=spot_num, status='A', lot_id=new_lot.id)
            db.session.add(new_spot)
        db.session.commit()
        flash('Parking lot added successfully', 'success')
        return redirect(url_for('manage_lots'))
    lots = ParkingLot.query.all()
    return render_template('parking_lots.html', lots=lots)

@app.route('/admin/lots/delete/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    lot = ParkingLot.query.get(lot_id)
    if not lot:
        flash('Lot not found', 'danger')
        return redirect(url_for('manage_lots'))
    # Check for occupied spots before deleting (your earlier logic)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    if any(spot.status == 'O' for spot in spots):
        flash('Cannot delete; some spots are still occupied', 'danger')
    else:
        db.session.delete(lot)
        db.session.commit()
        flash('Parking lot deleted', 'success')
    return redirect(url_for('manage_lots'))

@app.route('/admin/spots/<int:lot_id>')
def view_spots(lot_id):
    if not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    lot = ParkingLot.query.get(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('parking_spots.html', lot=lot, spots=spots)

@app.route('/admin/users')
def manage_users():
    if not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('users.html', users=users)

# ------ USER ------
@app.route('/user')
def user_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    curr_reservation = Reservation.query.filter_by(user_id=user_id, leaving_timestamp=None).first()
    if curr_reservation:
        spot = ParkingSpot.query.get(curr_reservation.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
    else:
        spot = lot = None
    return render_template('user_dashboard.html', reservation=curr_reservation, spot=spot, lot=lot)

@app.route('/user/lots')
def user_view_lots():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    lots = ParkingLot.query.all()
    return render_template('parking_lots.html', lots=lots)

@app.route('/user/reserve/<int:lot_id>', methods=['POST'])
def reserve_spot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not spot:
        flash('No spots available in this lot', 'danger')
        return redirect(url_for('user_view_lots'))
    spot.status = 'O'
    reservation = Reservation(
        user_id=user_id,
        spot_id=spot.id,
        parking_timestamp=datetime.now(),
        parking_cost=spot.lot.price
    )
    db.session.add(reservation)
    db.session.commit()
    flash('Spot reserved successfully', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/release', methods=['POST'])
def release_spot():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
    reservation = Reservation.query.filter_by(user_id=user_id, leaving_timestamp=None).first()
    if not reservation:
        flash('No active reservation found', 'danger')
        return redirect(url_for('user_dashboard'))
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'A'
    reservation.leaving_timestamp = datetime.now()
    db.session.commit()
    flash('Spot released successfully', 'success')
    return redirect(url_for('user_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)