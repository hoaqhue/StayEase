from hotelapp import db, app
from hotelapp.models import (
    RoomType, RoomStatus, ClientType, UserRole,
    PaymentMethod, Room, Client, User, Image, Regulation, BookingForm, BookingRoomDetails, AdImage
)
import hashlib
from datetime import datetime


def seed_data():
    try:
        # Xóa dữ liệu cũ
        db.session.query(BookingRoomDetails).delete()
        db.session.query(BookingForm).delete()
        db.session.query(Image).delete()
        db.session.query(User).delete()
        db.session.query(Client).delete()
        db.session.query(UserRole).delete()
        db.session.query(PaymentMethod).delete()
        db.session.query(Room).delete()
        db.session.query(RoomStatus).delete()
        db.session.query(RoomType).delete()
        db.session.query(ClientType).delete()
        db.session.query(Regulation).delete()
        db.session.query(AdImage).delete()

        # Thêm ảnh quảng cáo mẫu
        ad_images = [
            AdImage(url="https://www.lottehotel.com/content/dam/lotte-hotel/global/common/company/saigon-hotel.jpg",
                    description="Image"),
            AdImage(url="https://www.lottehotel.com/content/dam/lotte-hotel/lotte/hanoi/accommodation/standard/deluxeroom/180921-2-2000-roo-LTHA.jpg.thumb.768.768.jpg",
                    description="Image"),
            AdImage(url="https://galatravel.vn/pic/hotel/4096906_636830779542384416_HasThumb.jpg",
                    description="Image"),
            AdImage(url="https://macmedia.vn/media/12247/180712-2-2000-con-hanoi-hoteljpgthumb19201920.jpg",
                    description="Image")
        ]
        db.session.add_all(ad_images)
        db.session.commit()

        # Tạo loại phòng
        room_types = [
            RoomType(type="Deluxe", price_million=1000000),  # Deluxe Room
            RoomType(type="Standard", price_million=800000),  # Standard Room
            RoomType(type="Suite Family", price_million=1500000),  # Family Suite
            RoomType(type="Presidential", price_million=3000000),  # Presidential Suite
        ]

        db.session.add_all(room_types)
        db.session.commit()

        # Tạo trạng thái phòng
        room_statuses = [
            RoomStatus(status="Có sẵn"),
            RoomStatus(status="Bảo trì"),
            RoomStatus(status="Đã đặt"),
        ]
        db.session.add_all(room_statuses)
        db.session.commit()

        # Tạo loại khách hàng
        client_types = [
            ClientType(type="Nội Địa", coefficient=0.25),  # Khách nội địa
            ClientType(type="Nước Ngoài", coefficient=1.5)  # Khách nước ngoài
        ]

        db.session.add_all(client_types)
        db.session.commit()



        # Tạo vai trò người dùng
        user_roles = [
            UserRole(type="Admin"),
            UserRole(type="Receptionist"),
            UserRole(type="Guest"),
        ]
        db.session.add_all(user_roles)
        db.session.commit()


        payment_methods = [
            PaymentMethod(type="Thẻ tín dụng"),
            PaymentMethod(type="Tiền mặt"),
            PaymentMethod(type="Chuyển khoản ngân hàng"),
            PaymentMethod(type="Ví điện tử"),
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
                client_type_id=client_types[0].id
            ),
        ]
        db.session.add_all(clients)
        db.session.commit()

        # Tạo tài khoản Admin
        admin_user = User(
            username="admin",
            password=hashlib.md5("123456".encode("utf-8")).hexdigest(),
            user_role_id=user_roles[0].id,
            client_id=clients[0].client_id
        )
        rec_user = User(
            username="rec",
            password=hashlib.md5("123456".encode("utf-8")).hexdigest(),
            user_role_id=user_roles[1].id,
            client_id=clients[0].client_id
        )
        db.session.add_all([admin_user, rec_user])
        db.session.commit()


        rooms = [
            Room(
                name="Room 101",
                room_type_id=room_types[0].id,
                room_status_id=room_statuses[0].id,
                description="Phòng sang trọng với tiện nghi hiện đại và tầm nhìn tuyệt đẹp."
            ),
            Room(
                name="Room 102",
                room_type_id=room_types[0].id,
                room_status_id=room_statuses[1].id,
                description="Phòng sang trọng với tiện nghi hiện đại và tầm nhìn tuyệt đẹp."
            ),
            Room(
                name="Room 103",
                room_type_id=room_types[0].id,
                room_status_id=room_statuses[0].id,
                description="Phòng sang trọng với tiện nghi hiện đại và tầm nhìn tuyệt đẹp."
            ),
            Room(
                name="Room 104",
                room_type_id=room_types[0].id,
                room_status_id=room_statuses[0].id,
                description="Phòng sang trọng với tiện nghi hiện đại và tầm nhìn tuyệt đẹp."
            ),
            Room(
                name="Room 105",
                room_type_id=room_types[0].id,
                room_status_id=room_statuses[0].id,
                description="Phòng sang trọng với tiện nghi hiện đại và tầm nhìn tuyệt đẹp."
            ),
            Room(
                name="Room 201",
                room_type_id=room_types[1].id,
                room_status_id=room_statuses[0].id,
                description="Phòng thoải mái và tiết kiệm, phù hợp cho khách du lịch với ngân sách hạn chế."
            ),
            Room(
                name="Room 202",
                room_type_id=room_types[1].id,
                room_status_id=room_statuses[1].id,
                description="Phòng thoải mái và tiết kiệm, phù hợp cho khách du lịch với ngân sách hạn chế."
            ),
            Room(
                name="Room 203",
                room_type_id=room_types[1].id,
                room_status_id=room_statuses[0].id,
                description="Phòng thoải mái và tiết kiệm, phù hợp cho khách du lịch với ngân sách hạn chế."
            ),
            Room(
                name="Room 204",
                room_type_id=room_types[1].id,
                room_status_id=room_statuses[0].id,
                description="Phòng thoải mái và tiết kiệm, phù hợp cho khách du lịch với ngân sách hạn chế."
            ),
            Room(
                name="Room 205",
                room_type_id=room_types[1].id,
                room_status_id=room_statuses[0].id,
                description="Phòng thoải mái và tiết kiệm, phù hợp cho khách du lịch với ngân sách hạn chế."
            ),
            Room(
                name="Room 301",
                room_type_id=room_types[2].id,
                room_status_id=room_statuses[0].id,
                description="Phòng rộng rãi, lý tưởng cho các gia đình, với không gian thoải mái"
            ),
            Room(
                name="Room 302",
                room_type_id=room_types[2].id,
                room_status_id=room_statuses[0].id,
                description="Phòng rộng rãi, lý tưởng cho các gia đình, với không gian thoải mái"
            ),
            Room(
                name="Room 303",
                room_type_id=room_types[2].id,
                room_status_id=room_statuses[0].id,
                description="Phòng rộng rãi, lý tưởng cho các gia đình, với không gian thoải mái"
            ),
            Room(
                name="Room 304",
                room_type_id=room_types[2].id,
                room_status_id=room_statuses[0].id,
                description="Phòng rộng rãi, lý tưởng cho các gia đình, với không gian thoải mái"
            ),
            Room(
                name="Room 305",
                room_type_id=room_types[2].id,
                room_status_id=room_statuses[0].id,
                description="Phòng rộng rãi, lý tưởng cho các gia đình, với không gian thoải mái"
            ),
            Room(
                name="Room 401",
                room_type_id=room_types[3].id,
                room_status_id=room_statuses[0].id,
                description="Phòng tổng thống với thiết kế thanh lịch và tiện nghi cao cấp, dành cho khách VIP."
            ),
            Room(
                name="Room 402",
                room_type_id=room_types[3].id,
                room_status_id=room_statuses[0].id,
                description="Phòng tổng thống với thiết kế thanh lịch và tiện nghi cao cấp, dành cho khách VIP."
            ),
            Room(
                name="Room 403",
                room_type_id=room_types[3].id,
                room_status_id=room_statuses[0].id,
                description="Phòng tổng thống với thiết kế thanh lịch và tiện nghi cao cấp, dành cho khách VIP."
            ),
            Room(
                name="Room 404",
                room_type_id=room_types[3].id,
                room_status_id=room_statuses[0].id,
                description="Phòng tổng thống với thiết kế thanh lịch và tiện nghi cao cấp, dành cho khách VIP."
            ),
            Room(
                name="Room 405",
                room_type_id=room_types[3].id,
                room_status_id=room_statuses[0].id,
                description="Phòng tổng thống với thiết kế thanh lịch và tiện nghi cao cấp, dành cho khách VIP."
            ),
        ]
        db.session.add_all(rooms)
        db.session.commit()

        # Tạo ảnh phòng
        room_images = {
            "Deluxe": [
                "https://res.cloudinary.com/dco0ptusf/image/upload/v1729844929/cld-sample-2.jpg"
            ],
            "Standard": [
                "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
            ],
            "Suite Family": [
                "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
            ],
            "Presidential": [
                "https://res.cloudinary.com/dj4slrwsl/image/upload/v1733044164/PMC_3922re2-7a204d0f28cc4d2abacf951df89d19d5_nzuu38.jpg"
            ]
        }
        for room in rooms:
            urls = room_images.get(room.room_type.type, [])
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
