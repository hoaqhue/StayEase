import hashlib
from datetime import datetime, timedelta
from hotelapp import app, db
from models import (
    ClientType, Client, UserRole, User,
    PaymentMethod, RoomType, RoomStatus,
    Room, Image, Regulation
)


def seed_database():
    # Xóa dữ liệu cũ
    db.session.query(ClientType).delete()
    db.session.query(Client).delete()
    db.session.query(UserRole).delete()
    db.session.query(User).delete()
    db.session.query(PaymentMethod).delete()
    db.session.query(RoomType).delete()
    db.session.query(RoomStatus).delete()
    db.session.query(Room).delete()
    db.session.query(Image).delete()
    db.session.query(Regulation).delete()

    # Client Types
    foreigner_type = ClientType(type='Foreigner', coefficient=1.5)
    domestic_type = ClientType(type='Domestic', coefficient=1.0)
    db.session.add_all([foreigner_type, domestic_type])
    db.session.flush()  # Flush to get IDs

    # Clients
    clients_data = [
        {
            'full_name': f'Client {i}',
            'identification_code': f'ID{1000 + i}',
            'address': f'Address {i}',
            'phone_number': f'090{1000 + i}',
            'email': f'client{i}@example.com',
            'client_type_id': foreigner_type.id if i % 2 == 0 else domestic_type.id
        } for i in range(1, 11)
    ]
    clients = [Client(**data) for data in clients_data]
    db.session.add_all(clients)
    db.session.flush()  # Flush to get IDs

    # User Roles
    admin_role = UserRole(type='Admin')
    receptionist_role = UserRole(type='Receptionist')
    db.session.add_all([admin_role, receptionist_role])
    db.session.flush()  # Flush to get IDs

    # Admin Client
    admin_client = Client(
        full_name='Admin User',
        identification_code='ADMIN001',
        address='Admin Office',
        phone_number='0901234567',
        email='admin@hotel.com',
        client_type_id=domestic_type.id
    )
    db.session.add(admin_client)
    db.session.flush()  # Flush to get IDs

    # Admin User
    admin_user = User(
        username='admin',
        password=hashlib.md5("123456".encode('utf-8')).hexdigest(),
        user_role_id=admin_role.id,
        client_id=admin_client.id
    )
    db.session.add(admin_user)

    # Payment Methods
    payment_methods = [
        PaymentMethod(type='ZaloPay'),
        PaymentMethod(type='MomoPay'),
        PaymentMethod(type='VNPay')
    ]
    db.session.add_all(payment_methods)

    # Room Types
    room_types = [
        RoomType(type='VIP', price_million=1.5),
        RoomType(type='Standard', price_million=1.0),
        RoomType(type='Economic', price_million=0.5)
    ]
    db.session.add_all(room_types)
    db.session.flush()  # Flush to get IDs

    # Room Statuses
    room_statuses = [
        RoomStatus(status='In Use'),
        RoomStatus(status='Empty'),
        RoomStatus(status='Maintaining')
    ]
    db.session.add_all(room_statuses)
    db.session.flush()  # Flush to get IDs

    # Rooms with Images
    default_image_url = "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
    rooms = []
    for i in range(1, 11):
        room_type = room_types[i % 3]
        room_status = room_statuses[i % 3]
        room = Room(
            name=f'Room {100 + i}',
            room_type_id=room_type.id,
            room_status_id=room_status.id
        )
        rooms.append(room)

    db.session.add_all(rooms)
    db.session.flush()  # Flush rooms to get their IDs

    # Create Images after rooms are flushed
    images = []
    for room in rooms:
        image = Image(
            url=default_image_url,
            room_id=room.id
        )
        images.append(image)

    db.session.add_all(images)

    # Regulations
    regulations = [
        Regulation(
            key='max_booking_days',
            value=28.0,
            updated_date=datetime.now()
        ),
        Regulation(
            key='max_persons_per_room',
            value=3.0,
            updated_date=datetime.now()
        ),
        Regulation(
            key='max_capacity_surcharge_percentage',
            value=0.25,
            updated_date=datetime.now()
        )
    ]
    db.session.add_all(regulations)

    # Commit changes
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        seed_database()
        print("Database seeded successfully!")