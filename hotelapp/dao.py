import hashlib
from datetime import datetime

from flask import Flask, session, jsonify
from hotelapp import app
from hotelapp.models import *

def load_rooms():
    return Room.query.all()


def auth_user(username, password):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    return User.query.filter(User.username.__eq__(username.strip()), User.password.__eq__(password)).first()


def get_user_by_id(id):
    return User.query.get(id)




def get_room_types():
    return RoomType.query.all()


def get_user_role(user):
    # Đảm bảo user.role (hoặc field tương ứng) trả về chuỗi
    role = user.user_role if isinstance(user.user_role, str) else str(user.user_role)
    return UserRole.query.filter(UserRole.type == role).first()


def create_user(name, username, password, identification_code, phone_number, email, address, client_type_id):
    # Hash mật khẩu
    hashed_password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()

    # Tạo đối tượng Client
    client = Client(
        full_name=name,
        identification_code=identification_code,
        address=address,
        phone_number=phone_number,
        email=email,
        client_type_id=client_type_id
    )
    db.session.add(client)
    db.session.flush()  # Đảm bảo `client.id` được tạo trước khi tiếp tục

    # Lấy role "Guest" từ bảng UserRole
    guest_role = UserRole.query.filter_by(type="Guest").first()
    if not guest_role:
        raise ValueError("Role 'Guest' không tồn tại trong bảng UserRole")

    # Tạo đối tượng User
    user = User(
        username=username,
        password=hashed_password,
        user_role_id=guest_role.id,  # Sử dụng ID của role "Guest"
        client_id=client.client_id
    )
    db.session.add(user)
    db.session.commit()


def get_client_types():
    return ClientType.query.all()
def get_client_by_phone(phone_number):
    return Client.query.filter_by(phone_number=phone_number).first()
def get_client_by_id(client_id):
    return Client.query.filter_by(client_id=client_id).first()


def get_client_by_identification_code(identification_code):
    return Client.query.filter_by(identification_code=identification_code).first()

def get_regulation_by_key(key):
    return Regulation.query.filter_by(key=key).first()

def update_room_status(checkin):
    # Lấy các booking đã hết hạn (ngày trả phòng nhỏ hơn ngày check-in)
    expired_bookings = BookingForm.query.filter(BookingForm.check_out_date < checkin).all()

    for booking in expired_bookings:
        for booking_detail in booking.booking_room_details:
            room = booking_detail.room
            available_status = RoomStatus.query.filter_by(status="Có sẵn").first()

            # Kiểm tra trạng thái phòng và cập nhật nếu cần
            if available_status and room.room_status_id != available_status.id:
                room.room_status_id = available_status.id

    # Commit tất cả các thay đổi sau khi đã duyệt hết các booking
    db.session.commit()
    print(f"Đã cập nhật trạng thái của các phòng hết hạn thành 'Có sẵn'.")


def get_client_by_email(email):
    return Client.query.filter_by(email=email).first()

def get_client_type_by_id(id):
    return ClientType.query.get(id)

def get_client_type_by_type(type):
    return ClientType.query.filter_by(type=type).first()

def get_forms():
    return BookingForm.query.filter_by(is_checked_in = False).all()

def create_invoice(form_id, payment_method, trans_id):
    if not trans_id:
        trans_id = "CASH"  # Giá trị mặc định cho tiền mặt
    print("form id: ", form_id)
    total = 0
    for form_details in BookingRoomDetails.query.filter_by(booking_form_id=form_id).all():
        total += form_details.total
    invoice = Invoice(
        booking_form_id=form_id,
        payment_method_id=payment_method,
        transaction_id=trans_id,
        total=total
    )
    print(trans_id, total)
    db.session.add(invoice)
    db.session.commit()
    return invoice

def get_clients_of_booking_form(booking_form_id):
    with app.app_context():
        clients = db.session.query(Client).join(
            ClientRoomDetails, Client.client_id == ClientRoomDetails.client_id
        ).join(
            BookingRoomDetails, BookingRoomDetails.id == ClientRoomDetails.booking_details_id
        ).filter(
            BookingRoomDetails.booking_form_id == booking_form_id
        ).all()

        return clients

if __name__ == "__main__":
    with app.app_context():
        print(auth_user("admin", "123456"))
        print("Database loaded successfully!")



