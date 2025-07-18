from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False, default=10.0)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)

    def __repr__(self):
        return f'<ParkingLot {self.name}>'

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), default='O')  # 'O' = Occupied, 'A' = Available
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    reservations = db.relationship('Reservation', backref='spot', lazy=True)

    def __repr__(self):
        return f'<ParkingSpot #{self.spot_number} at Lot {self.lot_id}>'

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Reservation by User {self.user_id} at Spot {self.spot_id}>'