import hashlib

from flask import Flask
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
        client_id=client.id
    )
    db.session.add(user)
    db.session.commit()


def get_client_types():
    return ClientType.query.all()


if __name__ == "__main__":
    with app.app_context():
        print(auth_user("admin", "123456"))
        print("Database loaded successfully!")


# Ví dụ về hàm kiểm tra số điện thoại đã tồn tại
def get_client_by_phone(phone_number):
    return Client.query.filter_by(phone_number=phone_number).first()


def get_client_by_identification_code(identification_code):
    return Client.query.filter_by(identification_code=identification_code).first()


def get_client_by_email(email):
    return Client.query.filter_by(email=email).first()


def get_forms():
    return BookingForm.query.filter_by(is_checked_in = False).all()

def create_invoice(form_id, payment_method, trans_id):
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