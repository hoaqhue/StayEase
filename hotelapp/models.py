from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date, Enum, DateTime
from sqlalchemy.orm import relationship, Relationship, backref
from hotelapp import app, db
from enum import Enum as enum


class Status(enum):
    PENDING=0
    SUCCESS=1
    FAILED=2


class BookingForm(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    is_checked_in = Column(Boolean, default=False)
    receipted_by = Column(Integer, ForeignKey('user.id'))
    client_id = Column(Integer, ForeignKey('client.client_id'), nullable=False)
    booking_room_details=db.relationship('BookingRoomDetails', lazy=True, backref='booking_form' )


    def __str__(self):
        return f"Booking Form {self.id}"


class Client(db.Model):
    client_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(50), nullable=False)
    identification_code = Column(String(20), nullable=False, unique=True)
    address = Column(String(50), nullable=False)
    phone_number = Column(String(50), nullable=True, unique=True)
    email = Column(String(50), nullable=False)
    client_type_id = Column(Integer, ForeignKey('client_type.id'), nullable=True)
    booking_forms = db.relationship("BookingForm", backref="client", cascade="all, delete-orphan")

    def __str__(self):
        return self.full_name


class ClientType(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    coefficient = Column(Float, default=0)

    def __str__(self):
        return f"{self.type}: {self.coefficient}"  # Combine type and coefficient in a readable format




class User(db.Model, UserMixin):
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(20), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    user_role_id = Column(Integer, ForeignKey('user_role.id'), nullable=False)
    client_id = Column(Integer, ForeignKey('client.client_id'), nullable=True)
    user_role = relationship('UserRole', backref='user', lazy=False)

    def __str__(self):
        return self.username


class Regulation(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    updated_by = Column(Integer, ForeignKey('user.id'), nullable=True)
    updated_date = Column(Date)

    def __str__(self):
        return self.key


class Invoice(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    total = Column(Float, default=0)
    created_date = Column(Date, nullable=False, default=datetime.now)
    booking_form_id = Column(Integer, ForeignKey('booking_form.id'), nullable=True)
    payment_method_id = Column(Integer, ForeignKey('payment_method.id'), nullable=True)
    transaction_id = Column(String(50), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.PENDING)

    def __str__(self):
        return f"Invoice {self.id}"


class ClientRoomDetails(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey('client.client_id'), nullable=True)
    booking_details_id = Column(Integer, ForeignKey('booking_room_details.id'), nullable=True)

    def __str__(self):
        return f"Client Room Details {self.id}"


class UserRole(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)

    def __str__(self):
        return self.type


class PaymentMethod(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(100), nullable=False)

    def __str__(self):
        return self.type


class BookingRoomDetails(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    total = Column(Float, default=0)
    booking_form_id = Column(Integer, ForeignKey('booking_form.id'), nullable=True)
    room_id = Column(Integer, ForeignKey('room.id'), nullable=True)
    room=db.relationship('Room', lazy=True, backref='booking_form_details')
    passengers = Column(Integer, nullable=False, default=1)


    def __str__(self):
        return f"Booking Room Details {self.id}"


class RoomDetailsReport(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_count = Column(Integer, default=0)
    rate = Column(Float, default=0)
    report_id = Column(Integer, ForeignKey('usage_density_report.id'), nullable=True)
    room_id = Column(Integer, ForeignKey('room.id'), nullable=True)

    def __str__(self):
        return f"Room Details Report {self.id}"


class UsageDensityReport(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(Date)

    def __str__(self):
        return f"Usage Density Report {self.id}"


class MonthlyReport(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(Date)

    def __str__(self):
        return f"Monthly Report {self.id}"


class RoomTypeReport(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    revenue = Column(Float, default=0)
    rate = Column(Float, default=0)
    rent_count = Column(Integer, default=0)
    report_id = Column(Integer, ForeignKey('monthly_report.id'), nullable=True)
    room_type_id = Column(Integer, ForeignKey('room_type.id'), nullable=True)

    def __str__(self):
        return f"Room Type Report {self.id}"


class Image(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(200),
                 default="https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg")
    room_id = Column(Integer, ForeignKey('room.id'), nullable=True)
    room = db.relationship('Room', back_populates='images')

    def __str__(self):
        return f"Image {self.id}"


class RoomStatus(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False)

    def __str__(self):
        return self.status


class Room(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=True, unique=True)
    description=Column(String(5000), nullable=True)
    room_type_id = Column(Integer, ForeignKey('room_type.id'), nullable=True)
    room_status_id = Column(Integer, ForeignKey('room_status.id'), nullable=True)
    room_status = Relationship('RoomStatus', lazy=True, backref='room')
    room_type = Relationship('RoomType', lazy=True, backref='room')
    images = db.relationship('Image', back_populates='room')

    def __str__(self):
        return self.name


class RoomType(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    price_million = Column(Float, default=0)

    def __str__(self):
        return self.type

class AdImage(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(200), nullable=False)
    description = Column(String(200), nullable=True)

    def __str__(self):
        return f"AdImage {self.id}"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # db.session.commit()
