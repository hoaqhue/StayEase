from hotelapp import db, app
from hotelapp.models import (
    RoomType, RoomStatus, ClientType, UserRole,
    PaymentMethod, Room, Client, User, Image, Regulation
)
import hashlib
from datetime import datetime


def seed_data():
    try:
        # Xóa dữ liệu cũ
        db.session.query(Client).delete()
        db.session.query(User).delete()
        db.session.query(UserRole).delete()
        db.session.query(PaymentMethod).delete()
        db.session.query(Room).delete()
        db.session.query(RoomStatus).delete()
        db.session.query(RoomType).delete()
        db.session.query(ClientType).delete()
        db.session.query(Regulation).delete()
        db.session.query(Image).delete()

        # Tạo loại phòng
        room_types = [
            RoomType(type="Deluxe", price_million=1.0),
            RoomType(type="Standard", price_million=0.8),
            RoomType(type="Family Suite", price_million=1.5),
            RoomType(type="Presidential Suite", price_million=3.0),
        ]
        db.session.add_all(room_types)
        db.session.commit()

        # Tạo trạng thái phòng
        room_statuses = [
            RoomStatus(status="Available"),
            RoomStatus(status="Occupied"),
            RoomStatus(status="Maintenance"),
            RoomStatus(status="Reserved"),
        ]
        db.session.add_all(room_statuses)
        db.session.commit()

        # Tạo loại khách hàng
        client_types = [
            ClientType(type="Regular", coefficient=1.0),
            ClientType(type="VIP", coefficient=1.5),
            ClientType(type="Premium", coefficient=2.0),
        ]
        db.session.add_all(client_types)
        db.session.commit()

        # Check ClientType after committing
        print(f"Client Types: {[client_type.type for client_type in client_types]}")

        # Tạo vai trò người dùng
        user_roles = [
            UserRole(type="Admin"),
            UserRole(type="Receptionist"),
            UserRole(type="Guest"),
        ]
        db.session.add_all(user_roles)
        db.session.commit()

        # Check UserRole after committing
        print(f"User Roles: {[role.type for role in user_roles]}")

        # Tạo phương thức thanh toán
        payment_methods = [
            PaymentMethod(type="Credit Card"),
            PaymentMethod(type="Cash"),
            PaymentMethod(type="Bank Transfer"),
            PaymentMethod(type="E-Wallet"),
        ]
        db.session.add_all(payment_methods)
        db.session.commit()

        # Tạo khách hàng
        clients = [
            Client(
                full_name="Nguyen Van A",
                identification_code="1234567890",
                address="Hanoi, Vietnam",
                phone_number="0123456789",
                email="nguyenvana@example.com",
                client_type_id=client_types[0].id
            ),
            Client(
                full_name="Tran Thi B",
                identification_code="0987654321",
                address="Ho Chi Minh, Vietnam",
                phone_number="0987654321",
                email="tranthib@example.com",
                client_type_id=client_types[1].id
            ),
            Client(
                full_name="Le Thi C",
                identification_code="1122334455",
                address="Da Nang, Vietnam",
                phone_number="0912345678",
                email="lethic@example.com",
                client_type_id=client_types[2].id
            ),
        ]
        db.session.add_all(clients)
        db.session.commit()

        # Tạo tài khoản Admin
        admin_user = User(
            username="admin",
            password=hashlib.md5("123456".encode("utf-8")).hexdigest(),
            user_role_id=user_roles[0].id,
            client_id=clients[0].id
        )
        db.session.add(admin_user)
        db.session.commit()

        # Check if admin user is created
        print(f"Admin user created: {admin_user.username}")

        # Tạo phòng
        rooms = [
            Room(name="Room 101", room_type_id=room_types[0].id, room_status_id=room_statuses[0].id, price=200000),
            Room(name="Room 102", room_type_id=room_types[1].id, room_status_id=room_statuses[1].id, price=300000),
            Room(name="Room 201", room_type_id=room_types[2].id, room_status_id=room_statuses[0].id, price=400000),
            Room(name="Room 202", room_type_id=room_types[3].id, room_status_id=room_statuses[0].id, price=500000),
        ]
        db.session.add_all(rooms)
        db.session.commit()

        # Tạo ảnh phòng
        room_images = {
            "Room 101": [
                "https://res.cloudinary.com/dco0ptusf/image/upload/v1729844929/cld-sample-2.jpg"
            ],
            "Room 102": [
                "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
            ],
            "Room 201": [
                "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
            ],
            "Room 202": [
                "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
            ]
        }
        for room in rooms:
            urls = room_images.get(room.name, [])
            for url in urls:
                image = Image(url=url, room_id=room.id)
                db.session.add(image)
        db.session.commit()

        # Tạo quy định
        regulations = [
            Regulation(key="max_booking_days", value=28.0, updated_date=datetime.now()),
            Regulation(key="max_persons_per_room", value=3.0, updated_date=datetime.now()),
            Regulation(key="max_capacity_surcharge_percentage", value=0.25, updated_date=datetime.now()),
        ]
        db.session.add_all(regulations)
        db.session.commit()

        print("Dữ liệu mẫu đã được tạo thành công.")

    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi tạo dữ liệu mẫu: {e}")


if __name__ == "__main__":
    with app.app_context():
        seed_data()
